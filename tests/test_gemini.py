"""Gemini wire contract and local event presentation; no live secrets/network."""
import io
import json
from urllib.error import HTTPError, URLError
from unittest.mock import Mock

import pytest
from app import create_app
from tests.auth_support import login
from app.ai_explanations import GeminiProvider, ProviderError, safe_features
from app.database import insert_log
from tests.test_ai_explanations import app_fixture, Provider, wait, token, OUTPUT, KEY


def opener_for(body):
    opener=Mock()
    opener.open.return_value.__enter__=Mock(return_value=io.BytesIO(json.dumps(body).encode()))
    opener.open.return_value.__exit__=Mock(return_value=False)
    return opener


def test_gemini_wire_contract_privacy_and_vietnamese_prompt():
    opener=opener_for({'choices':[{'finish_reason':'stop','message':{'content':json.dumps(OUTPUT)}}]})
    provider=GeminiProvider(KEY,'gemini-fixture',opener=opener)
    assert provider.analyze(safe_features('../private/TOKEN?ip=192.0.2.4','BLOCK',True))==OUTPUT
    request=opener.open.call_args.args[0]
    body=json.loads(request.data)
    assert request.full_url=='https://generativelanguage.googleapis.com/v1beta/openai/chat/completions'
    assert request.get_header('Authorization')=='Bearer '+KEY
    assert body['max_tokens']==2048 and body['response_format']=={'type':'json_object'}
    assert 'store' not in body and 'max_completion_tokens' not in body
    assert 'Vietnamese' in body['messages'][0]['content']
    for secret in ['private','TOKEN','192.0.2.4',KEY]:assert secret not in request.data.decode()


@pytest.mark.parametrize('error,code',[(TimeoutError(),'timeout'),(URLError('sensitive'),'network'),
    (HTTPError('https://example.test',401,'secret',{},None),'authentication'),
    (HTTPError('https://example.test',403,'secret',{},None),'authentication'),
    (HTTPError('https://example.test',429,'secret',{},None),'quota')])
def test_gemini_errors(error,code):
    opener=Mock();opener.open.side_effect=error
    with pytest.raises(ProviderError,match='^'+code+'$'):
        GeminiProvider(KEY,'gemini-fixture',opener=opener).analyze(safe_features('..','BLOCK',True))


@pytest.mark.parametrize('body',[
    {'choices':[{'finish_reason':'length','message':{'content':json.dumps(OUTPUT)}}]},
    {'choices':[]}, {'choices':[{'message':{'content':'```json\n{}\n```'}}]},
    {'choices':[{'message':{'content':json.dumps({**OUTPUT,'why':KEY})}}]}])
def test_gemini_invalid_responses(body):
    with pytest.raises(ProviderError,match='invalid_response'):
        GeminiProvider(KEY,'gemini-fixture',opener=opener_for(body)).analyze(safe_features('..','BLOCK',True))


@pytest.mark.parametrize('key,model,configured',[(KEY,'gemini-fixture',True),(None,'gemini-fixture',False),(KEY,None,False)])
def test_factory_gemini_environment_and_missing_configuration(tmp_path,monkeypatch,key,model,configured):
    from app import ai_explanations
    for name,value in [('AI_EXPLANATION_API_KEY',key),('AI_EXPLANATION_MODEL',model),('AI_EXPLANATION_PROVIDER','gemini')]:
        if value is None:monkeypatch.delenv(name,raising=False)
        else:monkeypatch.setenv(name,value)
    provider=Provider()
    constructor=Mock(return_value=provider)
    monkeypatch.setattr(ai_explanations,'GeminiProvider',constructor)
    app=create_app({'DATABASE':tmp_path/'events.sqlite3','FILES_ROOT':tmp_path/'files',
                    'ADMIN_HASH_FILE':tmp_path/'admin_password.hash','AUDITOR_HASH_FILE':tmp_path/'auditor_password.hash',
                    'ADMIN_PASSWORD':'isolated-fixture-password','MODEL_PATH':tmp_path/'missing-model.joblib'})
    service=app.extensions['ai_explanations']
    try:
        assert service.snapshot()['configured']==configured
        assert not service.snapshot()['enabled'] and not provider.calls
        if configured:
            assert constructor.call_args.args[:2]==(KEY,'gemini-fixture')
        else:constructor.assert_not_called()
    finally:service.close()


def test_event_detail_links_exact_event_and_saved_provider(tmp_path):
    provider=Provider();provider.name='gemini';provider.model='gemini-fixture'
    app,client=app_fixture(tmp_path,provider)
    service=app.extensions['ai_explanations'];service.set_enabled(True)
    try:
        client.get('/download?path=../secret');wait(service)
        # Event outside the 20 recent analyses must still be accessible.
        for i in range(2,24):service._process(i,safe_features('..','BLOCK',True))
        page=client.get('/dashboard/events/1')
        assert page.status_code==200
        for value in [b'gemini-fixture',b'BLOCK',b'403',OUTPUT['why'].encode()]:assert value in page.data
        assert service.snapshot(1)['rows'][0]['event_id']==1
        assert client.get('/dashboard/events/99999').status_code==404
        assert b'/dashboard/events/1' in client.get('/dashboard').data
        assert client.post('/dashboard/ai-analysis/settings',data={'enabled':'0'}).status_code==403
        assert client.post('/dashboard/ai-analysis/settings',data={'csrf_token':token(client),'enabled':'0'}).status_code==302
    finally:service.close()


def test_event_detail_auth_and_xss(tmp_path):
    app,client=app_fixture(tmp_path)
    event=insert_log(app.config['DATABASE'],'192.0.2.8','<script>alert(1)</script>',None,'unavailable','MISS',404,'<img src=x onerror=alert(2)>',1)
    page=client.get(f'/dashboard/events/{event}')
    assert page.status_code==200 and b'<script>alert(1)</script>' not in page.data
    assert b'&lt;script&gt;' in page.data and b'UNAVAILABLE' in page.data
    with client.session_transaction() as session:session.clear()
    assert client.get(f'/dashboard/events/{event}').status_code==302
    login(client,password='auditor-fixture-only',role='auditor')
    assert client.get(f'/dashboard/events/{event}').status_code==403
