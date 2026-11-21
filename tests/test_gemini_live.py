"""No live credentials: transport, timing migration, hidden input and TCP mocks."""
import json
import io
import sqlite3
from contextlib import closing
from unittest.mock import Mock
from urllib.error import HTTPError
import pytest
from app.ai_explanations import GeminiProvider,ProviderError,safe_features,ExplanationService
from tests.test_ai_explanations import Provider,OUTPUT,KEY,app_fixture,wait
from tests.test_gemini import opener_for
from tools import verify_gemini_live as live


@pytest.mark.parametrize('extra',[{'path':'private/file'},{'ip':'192.0.2.3'},{'token':'secret'}])
def test_provider_rejects_extra_sensitive_fields_before_http(extra):
    opener=Mock()
    with pytest.raises(ProviderError,match='invalid_features'):
        GeminiProvider(KEY,'gemini-fixture',opener=opener).analyze({**safe_features('..','BLOCK',True),**extra})
    opener.open.assert_not_called()


@pytest.mark.parametrize('timeout,tokens',[(float('nan'),2048),(20,0),(20,8193)])
def test_gemini_invalid_limits_rejected(timeout,tokens):
    with pytest.raises(ValueError):GeminiProvider(KEY,'gemini-fixture',timeout,max_tokens=tokens)


def test_gemini_extended_limits_and_request_schema():
    opener=opener_for({'choices':[{'finish_reason':'stop','message':{'content':json.dumps(OUTPUT)}}]})
    provider=GeminiProvider(KEY,'gemini-fixture',timeout=45,max_tokens=4096,opener=opener)
    assert provider.analyze(safe_features('..','BLOCK',True))==OUTPUT
    assert opener.open.call_args.kwargs['timeout']==45
    assert json.loads(opener.open.call_args.args[0].data)['max_tokens']==4096


def test_key_accidentally_entered_as_model_is_rejected():
    with pytest.raises(ValueError,match='Credential must not appear'):
        GeminiProvider(KEY,KEY)


@pytest.mark.parametrize('code,reason',[(400,'invalid_request'),(404,'model_unavailable')])
def test_sanitized_compatibility_errors(code,reason):
    opener=Mock();opener.open.side_effect=HTTPError('https://example.test',code,'SECRET_RESPONSE',{},None)
    with pytest.raises(ProviderError,match='^'+reason+'$'):
        GeminiProvider(KEY,'gemini-fixture',opener=opener).analyze(safe_features('..','BLOCK',True))


@pytest.mark.parametrize('message,reason,diagnostic',[
    ('API key not valid '+KEY,'API_KEY_INVALID','api_key_invalid'),
    ('API key expired '+KEY,'API_KEY_EXPIRED','api_key_expired'),
    ('Key restriction '+KEY,'API_KEY_SERVICE_BLOCKED','api_key_restricted')])
def test_google_400_authentication_is_classified_without_raw_body(message,reason,diagnostic):
    body=json.dumps({'error':{'message':message,'details':[{'reason':reason}]}}).encode()
    opener=Mock();opener.open.side_effect=HTTPError('https://example.test',400,'Bad Request',{},io.BytesIO(body))
    with pytest.raises(ProviderError) as caught:
        GeminiProvider(KEY,'gemini-fixture',opener=opener).analyze(safe_features('..','BLOCK',True))
    assert str(caught.value)=='authentication' and caught.value.diagnostic==diagnostic
    assert KEY not in repr(caught.value.__dict__)+repr(caught.value)


def test_list_models_sends_no_event_and_returns_validated_ids():
    opener=opener_for({'data':[{'id':'models/gemini-text-fixture'},{'id':'gemini-chat-fixture'}]})
    provider=GeminiProvider(KEY,'discovery',opener=opener)
    assert provider.list_models()==['gemini-chat-fixture','gemini-text-fixture']
    request=opener.open.call_args.args[0]
    assert request.get_method()=='GET' and request.data is None and request.full_url.endswith('/openai/models')


def test_list_models_cannot_echo_key():
    with pytest.raises(ProviderError,match='invalid_response'):
        GeminiProvider(KEY,'discovery',opener=opener_for({'data':[{'id':KEY}]})).list_models()


def test_prompt_explicitly_overrides_existing_environment_key(monkeypatch):
    monkeypatch.setenv('AI_EXPLANATION_API_KEY','old-fixture-key');monkeypatch.setenv('AI_EXPLANATION_MODEL','gemini-fixture')
    monkeypatch.setattr(live.sys.stdin,'isatty',lambda:True)
    monkeypatch.setattr(live.getpass,'getpass',lambda _:KEY)
    assert live.read_configuration(True,force_key=True)
    assert live.os.environ['AI_EXPLANATION_API_KEY']==KEY


@pytest.mark.parametrize('error',[None,ProviderError('quota'),ProviderError('timeout')])
def test_timings_saved_and_rendered_for_success_or_error(tmp_path,error):
    app,client=app_fixture(tmp_path,Provider(error));service=app.extensions['ai_explanations'];service.set_enabled(True)
    try:
        client.get('/download?path=../fixture');wait(service)
        item=service.snapshot(1)['rows'][0]
        assert item['duration_ms']>=0 and item['completed']>=item['started']
        page=client.get('/dashboard/events/1')
        assert page.status_code==200 and 'Thời gian phân tích API'.encode() in page.data
        client.get('/download?path=../other');wait(service)
        assert service.snapshot(2)['rows'][0]['duration_ms'] is None  # cache never invents fresh API duration
    finally:service.close()


def test_old_sidecar_snapshot_without_timing_table_is_readable(tmp_path):
    path=tmp_path/'old.sqlite3'
    with closing(sqlite3.connect(path)) as db,db:
        db.executescript('CREATE TABLE settings(id INTEGER,enabled INTEGER);CREATE TABLE cache(fingerprint TEXT,status TEXT,output TEXT);CREATE TABLE analyses(event_id INTEGER,created REAL,fingerprint TEXT,status TEXT,output TEXT);')
        db.execute('INSERT INTO analyses VALUES(1,1,?,?,?)',('old','success',json.dumps(OUTPUT)))
    snapshot=ExplanationService(path).snapshot(1)
    assert not snapshot['unavailable'] and snapshot['rows'][0]['duration_ms'] is None


def test_hidden_prompt_no_echo_fallback(tmp_path,monkeypatch):
    monkeypatch.delenv('AI_EXPLANATION_API_KEY',raising=False)
    monkeypatch.setattr(live.sys.stdin,'isatty',lambda:False)
    prompt=Mock();monkeypatch.setattr(live.getpass,'getpass',prompt)
    with pytest.raises(ValueError,match='secure_terminal_required'):live.read_configuration(True)
    prompt.assert_not_called()


@pytest.mark.parametrize('error',[None,ProviderError('quota'),ProviderError('network')])
def test_complete_tcp_pipeline_mock_and_api_outage(tmp_path,monkeypatch,error):
    monkeypatch.setattr(live,'ROOT',tmp_path)
    provider=Provider(error);provider.model='gemini-fixture';provider.timeout=.1
    report={'mode':'MOCK_ONLY'}
    live.verify_pipeline(provider,report)
    assert report['mode']=='MOCK_ONLY'
    assert report['status']==('FAIL' if error else 'PASS')
    assert report['download_http']==403 and report['event']['action']=='BLOCK'
    assert next(c for c in report['checks'] if c['name']=='Security Alert already persisted')['result']=='PASS'
    assert len(provider.calls)==2
    assert all('path' not in f and 'ip' not in f for f in provider.calls)


def test_missing_configuration_is_not_run_without_secret_output(tmp_path,monkeypatch,capsys):
    monkeypatch.setattr(live,'ROOT',tmp_path)
    monkeypatch.delenv('AI_EXPLANATION_API_KEY',raising=False);monkeypatch.delenv('AI_EXPLANATION_MODEL',raising=False)
    assert live.main([])==2
    report=json.loads(next(tmp_path.glob('docs/h07/evidence/gemini_live_*/report.json')).read_text())
    assert report['status']=='NOT_RUN' and 'checks' not in report
    assert 'NOT_RUN' in capsys.readouterr().out


def test_launcher_passes_environment_without_key_on_command_line(monkeypatch,capsys):
    from tools import run_with_gemini as launcher
    monkeypatch.setenv('AI_EXPLANATION_API_KEY',KEY);monkeypatch.setenv('AI_EXPLANATION_MODEL','gemini-fixture')
    monkeypatch.setenv('AI_EXPLANATION_PROVIDER','openai-compatible')
    called=[]
    def run(path,run_name):
        called.append((launcher.os.environ['AI_EXPLANATION_API_KEY'],launcher.os.environ['AI_EXPLANATION_PROVIDER']))
    monkeypatch.setattr(launcher.runpy,'run_path',run)
    assert launcher.main()==0 and called==[(KEY,'gemini')]
    assert KEY not in capsys.readouterr().out


def test_launcher_missing_key_never_starts_server(monkeypatch):
    from tools import run_with_gemini as launcher
    monkeypatch.delenv('AI_EXPLANATION_API_KEY',raising=False);monkeypatch.delenv('AI_EXPLANATION_MODEL',raising=False)
    monkeypatch.setattr(launcher.sys.stdin,'isatty',lambda:False)
    run=Mock();monkeypatch.setattr(launcher.runpy,'run_path',run)
    assert launcher.main()==2
    run.assert_not_called()
