"""Advisory API privacy, isolation, failure modes, dedup and authorization."""
import io
import json
import re
import sqlite3
import threading
from pathlib import Path
from urllib.error import HTTPError,URLError
from unittest.mock import Mock

import pytest
from app import create_app
from app.passwords import password_hash
from tests.auth_support import login
from app.ai_explanations import ChatCompletionProvider,ExplanationService,ProviderError,safe_features

OUTPUT={'why':'Encoded parent components','traversal_type':'encoded traversal','risk':'high','recommendations':'Keep independent path boundary checks.'}
KEY='fixture-api-key-not-a-real-secret-92837'


class Provider:
    identity='fixture-provider'
    def __init__(self,error=None):self.calls=[];self.error=error
    def analyze(self,features):
        self.calls.append(features)
        if self.error:raise self.error
        return dict(OUTPUT)


def app_fixture(tmp_path,provider=None):
    public=tmp_path/'public';public.mkdir();(public/'ok.txt').write_bytes(b'PUBLIC')
    app=create_app({'TESTING':True,'CSRF_ENABLED':True,'FILES_ROOT':public,'DATABASE':tmp_path/'logs.sqlite3','AI_EXPLANATION_ADAPTER':provider,
                    'AUDITOR_PASSWORD_HASH':password_hash('auditor-fixture-only')})
    client=app.test_client()
    login(client)
    return app,client


def token(client,path='/dashboard'):
    return re.search(rb'name="csrf_token" value="([^"]+)"',client.get(path).data)[1].decode()


def wait(service):
    # Queue.join has no deadline; test uses a condition with a bounded timer.
    done=threading.Event()
    threading.Thread(target=lambda:(service.queue.join(),done.set()),daemon=True).start()
    assert done.wait(5),'Background worker did not finish'


def test_privacy_allowlist_no_raw_path_or_secret():
    raw='../private/secret-password-TOKEN-8412?ip=192.0.2.22'
    features=safe_features(raw,'BLOCK',True)
    assert features['parent_components']==1
    assert set(features)=={'decision','ml_alert','parent_components','absolute_style','backslash','structural_encoding','remaining_decode_changes','length_bucket'}
    text=json.dumps(features)
    for value in ['private','secret','TOKEN','8412','192.0.2.22','password']:assert value not in text
    assert safe_features('%252e%252e%252fsecret','BLOCK',True)['remaining_decode_changes']==2


@pytest.mark.parametrize('body,error,code',[
 (None,URLError('network details must not be logged'),'network'),
 (None,TimeoutError('timeout details'),'timeout'),
 (None,HTTPError('https://example.test',429,'quota',{},None),'quota'),
 (b'not-json',None,'invalid_response'),
 (json.dumps({'choices':[{'message':{'content':json.dumps({**OUTPUT,'risk':[]})}}]}).encode(),None,'invalid_response'),
 (json.dumps({'choices':[{'message':{'content':json.dumps({**OUTPUT,'why':KEY})}}]}).encode(),None,'invalid_response')])
def test_provider_failure_codes_do_not_expose_responses(body,error,code):
    opener=Mock()
    if error:opener.open.side_effect=error
    else:opener.open.return_value.__enter__=Mock(return_value=io.BytesIO(body));opener.open.return_value.__exit__=Mock(return_value=False)
    provider=ChatCompletionProvider(KEY,'https://example.test/v1/chat/completions','fixture-model',opener=opener)
    with pytest.raises(ProviderError) as caught:provider.analyze(safe_features('../secret','BLOCK',True))
    assert str(caught.value)==code


def test_provider_request_success_is_sanitized_and_bounded():
    envelope=json.dumps({'choices':[{'message':{'content':json.dumps(OUTPUT)}}]}).encode()
    opener=Mock();opener.open.return_value.__enter__=Mock(return_value=io.BytesIO(envelope));opener.open.return_value.__exit__=Mock(return_value=False)
    provider=ChatCompletionProvider(KEY,'https://example.test/v1/chat/completions','fixture-model',timeout=2,opener=opener)
    assert provider.analyze(safe_features('../SECRET_RAW_7823','BLOCK',True))==OUTPUT
    args,kwargs=opener.open.call_args;request=args[0]
    assert kwargs['timeout']==2 and 'SECRET_RAW_7823' not in request.data.decode()
    assert KEY not in request.data.decode() and request.get_header('Authorization')=='Bearer '+KEY
    assert json.loads(request.data)['store'] is False


def test_offline_and_admin_toggle_csrf_roles(tmp_path,monkeypatch):
    monkeypatch.delenv('AI_EXPLANATION_API_KEY',raising=False)
    app,client=app_fixture(tmp_path);service=app.extensions['ai_explanations']
    assert service.provider is None
    assert client.get('/download?path=../secret').status_code==403 and not service.path.exists()
    assert client.post('/dashboard/ai-analysis/settings',data={'enabled':'1'}).status_code==403
    assert client.post('/dashboard/ai-analysis/settings',data={'enabled':'1','csrf_token':token(client)}).status_code==302
    assert service.snapshot()['enabled'] and not service.snapshot()['configured']
    assert client.get('/download?path=ok.txt').data==b'PUBLIC'
    for role,status in [('auditor',403),(None,302)]:
        with client.session_transaction() as session:
            session.clear()
        if role:login(client,password='auditor-fixture-only',role=role)
        csrf=token(client,'/login')
        assert client.post('/dashboard/ai-analysis/settings',data={'enabled':'0','csrf_token':csrf}).status_code==status


@pytest.mark.parametrize('error,status',[(None,'success'),(ProviderError('network'),'network'),(ProviderError('quota'),'quota'),(ProviderError('timeout'),'timeout'),(ProviderError('invalid_response'),'invalid_response')])
def test_async_download_decisions_unchanged_and_no_sensitive_sidecar(tmp_path,error,status):
    provider=Provider(error);app,client=app_fixture(tmp_path,provider);service=app.extensions['ai_explanations'];service.set_enabled(True)
    try:
        response=client.get('/download?path=../PRIVATE_PASSWORD_8193.txt')
        assert response.status_code==403
        wait(service);snapshot=service.snapshot()
        assert snapshot['rows'][0]['status']==status
        with sqlite3.connect(app.config['DATABASE']) as db:
            assert db.execute('SELECT action,http_status FROM access_logs').fetchone()==('BLOCK',403)
        assert 'PRIVATE_PASSWORD_8193' not in repr(provider.calls)+repr(snapshot)
        assert 'Ph\u00e2n t\u00edch AI' in client.get('/dashboard').get_data(as_text=True)
    finally:service.close()


def test_slow_provider_never_waits_on_download_and_queue_is_bounded(tmp_path):
    started=threading.Event();release=threading.Event()
    class Slow(Provider):
        def analyze(self,features):started.set();assert release.wait(5);return OUTPUT
    app,client=app_fixture(tmp_path,Slow());service=app.extensions['ai_explanations'];service.set_enabled(True)
    try:
        # The response must return while provider is still unable to complete.
        assert client.get('/download?path=../secret').status_code==403
        assert started.wait(2) and not release.is_set()
        for i in range(100):service.submit(i+100,'../secret','BLOCK',True)
        assert service.queue.qsize()<=16 and service.dropped>0
    finally:release.set();wait(service);service.close()


def test_cache_rate_budget_shared_between_service_instances_and_disable(tmp_path):
    provider=Provider();path=tmp_path/'sidecar.sqlite3'
    one=ExplanationService(path,provider,limit=1);two=ExplanationService(path,provider,limit=1);one.set_enabled(True)
    try:
        one.submit(1,'../privateA','BLOCK',True);wait(one)
        two.submit(2,'../privateB','BLOCK',True);wait(two)
        assert len(provider.calls)==1 and two.snapshot()['rows'][0]['status']=='cached'
        two.submit(3,'C:/secret','BLOCK',True);wait(two)
        assert two.snapshot()['rows'][0]['status']=='rate_limited' and len(provider.calls)==1
        one.set_enabled(False);two.submit(4,'../../secret','BLOCK',True);wait(two)
        assert len(provider.calls)==1
    finally:one.close();two.close()


def test_api_output_xss_is_escaped_and_key_never_in_dashboard(tmp_path):
    provider=Provider();provider.analyze=lambda features:{**OUTPUT,'why':'<script>alert(1)</script>'}
    app,client=app_fixture(tmp_path,provider);service=app.extensions['ai_explanations'];service.set_enabled(True)
    try:
        client.get('/download?path=../secret');wait(service)
        html=client.get('/dashboard').get_data(as_text=True)
        assert '<script>alert(1)</script>' not in html and '&lt;script&gt;alert(1)&lt;/script&gt;' in html and KEY not in html
    finally:service.close()

def test_high_lr_score_still_allows_valid_and_misses_missing_file(tmp_path,monkeypatch):
    import joblib
    class Predictor:
        def predict_proba(self,values):return [[.01,.99] for _ in values]
    monkeypatch.setattr(joblib,'load',lambda path:Predictor())
    provider=Provider();app,client=app_fixture(tmp_path,provider);service=app.extensions['ai_explanations'];service.set_enabled(True)
    try:
        assert client.get('/download?path=ok.txt').data==b'PUBLIC'
        assert client.get('/download?path=missing.txt').status_code==404
        wait(service)
        assert {entry['decision'] for entry in provider.calls}=={'ALLOW','MISS'}
        with sqlite3.connect(app.config['DATABASE']) as db:
            assert db.execute('SELECT action,http_status,ml_label FROM access_logs ORDER BY id').fetchall()==[('ALLOW',200,'suspicious'),('MISS',404,'suspicious')]
    finally:service.close()


def test_external_failures_cool_down_without_another_call(tmp_path):
    provider=Provider(ProviderError('quota'));service=ExplanationService(tmp_path/'sidecar.sqlite3',provider);service.set_enabled(True)
    try:
        service.submit(1,'../secret','BLOCK',True);wait(service)
        service.submit(2,'../another','BLOCK',True);wait(service)
        assert len(provider.calls)==1 and service.snapshot()['rows'][0]['status']=='quota'
    finally:service.close()


def test_sidecar_outage_never_changes_download_result(tmp_path,monkeypatch):
    provider=Provider();app,client=app_fixture(tmp_path,provider);service=app.extensions['ai_explanations']
    monkeypatch.setattr(service,'_enabled',lambda:(_ for _ in ()).throw(sqlite3.OperationalError('private error')))
    try:
        assert client.get('/download?path=../secret').status_code==403
        wait(service)
        assert service.dropped==1 and not provider.calls
        assert client.get('/download?path=ok.txt').data==b'PUBLIC'
    finally:service.close()


def test_business_db_cannot_be_reused_as_sidecar(tmp_path):
    db=tmp_path/'business.sqlite3'
    with pytest.raises(ValueError,match='separate'):
        create_app({'TESTING':True,'DATABASE':db,'FILES_ROOT':tmp_path/'public','AI_EXPLANATION_DATABASE':db})
    assert not db.exists()

@pytest.mark.parametrize('endpoint',['http://example.test/api','https://user:pass@example.test/api','https://example.test/api?token=secret','https://example.test/api#secret'])
def test_unsafe_endpoint_configuration_rejected(endpoint):
    with pytest.raises(ValueError):ChatCompletionProvider(KEY,endpoint,'fixture-model')


def test_api_key_echo_json_escaping_is_rejected():
    key='fixture-key-with-quote-"-78239'
    body=json.dumps({'choices':[{'message':{'content':json.dumps({**OUTPUT,'why':key})}}]}).encode()
    opener=Mock();opener.open.return_value.__enter__=Mock(return_value=io.BytesIO(body));opener.open.return_value.__exit__=Mock(return_value=False)
    provider=ChatCompletionProvider(key,'https://example.test/v1/chat/completions','fixture-model',opener=opener)
    with pytest.raises(ProviderError,match='invalid_response'):provider.analyze(safe_features('../secret','BLOCK',True))


def test_worker_start_failure_falls_back_to_offline(tmp_path,monkeypatch):
    def failed_start(self):raise RuntimeError('fixture thread resource unavailable')
    monkeypatch.setattr(threading.Thread,'start',failed_start)
    app,client=app_fixture(tmp_path,Provider());service=app.extensions['ai_explanations']
    assert service.provider is None and service.snapshot()['dropped']==1
    assert client.get('/download?path=ok.txt').data==b'PUBLIC'
