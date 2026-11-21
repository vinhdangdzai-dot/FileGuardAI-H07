"""Native API contract with fake credentials only."""
import json
import pytest
from app.ai_explanations import GeminiNativeProvider,ProviderError,safe_features
from tests.test_gemini import opener_for,KEY,OUTPUT

def test_native_wire_contract():
    opener=opener_for({'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':json.dumps(OUTPUT)}]}}]})
    provider=GeminiNativeProvider(KEY,'gemini-2.5-flash',opener=opener)
    assert provider.analyze(safe_features('../PRIVATE','BLOCK',True))==OUTPUT
    request=opener.open.call_args.args[0];body=json.loads(request.data)
    assert request.full_url.endswith('/models/gemini-2.5-flash:generateContent')
    assert request.get_header('X-goog-api-key')==KEY and request.get_header('Authorization') is None
    assert body['generationConfig']=={'maxOutputTokens':2048,'responseMimeType':'application/json'}
    assert KEY not in request.data.decode() and 'PRIVATE' not in request.data.decode()

@pytest.mark.parametrize('candidate',[{},None,{'finishReason':'MAX_TOKENS'}, {'finishReason':'STOP','content':{'parts':[{'text':None}]}}])
def test_native_rejects_invalid_or_truncated(candidate):
    provider=GeminiNativeProvider(KEY,'gemini-fixture',opener=opener_for({'candidates':[candidate]}))
    with pytest.raises(ProviderError,match='invalid_response'):provider.analyze(safe_features('..','BLOCK',True))

def test_native_model_listing_header_and_filter():
    opener=opener_for({'models':[{'name':'models/gemini-fixture','supportedGenerationMethods':['generateContent']},{'name':'models/embedding','supportedGenerationMethods':['embedContent']}]})
    provider=GeminiNativeProvider(KEY,'discovery',opener=opener)
    assert provider.list_models()==['gemini-fixture']
    assert opener.open.call_args.args[0].get_header('X-goog-api-key')==KEY
