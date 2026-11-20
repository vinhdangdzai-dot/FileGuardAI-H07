"""Bounded same-key diagnostics; no real key, Google calls or model deployment."""
import io
import json
from unittest.mock import Mock
from urllib.error import HTTPError
import pytest
from app.ai_explanations import GeminiProvider,GeminiNativeProvider,ProviderError
from tests.test_gemini import opener_for,KEY
from tools import compare_gemini_apis as comparison
from tools import verify_gemini_live as live
from tests.test_ai_explanations import OUTPUT


def response(body,status=200):
    stream=io.BytesIO(json.dumps(body).encode());stream.status=status
    return stream


def test_minimal_pair_uses_same_key_model_prompt_without_json_mode():
    native_open=opener_for({'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':'OK'}]}}]})
    compat_open=opener_for({'choices':[{'finish_reason':'stop','message':{'content':'OK'}}]})
    native=GeminiNativeProvider(KEY,'gemini-2.5-flash-lite',opener=native_open)
    compatible=GeminiProvider(KEY,'gemini-2.5-flash-lite',opener=compat_open)
    assert native.probe_minimal()['content_nonempty'] and compatible.probe_minimal()['content_nonempty']
    nr=native_open.open.call_args.args[0];cr=compat_open.open.call_args.args[0]
    nb=json.loads(nr.data);cb=json.loads(cr.data)
    assert nr.get_header('X-goog-api-key')==cr.get_header('Authorization').removeprefix('Bearer ')==KEY
    assert nb['contents'][0]['parts'][0]['text']==cb['messages'][0]['content']=='Reply with OK.'
    assert 'responseMimeType' not in nb['generationConfig'] and 'response_format' not in cb
    assert KEY not in nr.data.decode()+cr.data.decode()


def test_exact_model_metadata_reports_methods_not_catalog_assumption():
    opener=opener_for({'name':'models/gemini-fixture','supportedGenerationMethods':['generateContent','countTokens'],'description':KEY})
    provider=GeminiNativeProvider(KEY,'gemini-fixture',opener=opener)
    info=provider.model_info()
    assert info['generate_content_supported'] and info['supported_methods']==['generateContent','countTokens']
    assert KEY not in json.dumps(info)
    request=opener.open.call_args.args[0]
    assert request.get_method()=='GET' and request.full_url.endswith('/models/gemini-fixture')


def test_rpc_error_code_is_allowlisted_and_body_never_persisted():
    opener=Mock();opener.open.side_effect=HTTPError('https://example.test',404,'SECRET',{},io.BytesIO(json.dumps({'error':{'status':'NOT_FOUND','message':KEY}}).encode()))
    provider=GeminiNativeProvider(KEY,'gemini-fixture',opener=opener)
    with pytest.raises(ProviderError) as caught:provider.probe_minimal()
    assert caught.value.metadata()['upstream_status']=='NOT_FOUND'
    assert caught.value.http_status==404 and KEY not in json.dumps(caught.value.metadata())


class FakeProvider:
    def __init__(self,name,error=None):
        self.name=name;self.model='gemini-fixture';self.key=KEY;self.timeout=.1
        self.endpoint='https://example.test/models/gemini-fixture:generateContent';self.error=error;self.calls=0
    def probe_minimal(self):
        self.calls+=1
        if self.error:raise self.error
        return {'http_status':200,'content_nonempty':True}
    def model_info(self):self.calls+=1;return {'supported_methods':['generateContent']}


def test_native_success_selects_only_test_fixture_and_keeps_comparison_failure(monkeypatch):
    native=FakeProvider('gemini-native');compat=FakeProvider('gemini',ProviderError('model_unavailable',http_status=404))
    selected=[]
    def pipeline(provider,report):selected.append(provider);report['status']='PASS'
    monkeypatch.setattr(comparison,'verify_pipeline',pipeline)
    report={'mode':'MOCK_ONLY'};comparison.compare(native,compat,report)
    assert report['selected_for_fixture_only']=='gemini-native' and selected==[native]
    assert report['integration_status']=='PASS' and report['status']=='FAIL'
    assert native.calls==2 and compat.calls==1 and report['max_http_requests']==5


def test_both_404_stops_without_repeat_generations(monkeypatch):
    native=FakeProvider('gemini-native',ProviderError('model_unavailable',http_status=404))
    compat=FakeProvider('gemini',ProviderError('model_unavailable',http_status=404))
    pipeline=Mock();monkeypatch.setattr(comparison,'verify_pipeline',pipeline)
    report={'mode':'MOCK_ONLY'};comparison.compare(native,compat,report)
    assert report['status']=='FAIL' and report['conclusion']=='both_404_model_endpoint_or_access_unavailable'
    assert report['pipeline']['status']=='NOT_RUN'
    pipeline.assert_not_called();assert native.calls==2 and compat.calls==1


def test_mismatched_credentials_rejected_before_requests():
    native=FakeProvider('gemini-native');compat=FakeProvider('gemini');compat.key='other-fixture-key'
    with pytest.raises(ValueError):comparison.compare(native,compat,{})
    assert native.calls==compat.calls==0


def test_shared_request_budget_stops_sixth_call_before_network():
    budget=comparison.RequestBudget(5);first=Mock();second=Mock()
    a=budget.wrap(first);b=budget.wrap(second)
    for _ in range(3):a.open('fixture')
    for _ in range(2):b.open('fixture')
    with pytest.raises(ProviderError,match='request_budget_exhausted'):b.open('fixture')
    assert budget.used==5 and first.open.call_count+second.open.call_count==5


def test_native_adapter_full_tcp_pipeline_with_failed_compatible_endpoint(tmp_path,monkeypatch):
    monkeypatch.setattr(live,'ROOT',tmp_path)
    def native_response(text):return {'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':text}]}}]}
    bodies=[native_response('OK'),{'name':'models/gemini-fixture','supportedGenerationMethods':['generateContent']},
            native_response(json.dumps(OUTPUT)),native_response(json.dumps(OUTPUT))]
    opened=[]
    opener=Mock()
    def open_native(request,**kwargs):
        opened.append(request)
        return response(bodies[len(opened)-1])
    opener.open.side_effect=open_native
    failed=Mock();failed.open.side_effect=HTTPError('https://example.test',404,'Not Found',{},io.BytesIO(b'{}'))
    budget=comparison.RequestBudget()
    native=GeminiNativeProvider(KEY,'gemini-fixture',opener=budget.wrap(opener))
    compat=GeminiProvider(KEY,'gemini-fixture',opener=budget.wrap(failed))
    report={'mode':'MOCK_ONLY'};comparison.compare(native,compat,report)
    assert report['status']=='FAIL' and report['integration_status']=='PASS'
    assert report['pipeline']['download_http']==403
    assert report['pipeline']['pipeline_analysis']['provider']=='gemini-native'
    assert all(c['result']=='PASS' for c in report['pipeline']['checks'])
    assert budget.used==5 and len(opened)==4 and failed.open.call_count==1


@pytest.mark.parametrize('body',[{}, {'name':'models/other','supportedGenerationMethods':['generateContent']},
    {'name':'models/gemini-fixture','supportedGenerationMethods':[{'private':KEY}]}])
def test_invalid_metadata_is_not_success(body):
    provider=GeminiNativeProvider(KEY,'gemini-fixture',opener=opener_for(body))
    with pytest.raises(ProviderError,match='invalid_response'):provider.model_info()
