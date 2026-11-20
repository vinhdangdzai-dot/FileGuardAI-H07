import io
import json
from unittest.mock import Mock
from urllib.error import HTTPError
import pytest
from app.ai_explanations import GeminiProvider,ProviderError,safe_features
from tests.test_ai_explanations import Provider,OUTPUT,KEY
from tools import verify_gemini_live as live

@pytest.mark.parametrize('http,category,retryable',[(503,'temporary_api',True),(400,'configuration',False),(401,'configuration',False),(404,'configuration',False),(429,'temporary_api',True)])
def test_http_metadata_never_exposes_body(http,category,retryable):
    opener=Mock();opener.open.side_effect=HTTPError('https://example.test',http,'SECRET',{},io.BytesIO(KEY.encode()))
    provider=GeminiProvider(KEY,'fixture',opener=opener)
    with pytest.raises(ProviderError) as caught:provider.analyze(safe_features('..','BLOCK',True))
    meta=caught.value.metadata()
    assert meta['http_status']==http and meta['category']==category and meta['retryable']==retryable
    assert KEY not in json.dumps(meta) and 'SECRET' not in json.dumps(meta)

def test_successful_pipeline_does_not_erase_failed_probe(tmp_path,monkeypatch):
    monkeypatch.setattr(live,'ROOT',tmp_path)
    provider=Provider();provider.model='fixture';provider.timeout=.1
    def analyze(features):
        provider.calls.append(features)
        if len(provider.calls)==1:raise ProviderError('provider_error',http_status=503)
        return OUTPUT
    provider.analyze=analyze
    report={'mode':'MOCK_ONLY'};live.verify_pipeline(provider,report)
    assert report['status']=='FAIL' and report['probe']['status']=='FAIL'
    assert report['pipeline_analysis']['status']=='success' and report['download_http']==403
    assert report['probe']['error']['http_status']==503
    assert [a['phase'] for a in report['request_attempts']]==['probe','pipeline']
    assert report['request_attempts'][0]['features']['structural_encoding'] is False
    assert report['request_attempts'][1]['features']['structural_encoding'] is True

def test_response_processing_and_utf8_roundtrip(tmp_path):
    opener=Mock();response=io.BytesIO(b'not json');response.status=200
    opener.open.return_value.__enter__=Mock(return_value=response)
    opener.open.return_value.__exit__=Mock(return_value=False)
    provider=GeminiProvider(KEY,'fixture',opener=opener)
    with pytest.raises(ProviderError) as caught:provider.analyze(safe_features('..','BLOCK',True))
    assert caught.value.category=='response_processing' and not caught.value.retryable
    assert provider.last_response_meta['http_status']==200
    text='Phát hiện mã hóa đường dẫn; chính sách độc lập quyết định chặn.'
    path=tmp_path/'report.json';path.write_text(json.dumps({'why':text},ensure_ascii=False),encoding='utf-8')
    assert json.loads(path.read_text(encoding='utf-8'))['why']==text
