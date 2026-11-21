"""One explicit live probe with synthetic coarse features; never print credentials."""
import json
import os
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.ai_explanations import GeminiProvider, ProviderError, safe_features


def main():
    key=os.environ.get('AI_EXPLANATION_API_KEY')
    model=os.environ.get('AI_EXPLANATION_MODEL')
    if not key or not model:
        print(json.dumps({'status':'NOT_RUN','reason':'missing_api_key_or_model'}))
        return 2
    try:
        provider=GeminiProvider(key,model,os.environ.get('AI_EXPLANATION_TIMEOUT','10'))
        result=provider.analyze(safe_features('../synthetic-fixture','BLOCK',True))
    except ProviderError as error:
        print(json.dumps({'status':'FAIL','reason':str(error)}))
        return 1
    except (ValueError,TypeError):
        print(json.dumps({'status':'FAIL','reason':'invalid_configuration'}))
        return 1
    # Do not print provider text or configuration: only validated schema metadata.
    print(json.dumps({'status':'PASS','schema_valid':True,'risk':result['risk'],
                      'fields':sorted(result),'synthetic_features_only':True}))
    return 0


if __name__=='__main__':raise SystemExit(main())
