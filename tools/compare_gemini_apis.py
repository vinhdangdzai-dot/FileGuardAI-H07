"""Same-key/model comparison: <=3 diagnostics + <=2 fixture calls, no retries."""
import argparse
from datetime import datetime,timezone
import getpass
import json
import os
from pathlib import Path
import secrets
import sys
import threading
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.ai_explanations import GeminiProvider,GeminiNativeProvider,ProviderError
from tools.verify_gemini_live import read_configuration,verify_pipeline


class RequestBudget:
    """Shared by both provider transports; failed attempts also consume budget."""
    def __init__(self,maximum=5):self.maximum=maximum;self.used=0;self.lock=threading.Lock()
    def wrap(self,opener):
        budget=self
        class BoundedOpener:
            def open(self,*args,**kwargs):
                with budget.lock:
                    if budget.used>=budget.maximum:raise ProviderError('request_budget_exhausted')
                    budget.used+=1
                return opener.open(*args,**kwargs)
        return BoundedOpener()


def call_once(provider,method):
    started=time.perf_counter()
    endpoint=provider.endpoint.removesuffix(':generateContent') if method=='model_info' else provider.endpoint
    result={'provider':provider.name,'model':provider.model,'endpoint':endpoint,
            'operation':method,'timeout_seconds':provider.timeout}
    try:result.update(status='PASS',metadata=getattr(provider,method)())
    except ProviderError as error:result.update(status='FAIL',error=error.metadata())
    result['duration_ms']=(time.perf_counter()-started)*1000
    return result


def compare(native,compatible,report):
    if native.key!=compatible.key or native.model!=compatible.model:raise ValueError('Same credentials and model required')
    report['same_key_and_model']=True
    report['max_http_requests']=5
    report['minimal_native']=call_once(native,'probe_minimal')
    report['minimal_openai_compatible']=call_once(compatible,'probe_minimal')
    report['native_model_metadata']=call_once(native,'model_info')
    n=report['minimal_native'];c=report['minimal_openai_compatible']
    if n['status']=='PASS':
        chosen=native
        report['conclusion']='native_generation_succeeded_compatibility_failed' if c['status']=='FAIL' else 'both_minimal_generations_succeeded'
    elif c['status']=='PASS':
        chosen=compatible;report['conclusion']='compatibility_generation_succeeded_native_failed'
    else:
        both404=all(item.get('error',{}).get('http_status')==404 for item in (n,c))
        report['conclusion']='both_404_model_endpoint_or_access_unavailable' if both404 else 'generation_failed_or_inconclusive'
        report['pipeline']={'status':'NOT_RUN','reason':'no_successful_minimal_generation; no repeated failed requests'}
        report['status']='FAIL';return
    # Explicit test-only selection. No deployment setting or model is changed.
    report['selected_for_fixture_only']=chosen.name
    pipeline={'mode':report.get('mode','LIVE_GOOGLE_API')}
    verify_pipeline(chosen,pipeline)
    report['pipeline']=pipeline
    report['integration_status']=pipeline['status']
    # The comparison may expose a failed endpoint even if the chosen integration works.
    report['status']='PASS' if pipeline['status']=='PASS' and all(r['status']=='PASS' for r in (n,c,report['native_model_metadata'])) else 'FAIL'


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prompt-key',action='store_true')
    parser.add_argument('--model',help='Nonsecret model ID; no automatic substitution')
    args=parser.parse_args(argv)
    out=ROOT/'docs/h07/evidence'/('gemini_compare_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+secrets.token_hex(3));out.mkdir(parents=True)
    report={'mode':'LIVE_GOOGLE_API','status':'NOT_RUN','created_at_utc':datetime.now(timezone.utc).isoformat()}
    original_key=os.environ.get('AI_EXPLANATION_API_KEY');original_model=os.environ.get('AI_EXPLANATION_MODEL')
    try:
        if args.model:os.environ['AI_EXPLANATION_MODEL']=args.model
        read_configuration(args.prompt_key,force_key=args.prompt_key)
        key=os.environ.get('AI_EXPLANATION_API_KEY');model=os.environ.get('AI_EXPLANATION_MODEL')
        if not key or not model:report['reason']='missing_api_key_or_model'
        else:
            options={'timeout':os.environ.get('AI_EXPLANATION_TIMEOUT','20'),'max_tokens':os.environ.get('AI_EXPLANATION_MAX_TOKENS','2048')}
            native=GeminiNativeProvider(key,model,**options);compatible=GeminiProvider(key,model,**options)
            report['model']=model
            budget=RequestBudget()
            native.opener=budget.wrap(native.opener);compatible.opener=budget.wrap(compatible.opener)
            try:compare(native,compatible,report)
            finally:report['http_requests_attempted']=budget.used
    except (ValueError,TypeError,getpass.GetPassWarning,EOFError):report.update(status='NOT_RUN',reason='invalid_configuration_or_secure_terminal_required')
    except KeyboardInterrupt:report.update(status='NOT_RUN',reason='interrupted_by_operator')
    except Exception:report.update(status='FAIL',reason='local_verification_error')
    finally:
        for name,value in [('AI_EXPLANATION_API_KEY',original_key),('AI_EXPLANATION_MODEL',original_model)]:
            if value is None:os.environ.pop(name,None)
            else:os.environ[name]=value
        (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Comparison:',report['status'],'Integration:',report.get('integration_status','NOT_RUN'))
    print('Conclusion:',report.get('conclusion',report.get('reason')))
    print('Evidence:',out.relative_to(ROOT))
    return 0 if report['status']=='PASS' else 2 if report['status']=='NOT_RUN' else 1


if __name__=='__main__':raise SystemExit(main())
