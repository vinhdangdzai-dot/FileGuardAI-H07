"""Explicit live Gemini probe + isolated TCP pipeline. Never accepts a key argument."""
import argparse
from contextlib import closing
from datetime import datetime, timezone
import getpass
import hashlib
from http.cookiejar import CookieJar
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import sys
import threading
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import build_opener, HTTPCookieProcessor, ProxyHandler
import warnings

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app import create_app
from app.ai_explanations import GeminiProvider,GeminiNativeProvider,ProviderError,safe_features,validate_features,validate_output
from markupsafe import escape
from tools.pytest_runtime import create_runtime
from werkzeug.serving import make_server


def read_configuration(prompt=False,*,prompt_model=True,force_key=False):
    """Hidden input only with a real terminal; refuse getpass echo fallback."""
    if prompt and not sys.stdin.isatty():raise ValueError('secure_terminal_required')
    entered=False
    if prompt and (force_key or not os.environ.get('AI_EXPLANATION_API_KEY')):
        with warnings.catch_warnings():
            warnings.simplefilter('error',getpass.GetPassWarning)
            key=getpass.getpass('Gemini API key (hidden, memory only): ').strip()
        if not key:raise ValueError('Invalid AI key format')
        os.environ['AI_EXPLANATION_API_KEY']=key;entered=True
    if not os.environ.get('AI_EXPLANATION_MODEL') and prompt and prompt_model:
        os.environ['AI_EXPLANATION_MODEL']=input('Gemini model ID available to your project: ').strip()
    return entered


class RecordingProvider:
    name='gemini'
    def __init__(self,provider):
        self.provider=provider;self.name=getattr(provider,'name','gemini');self.identity=provider.identity;self.model=provider.model;self.timeout=provider.timeout;self.sent=[];self.errors=[]
        self.phase='probe';self.attempts=[]
    def analyze(self,features):
        clean=validate_features(features);self.sent.append(clean)
        attempt={'phase':self.phase,'features':clean,'model':self.model,'timeout_seconds':self.timeout,
                 'endpoint':getattr(self.provider,'endpoint',None),'max_tokens':getattr(self.provider,'max_tokens',None)}
        if hasattr(self.provider,'make_request'):
            request=self.provider.make_request(clean)
            attempt['request_sha256']=hashlib.sha256(request.data).hexdigest()
        self.attempts.append(attempt)
        started=time.perf_counter()
        try:
            result=self.provider.analyze(clean)
            attempt['status']='success'
            return result
        except ProviderError as error:
            attempt.update(status='failed',error=error.metadata())
            self.errors.append({'phase':self.phase,**error.metadata()})
            raise
        finally:
            attempt['duration_ms']=(time.perf_counter()-started)*1000
            attempt['response_metadata']=getattr(self.provider,'last_response_meta',{})


def language_observations(result):
    # A documented heuristic, never presented as semantic or factual validation.
    return {field:bool(re.search('[àáảãạăằắẳẵặâầấẩẫậđèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵ]',result[field],re.I))
            for field in ('why','traversal_type','recommendations')}


def verify_pipeline(provider,report):
    protected=[ROOT/'data/paths_synthetic.csv',ROOT/'artifacts/model.joblib',ROOT/'instance/events.sqlite3']
    before={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected if p.is_file()}
    checks=report.setdefault('checks',[])
    def check(name,passed):checks.append({'name':name,'result':'PASS' if passed else 'FAIL'})
    recording=RecordingProvider(provider)
    started=time.perf_counter()
    try:
        result=validate_output(recording.analyze(safe_features('../synthetic-probe','BLOCK',True)))
        report['probe']={'status':'PASS','duration_ms':(time.perf_counter()-started)*1000,'analysis':result,
                         'vietnamese_diacritics_heuristic':language_observations(result),'human_review_required':True}
    except ProviderError as error:
        report['probe']={'status':'FAIL','reason':str(error),'error':error.metadata(),'duration_ms':(time.perf_counter()-started)*1000}
    recording.phase='pipeline'
    runtime=create_runtime(ROOT)
    public=runtime['root']/'public';public.mkdir();(public/'ok.txt').write_bytes(b'PUBLIC')
    password=secrets.token_hex(24)
    app=create_app({'TESTING':True,'CSRF_ENABLED':True,'FILES_ROOT':public,'DATABASE':runtime['root']/'events.sqlite3',
                    'ADMIN_PASSWORD':password,'AI_EXPLANATION_ADAPTER':recording})
    service=app.extensions['ai_explanations'];service.set_enabled(True)
    server=make_server('127.0.0.1',0,app,threaded=True)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base='http://127.0.0.1:'+str(server.server_port)
    client=build_opener(ProxyHandler({}),HTTPCookieProcessor(CookieJar()))
    def fetch(path,data=None):
        try:
            with client.open(base+path,data=urlencode(data).encode() if data else None,timeout=10) as response:
                return response.status,response.read().decode('utf-8',errors='replace')
        except HTTPError as error:
            try:return error.code,error.read().decode('utf-8',errors='replace')
            finally:error.close()
    def rows(sql):
        with closing(sqlite3.connect(app.config['DATABASE'])) as db:
            db.row_factory=sqlite3.Row
            return [dict(r) for r in db.execute(sql)]
    try:
        status,login=fetch('/login')
        csrf=re.search(r'name="csrf_token" value="([^"]+)"',login)[1]
        status,_=fetch('/login',{'csrf_token':csrf,'password':password})
        from tools.mfa_fixture import Authenticator
        authenticator=Authenticator()
        status,mfa_form=fetch('/login/mfa')
        mfa_csrf=re.search(r'name="csrf_token" value="([^"]+)"',mfa_form)[1]
        status,mfa_result=fetch('/login/mfa',{'csrf_token':mfa_csrf,'code':authenticator.factor(mfa_form)})
        authenticator.remember(mfa_result)
        status,_=fetch('/dashboard')
        check('Admin authenticated with TOTP over TCP',status==200)
        started=time.perf_counter()
        status,_=fetch('/download?path=%252e%252e%252fsynthetic-fixture')
        report['download_http']=status;report['download_duration_ms']=(time.perf_counter()-started)*1000
        logs=rows('SELECT id,action,http_status,ml_score,ml_label FROM access_logs ORDER BY id DESC LIMIT 1')
        event=logs[0];event_id=event['id'];report['event']=event
        check('Traversal BLOCK 403 before waiting for Gemini',status==403 and event['action']=='BLOCK' and event['http_status']==403)
        linked=rows('SELECT alert_id FROM alert_events WHERE event_id='+str(event_id))
        check('Security Alert already persisted',bool(linked))
        deadline=time.monotonic()+3*provider.timeout+15
        analysis=None
        while time.monotonic()<deadline:
            snapshot=service.snapshot(event_id)
            if snapshot['rows']:
                analysis=snapshot['rows'][0]
                if analysis['status'] not in ('pending','waiting'):break
            time.sleep(.25)
        report['pipeline_analysis']=analysis
        check('Gemini pipeline explanation succeeded',bool(analysis and analysis['status']=='success' and analysis['analysis']))
        check('API duration recorded',bool(analysis and analysis.get('duration_ms') is not None and analysis['duration_ms']>=0))
        dashboard_status,dashboard=fetch('/dashboard')
        detail_status,detail=fetch('/dashboard/events/'+str(event_id))
        if analysis and analysis['analysis']:
            why=str(escape(analysis['analysis']['why']))
            check('Dashboard renders returned explanation',dashboard_status==200 and why in dashboard)
            check('Event detail renders explanation and timing',detail_status==200 and why in detail and 'Thời gian phân tích' in detail)
            report['pipeline_language_heuristic']=language_observations(analysis['analysis'])
        else:
            check('Dashboard remains available on API failure',dashboard_status==200 and detail_status==200)
        after=rows('SELECT action,http_status FROM access_logs WHERE id='+str(event_id))[0]
        check('AI cannot modify BLOCK or alert',after=={'action':'BLOCK','http_status':403} and bool(linked))
        service.set_enabled(False)  # The explicit verification budget is two live calls.
        check('Benign file still downloads',fetch('/download?path=ok.txt')[0]==200)
        report['outbound_event_features']=recording.sent
        report['provider_diagnostics']=recording.errors
        report['request_attempts']=recording.attempts
        check('Only allowlisted coarse fields sent',all(validate_features(item)==item for item in recording.sent))
        report['runtime']=str(runtime['root'].relative_to(ROOT))
    finally:
        service.close();server.shutdown();server.server_close();thread.join(timeout=5)
        report['protected_unchanged']={path:hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest for path,digest in before.items()}
    report['status']='PASS' if report['probe']['status']=='PASS' and all(c['result']=='PASS' for c in checks) and all(report['protected_unchanged'].values()) else 'FAIL'
    report['human_review_required']=True
    if analysis and analysis.get('analysis'):
        text=json.dumps(analysis['analysis'],ensure_ascii=False)
        report['encoding_audit']={'format':'UTF-8 JSON without BOM','replacement_characters':text.count('\ufffd'),
                                  'note':'Read PowerShell with Get-Content -Encoding UTF8; diacritics alone do not validate meaning.'}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prompt-key',action='store_true',help='Hidden input in your own VS Code terminal, never via chat')
    parser.add_argument('--choose-model',action='store_true',help='One extra metadata API call, then choose an actual returned model ID')
    parser.add_argument('--native',action='store_true',help='Use native generateContent with x-goog-api-key')
    args=parser.parse_args(argv)
    out=ROOT/'docs/h07/evidence'/('gemini_live_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+secrets.token_hex(3));out.mkdir(parents=True)
    report={'mode':'LIVE_GOOGLE_API','created_at_utc':datetime.now(timezone.utc).isoformat(),'status':'NOT_RUN'}
    original=os.environ.get('AI_EXPLANATION_API_KEY')
    try:
        read_configuration(args.prompt_key,prompt_model=not args.choose_model,force_key=args.prompt_key)
        key=os.environ.get('AI_EXPLANATION_API_KEY');model=os.environ.get('AI_EXPLANATION_MODEL')
        if args.choose_model and key:
            if not sys.stdin.isatty():raise ValueError('secure_terminal_required')
            discovery=GeminiNativeProvider if args.native else GeminiProvider
            models=discovery(key,'model-discovery',os.environ.get('AI_EXPLANATION_TIMEOUT','20')).list_models()
            report['model_discovery']={'status':'PASS','models':models}
            print('Models returned by Google (choose a text/chat model):')
            for index,identifier in enumerate(models,1):print(str(index)+'. '+identifier)
            choice=int(input('Model number: ').strip())
            if not 1<=choice<=len(models):raise ValueError('Invalid AI model identifier')
            model=models[choice-1]
            os.environ['AI_EXPLANATION_MODEL']=model
        if not key or not model:report['reason']='missing_api_key_or_model'
        else:
            provider_class=GeminiNativeProvider if args.native else GeminiProvider
            provider=provider_class(key,model,os.environ.get('AI_EXPLANATION_TIMEOUT','20'),max_tokens=os.environ.get('AI_EXPLANATION_MAX_TOKENS','2048'))
            report['provider']=provider.name
            report['model']=provider.model;report['timeout_seconds']=provider.timeout;report['max_tokens']=provider.max_tokens
            verify_pipeline(provider,report)
    except ProviderError as error:
        report['status']='FAIL';report['provider_diagnostics']=[{'code':str(error),'diagnostic':error.diagnostic}]
    except (ValueError,TypeError,getpass.GetPassWarning,EOFError) as error:
        known={'secure_terminal_required':'secure_terminal_required',
               'Invalid AI model identifier':'invalid_model_identifier',
               'Invalid AI key format':'invalid_api_key_format',
               'Invalid Gemini timeout':'invalid_timeout',
               'Invalid Gemini token limit':'invalid_token_limit',
               'Credential must not appear in model or endpoint':'credential_used_as_model_or_endpoint'}
        report['status']='NOT_RUN'
        report['reason']=('secure_terminal_unavailable' if isinstance(error,(getpass.GetPassWarning,EOFError)) else known.get(str(error),'invalid_configuration'))
    except KeyboardInterrupt:report['status']='NOT_RUN';report['reason']='interrupted_by_operator'
    except Exception:
        report['status']='FAIL';report['reason']='local_verification_error'  # Never expose exception text/headers/key.
    finally:
        if original is None:os.environ.pop('AI_EXPLANATION_API_KEY',None)
        else:os.environ['AI_EXPLANATION_API_KEY']=original
        (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Gemini live:',report['status'])
    if report.get('reason'):print('Reason:',report['reason'])
    for code,hint in sorted({(item['code'],item.get('diagnostic') or 'not_provided') for item in report.get('provider_diagnostics',[])}):
        print('API status:',code,'Diagnostic:',hint)
    print('Evidence:',out.relative_to(ROOT))
    return 0 if report['status']=='PASS' else 2 if report['status']=='NOT_RUN' else 1


if __name__=='__main__':raise SystemExit(main())
