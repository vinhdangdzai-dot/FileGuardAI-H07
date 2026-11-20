"""Optional advisory explanations. Raw paths never enter queues or providers."""
from contextlib import closing, contextmanager
import hashlib
import json
import math
import queue
import re
import socket
import sqlite3
import threading
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlsplit
from urllib.request import Request, HTTPRedirectHandler, build_opener


def safe_features(raw, decision, suspicious):
    text=raw[:4096]
    views=[text]
    for _ in range(2):views.append(unquote(views[-1],errors='replace'))
    normalized=[v.replace('\\','/') for v in views]
    return {'decision':decision if decision in {'ALLOW','BLOCK','MISS'} else 'BLOCK',
            'ml_alert':bool(suspicious),'parent_components':min(4,max(v.split('/').count('..') for v in normalized)),
            'absolute_style':any(v.startswith('/') or bool(re.match(r'^[A-Za-z]:',v)) for v in normalized),
            'backslash':any('\\' in v for v in views),
            'structural_encoding':any(bool(re.search(r'%(?:2e|2f|5c|25|00)',v,re.I)) for v in views),
            'remaining_decode_changes':min(2,sum(views[i]!=views[i+1] for i in range(2))),
            'length_bucket':'long' if len(raw)>256 else 'medium' if len(raw)>64 else 'short'}


class ProviderError(Exception):
    def __init__(self,code,*,diagnostic=None,http_status=None,upstream_status=None,error_format=None):
        super().__init__(code)
        self.diagnostic=diagnostic
        self.http_status=http_status
        self.upstream_status=upstream_status
        self.error_format=error_format
        self.retryable=http_status in (408,429,500,502,503,504) or code in ('network','timeout')
        self.category=('temporary_api' if self.retryable else 'configuration' if code in
                       ('authentication','invalid_request','model_unavailable','invalid_features') else
                       'response_processing' if code=='invalid_response' else 'unknown_provider')

    def metadata(self):
        return {'code':str(self),'diagnostic':self.diagnostic,'http_status':self.http_status,
                'category':self.category,'retryable':self.retryable,
                'upstream_status':self.upstream_status,'error_format':self.error_format}


def sanitized_google_error(raw):
    """Read error metadata in memory; return constants only, never provider text."""
    try:
        error=json.loads(raw)['error']
        message=error.get('message','').lower()
        reasons={item.get('reason') for item in error.get('details',[]) if isinstance(item,dict) and isinstance(item.get('reason'),str)}
        if 'API_KEY_INVALID' in reasons or 'api key not valid' in message or 'invalid auth key' in message:return 'api_key_invalid'
        if 'API_KEY_EXPIRED' in reasons or ('api key' in message and 'expired' in message):return 'api_key_expired'
        if reasons & {'API_KEY_SERVICE_BLOCKED','API_KEY_HTTP_REFERRER_BLOCKED','API_KEY_IP_ADDRESS_BLOCKED','API_KEY_ANDROID_APP_BLOCKED','API_KEY_IOS_APP_BLOCKED'}:return 'api_key_restricted'
        if 'SERVICE_DISABLED' in reasons:return 'service_disabled'
        if 'response_format' in message or 'responseformat' in message:return 'response_format_rejected'
        if 'max_tokens' in message or 'maxoutputtokens' in message:return 'token_limit_rejected'
        if 'model' in message and any(word in message for word in ('not found','not supported','not available','deprecated')):return 'model_rejected'
    except (ValueError,KeyError,TypeError,AttributeError,UnicodeError):pass
    return None


def provider_http_error(error,*,google=False):
    """Preserve bounded HTTP/RPC metadata, never response text or credentials."""
    code=error.code;diagnostic=None;upstream=None;shape=None
    try:
        if google:
            raw=error.read(65537)
            diagnostic=sanitized_google_error(raw)
            try:
                value=json.loads(raw)['error']
                shape='json_error'
                allowed={'INVALID_ARGUMENT','NOT_FOUND','PERMISSION_DENIED','UNAUTHENTICATED',
                         'RESOURCE_EXHAUSTED','INTERNAL','UNAVAILABLE','DEADLINE_EXCEEDED',
                         'FAILED_PRECONDITION','UNKNOWN','UNIMPLEMENTED','CANCELLED','ABORTED'}
                status=value.get('status') if isinstance(value,dict) else None
                if isinstance(status,str) and status in allowed:upstream=status
            except (ValueError,KeyError,TypeError,UnicodeError):shape='unrecognized_error_body'
    except OSError:shape='unreadable_error_body'
    finally:error.close()
    label=('authentication' if diagnostic in {'api_key_invalid','api_key_expired','api_key_restricted','service_disabled'} else
           'quota' if code==429 else 'authentication' if code in (401,403) else
           'invalid_request' if code==400 else 'model_unavailable' if code==404 else 'provider_error')
    return ProviderError(label,diagnostic=diagnostic,http_status=code,upstream_status=upstream,error_format=shape)


def validate_features(features):
    """Last boundary before HTTP: reject arbitrary text and unknown fields."""
    template=safe_features('', 'ALLOW', False)
    if not isinstance(features,dict) or set(features)!=set(template):raise ProviderError('invalid_features')
    for key in ('ml_alert','absolute_style','backslash','structural_encoding'):
        if type(features[key]) is not bool:raise ProviderError('invalid_features')
    for key,maximum in [('parent_components',4),('remaining_decode_changes',2)]:
        if type(features[key]) is not int or not 0<=features[key]<=maximum:raise ProviderError('invalid_features')
    if features['decision'] not in ('ALLOW','BLOCK','MISS') or features['length_bucket'] not in ('short','medium','long'):
        raise ProviderError('invalid_features')
    return dict(features)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None


class ChatCompletionProvider:
    """HTTPS OpenAI-compatible adapter; endpoint/model configured by operator."""
    name = 'openai-compatible'
    def __init__(self,key,endpoint,model,timeout=3,opener=None):
        parsed=urlsplit(endpoint)
        if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError('AI endpoint must be a credential-free HTTPS URL')
        if not re.fullmatch(r'[A-Za-z0-9._:/-]{1,120}',model):raise ValueError('Invalid AI model identifier')
        if not isinstance(key,str) or not re.fullmatch(r'[!-~]{1,4096}',key):raise ValueError('Invalid AI key format')
        if key in model or key in endpoint:raise ValueError('Credential must not appear in model or endpoint')
        self.key,self.endpoint,self.model,self.timeout=key,endpoint,model,min(10,max(.1,float(timeout)))
        self.opener=opener or build_opener(NoRedirect())
        self.identity=hashlib.sha256((endpoint+'|'+model).encode()).hexdigest()

    def payload(self,features):
        prompt=('Explain security indicators in Vietnamese from coarse boolean/count features only. '
                'No original path or exploit success is known. AI is advisory and cannot authorize downloads. '
                'Return ONLY a JSON object with why (string), traversal_type (string), risk '
                '(low, medium, high or unknown), recommendations (string). Do not invent filenames or people.')
        return {'model':self.model,'messages':[{'role':'system','content':prompt},
                        {'role':'user','content':json.dumps(features,sort_keys=True)}],
                        'max_completion_tokens':600,'store':False}

    def make_request(self,features):
        body=json.dumps(self.payload(validate_features(features))).encode()
        return Request(self.endpoint,data=body,headers={'Authorization':'Bearer '+self.key,'Content-Type':'application/json'},method='POST')

    def response_content(self,raw):
        choice=json.loads(raw)['choices'][0]
        if not isinstance(choice,dict) or choice.get('finish_reason','stop')!='stop':raise ProviderError('invalid_response')
        return choice['message']['content']

    def analyze(self,features):
        self.last_response_meta={}
        request=self.make_request(features)
        try:
            with self.opener.open(request,timeout=self.timeout) as response:
                raw=response.read(65537)
                status=getattr(response,'status',None)
                self.last_response_meta={'http_status':status if type(status) is int else None,'response_bytes':len(raw)}
                if len(raw)>65536:raise ProviderError('invalid_response')
            content=self.response_content(raw)
            if not isinstance(content,str) or self.key in content:raise ProviderError('invalid_response')
            result=validate_output(json.loads(content))
            if any(self.key in value for value in result.values()):raise ProviderError('invalid_response')
            return result
        except HTTPError as error:
            raise provider_http_error(error,google=self.name.startswith('gemini')) from None
        except (TimeoutError,socket.timeout):raise ProviderError('timeout') from None
        except URLError as error:
            raise ProviderError('timeout' if isinstance(error.reason,TimeoutError) else 'network') from None
        except OSError:raise ProviderError('network') from None
        except (ValueError,KeyError,TypeError,IndexError,UnicodeError):raise ProviderError('invalid_response') from None


class GeminiProvider(ChatCompletionProvider):
    """Google's OpenAI-compatible endpoint, without OpenAI-only store options."""
    name = 'gemini'
    def __init__(self,key,model,timeout=20,opener=None,*,max_tokens=2048):
        super().__init__(key,'https://generativelanguage.googleapis.com/v1beta/openai/chat/completions',model,timeout,opener)
        value=float(timeout)
        if not math.isfinite(value):raise ValueError('Invalid Gemini timeout')
        self.timeout=min(60,max(.1,value))
        self.max_tokens=int(max_tokens)
        if not 256<=self.max_tokens<=8192:raise ValueError('Invalid Gemini token limit')
        self.identity=hashlib.sha256((self.identity+'|gemini-json-v3|'+str(self.max_tokens)).encode()).hexdigest()

    def models_request(self):
        return Request('https://generativelanguage.googleapis.com/v1beta/openai/models',
                        headers={'Authorization':'Bearer '+self.key},method='GET')

    def minimal_request(self):
        body={'model':self.model,'messages':[{'role':'user','content':'Reply with OK.'}],'max_tokens':256}
        return Request(self.endpoint,data=json.dumps(body).encode(),headers={'Authorization':'Bearer '+self.key,'Content-Type':'application/json'},method='POST')

    def probe_minimal(self):
        """Explicit diagnostic only: no event, schema or response text persisted."""
        request=self.minimal_request();status=None
        try:
            with self.opener.open(request,timeout=self.timeout) as response:
                status=getattr(response,'status',None)
                raw=response.read(65537)
            if len(raw)>65536:raise ProviderError('invalid_response',http_status=status)
            content=self.response_content(raw)
            if not isinstance(content,str) or not content.strip() or self.key in content:raise ProviderError('invalid_response',http_status=status)
            return {'http_status':status if type(status) is int else None,'content_nonempty':True,'response_bytes':len(raw)}
        except HTTPError as error:raise provider_http_error(error,google=True) from None
        except ProviderError as error:
            if error.http_status is None and type(status) is int:error.http_status=status
            raise
        except (TimeoutError,socket.timeout):raise ProviderError('timeout') from None
        except (URLError,OSError):raise ProviderError('network') from None
        except (ValueError,KeyError,TypeError,IndexError,UnicodeError,AttributeError):raise ProviderError('invalid_response',http_status=status) from None

    def model_ids(self,raw):
        return [item['id'] for item in json.loads(raw)['data']]

    def list_models(self):
        """Optional metadata request; no event data, no automatic model fallback."""
        request=self.models_request()
        try:
            with self.opener.open(request,timeout=self.timeout) as response:
                raw=response.read(262145)
            if len(raw)>262144:raise ProviderError('invalid_response')
            data=self.model_ids(raw)
            if not isinstance(data,list):raise ProviderError('invalid_response')
            models=[]
            for identifier in data:
                if not isinstance(identifier,str) or self.key in identifier or not re.fullmatch(r'[A-Za-z0-9._:/-]{1,120}',identifier):raise ProviderError('invalid_response')
                models.append(identifier.removeprefix('models/'))
            return sorted(set(models))
        except HTTPError as error:
            raise provider_http_error(error,google=True) from None
        except (TimeoutError,socket.timeout):raise ProviderError('timeout') from None
        except (URLError,OSError):raise ProviderError('network') from None
        except (ValueError,KeyError,TypeError,UnicodeError,AttributeError):raise ProviderError('invalid_response') from None

    def payload(self,features):
        payload=super().payload(features)
        payload.pop('store')
        payload.pop('max_completion_tokens')
        payload['max_tokens']=self.max_tokens
        payload['response_format']={'type':'json_object'}
        payload['messages'][0]['content'] += (' All explanatory strings MUST be in Vietnamese. '
            'why states observed reasons; traversal_type states suspicious indicators only. '
            'Do not assert symlink escape, compromise or exploit success from these features. '
            'risk is an advisory assessment, not the ML probability.')
        payload['messages'][0]['content'] += (' The decision was already made by independent local path policy. '
            'An ML alert NEVER causes BLOCK or grants access. Explain the observed features without '
            'attributing the policy decision to ML. Do not recommend uncontrolled or recursive URL decoding.')
        return payload


class GeminiNativeProvider(GeminiProvider):
    """Explicit native GenerateContent adapter, authenticated only by header."""
    name='gemini-native'
    def __init__(self,key,model,timeout=20,opener=None,*,max_tokens=2048):
        if not re.fullmatch(r'[A-Za-z0-9._-]{1,120}',model):raise ValueError('Invalid AI model identifier')
        super().__init__(key,model,timeout,opener,max_tokens=max_tokens)
        self.endpoint='https://generativelanguage.googleapis.com/v1beta/models/'+model+':generateContent'
        self.identity=hashlib.sha256((self.identity+'|native-v1').encode()).hexdigest()

    def make_request(self,features):
        messages=self.payload(validate_features(features))['messages']
        body={'systemInstruction':{'parts':[{'text':messages[0]['content']}]},
              'contents':[{'role':'user','parts':[{'text':messages[1]['content']}]}],
              'generationConfig':{'maxOutputTokens':self.max_tokens,'responseMimeType':'application/json'}}
        return Request(self.endpoint,data=json.dumps(body).encode(),headers={'x-goog-api-key':self.key,'Content-Type':'application/json'},method='POST')

    def minimal_request(self):
        body={'contents':[{'parts':[{'text':'Reply with OK.'}]}],'generationConfig':{'maxOutputTokens':256}}
        return Request(self.endpoint,data=json.dumps(body).encode(),headers={'x-goog-api-key':self.key,'Content-Type':'application/json'},method='POST')

    def model_info(self):
        """One metadata request for this exact model, not the global catalog."""
        request=Request(self.endpoint.removesuffix(':generateContent'),headers={'x-goog-api-key':self.key},method='GET')
        status=None
        try:
            with self.opener.open(request,timeout=self.timeout) as response:
                raw=response.read(65537);status=getattr(response,'status',None)
            if len(raw)>65536:raise ProviderError('invalid_response')
            value=json.loads(raw)
            if value['name'] not in ('models/'+self.model,self.model):raise ProviderError('invalid_response')
            methods=value['supportedGenerationMethods']
            if not isinstance(methods,list) or len(methods)>100 or any(not isinstance(m,str) or not re.fullmatch('[A-Za-z][A-Za-z0-9]{0,63}',m) or self.key in m for m in methods):raise ProviderError('invalid_response')
            return {'name':self.model,'http_status':status if type(status) is int else None,
                    'supported_methods':methods,'generate_content_supported':'generateContent' in methods}
        except HTTPError as error:raise provider_http_error(error,google=True) from None
        except ProviderError as error:
            if error.http_status is None and type(status) is int:error.http_status=status
            raise
        except (TimeoutError,socket.timeout):raise ProviderError('timeout') from None
        except (URLError,OSError):raise ProviderError('network') from None
        except (ValueError,KeyError,TypeError,UnicodeError):raise ProviderError('invalid_response',http_status=status) from None

    def response_content(self,raw):
        candidate=json.loads(raw)['candidates'][0]
        if not isinstance(candidate,dict) or candidate.get('finishReason')!='STOP':raise ProviderError('invalid_response')
        parts=candidate['content']['parts']
        if not isinstance(parts,list) or any(not isinstance(p,dict) or (not p.get('thought',False) and not isinstance(p.get('text'),str)) for p in parts):raise ProviderError('invalid_response')
        return ''.join(part['text'] for part in parts if not part.get('thought',False))

    def models_request(self):
        return Request('https://generativelanguage.googleapis.com/v1beta/models',headers={'x-goog-api-key':self.key},method='GET')

    def model_ids(self,raw):
        return [item['name'] for item in json.loads(raw)['models'] if 'generateContent' in item.get('supportedGenerationMethods',[])]


def validate_output(value):
    if not isinstance(value,dict) or set(value)!={'why','traversal_type','risk','recommendations'}:raise ProviderError('invalid_response')
    if not isinstance(value['risk'],str) or value['risk'] not in {'low','medium','high','unknown'}:raise ProviderError('invalid_response')
    for key,limit in [('why',1200),('traversal_type',150),('recommendations',1600)]:
        if not isinstance(value[key],str) or not value[key].strip() or len(value[key])>limit:raise ProviderError('invalid_response')
    return value


DDL='''CREATE TABLE IF NOT EXISTS settings(id INTEGER PRIMARY KEY CHECK(id=1),enabled INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS calls(created REAL NOT NULL);
CREATE INDEX IF NOT EXISTS calls_time ON calls(created);
CREATE TABLE IF NOT EXISTS cache(fingerprint TEXT PRIMARY KEY,created REAL NOT NULL,status TEXT NOT NULL,output TEXT);
CREATE TABLE IF NOT EXISTS analyses(event_id INTEGER PRIMARY KEY,created REAL NOT NULL,fingerprint TEXT NOT NULL,status TEXT NOT NULL,output TEXT);
CREATE TABLE IF NOT EXISTS provenance(event_id INTEGER PRIMARY KEY,provider TEXT NOT NULL,model TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS analysis_timings(event_id INTEGER PRIMARY KEY,started REAL NOT NULL,completed REAL,duration_ms REAL);'''


class ExplanationService:
    def __init__(self,path,provider=None,limit=20,capacity=16):
        self.path=Path(path);self.provider=provider;self.limit=max(1,min(100,int(limit)))
        self.queue=queue.Queue(maxsize=max(1,min(100,int(capacity))))
        self.stop=threading.Event();self.dropped=0;self.thread=None
        if provider is not None:
            self.thread=threading.Thread(target=self._run,daemon=True,name='advisory-explanations')
            try:self.thread.start()
            except RuntimeError:self.thread=None;self.provider=None;self.dropped=1

    @contextmanager
    def _connect(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        db=sqlite3.connect(self.path,timeout=2)
        try:
            db.row_factory=sqlite3.Row;db.executescript(DDL)
            with db:yield db
        finally:db.close()

    def _enabled(self):
        if not self.path.is_file():return False
        with closing(sqlite3.connect(self.path,timeout=2)) as db:
            row=db.execute('SELECT enabled FROM settings WHERE id=1').fetchone()
            return bool(row and row[0])

    def set_enabled(self,value):
        with self._connect() as db:db.execute('INSERT INTO settings VALUES(1,?) ON CONFLICT(id) DO UPDATE SET enabled=excluded.enabled',(int(value),))

    def submit(self,event_id,raw,decision,suspicious):
        # No disk, waiting or network on the download thread. Queue contains
        # only coarse features and local numeric log ID (ID is never sent).
        if self.provider is None or type(event_id) is not int or event_id<=0 or not (decision=='BLOCK' or suspicious):return False
        try:self.queue.put_nowait((event_id,safe_features(raw,decision,suspicious)))
        except queue.Full:self.dropped+=1;return False
        return True

    def _process(self,event_id,features):
        if not self._enabled():return
        now=time.time();fingerprint=hashlib.sha256((self.provider.identity+json.dumps(features,sort_keys=True)).encode()).hexdigest()
        pending_window=max(30,3*getattr(self.provider,'timeout',3)+10)
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('INSERT OR IGNORE INTO provenance VALUES(?,?,?)',
                       (event_id,getattr(self.provider,'name','custom'),getattr(self.provider,'model','unknown')))
            cached=db.execute('SELECT * FROM cache WHERE fingerprint=?',(fingerprint,)).fetchone()
            if cached and ((cached['status']=='success' and cached['created']>now-86400) or (cached['status']=='pending' and cached['created']>now-pending_window)):
                db.execute('INSERT OR IGNORE INTO analyses VALUES(?,?,?,?,?)',(event_id,now,fingerprint,'cached' if cached['status']=='success' else 'waiting',cached['output']))
                return
            if cached and cached['status'] not in {'pending','success'} and cached['created']>now-60:
                db.execute('INSERT OR IGNORE INTO analyses VALUES(?,?,?,?,NULL)',(event_id,now,fingerprint,cached['status']));return
            if db.execute('SELECT COUNT(*) FROM calls WHERE created>?',(now-3600,)).fetchone()[0]>=self.limit:
                db.execute('INSERT OR IGNORE INTO analyses VALUES(?,?,?,?,NULL)',(event_id,now,fingerprint,'rate_limited'));return
            db.execute('INSERT INTO calls VALUES(?)',(now,))
            db.execute('INSERT INTO cache VALUES(?,?,?,NULL) ON CONFLICT(fingerprint) DO UPDATE SET created=excluded.created,status=excluded.status,output=NULL',(fingerprint,now,'pending'))
            db.execute('INSERT OR IGNORE INTO analyses VALUES(?,?,?,?,NULL)',(event_id,now,fingerprint,'pending'))
            db.execute('INSERT OR IGNORE INTO analysis_timings(event_id,started) VALUES(?,?)',(event_id,now))
        status,output='canceled',None
        started=time.time();clock=time.perf_counter();called=False
        if self._enabled():
            called=True
            try:
                output=json.dumps(validate_output(self.provider.analyze(features)),ensure_ascii=False);status='success'
            except ProviderError as error:status=str(error) if str(error) in {'quota','authentication','network','timeout','invalid_response','provider_error','invalid_request','model_unavailable','invalid_features'} else 'provider_error'
            except Exception:status='provider_error'  # Never persist exception text, headers or response bodies.
        elapsed=(time.perf_counter()-clock)*1000 if called else None
        with self._connect() as db:
            db.execute('UPDATE cache SET status=?,output=? WHERE fingerprint=?',(status,output,fingerprint))
            db.execute('UPDATE analyses SET status=?,output=? WHERE event_id=?',(status,output,event_id))
            db.execute('UPDATE analysis_timings SET started=?,completed=?,duration_ms=? WHERE event_id=?',(started,time.time(),elapsed,event_id))

    def _run(self):
        while not self.stop.is_set():
            try:item=self.queue.get(timeout=.2)
            except queue.Empty:continue
            try:self._process(*item)
            except Exception:self.dropped+=1  # Sidecar outage never affects authorization.
            finally:self.queue.task_done()

    def snapshot(self,event_id=None):
        enabled=False;rows=[];unavailable=False
        try:
            enabled=self._enabled()
            if self.path.is_file():
                with closing(sqlite3.connect(self.path,timeout=2)) as db:
                    db.row_factory=sqlite3.Row
                    # Old sidecars remain readable before the next worker initializes provenance.
                    has_provenance=db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='provenance'").fetchone()
                    source="p.provider,p.model" if has_provenance else "NULL AS provider,NULL AS model"
                    join=" LEFT JOIN provenance p USING(event_id)" if has_provenance else ""
                    has_timings=db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='analysis_timings'").fetchone()
                    source+=",t.started,t.completed,t.duration_ms" if has_timings else ",NULL AS started,NULL AS completed,NULL AS duration_ms"
                    join+=" LEFT JOIN analysis_timings t USING(event_id)" if has_timings else ""
                    query="SELECT a.event_id,a.created,"+source+",CASE WHEN a.status='waiting' THEN COALESCE(c.status,'pending') ELSE a.status END AS status,CASE WHEN a.status='waiting' THEN c.output ELSE a.output END AS output FROM analyses a LEFT JOIN cache c USING(fingerprint)"+join
                    params=()
                    if event_id is not None:query+=' WHERE a.event_id=?';params=(event_id,)
                    for row in db.execute(query+' ORDER BY a.created DESC LIMIT 20',params):
                        item=dict(row);output=item.pop('output');item['analysis']=json.loads(output) if output else None
                        stale=max(30,3*getattr(self.provider,'timeout',3)+10)
                        if item['status']=='pending' and item['created']<time.time()-stale:item['status']='interrupted'
                        rows.append(item)
        except (sqlite3.Error,OSError,ValueError,TypeError):unavailable=True
        return {'enabled':enabled,'configured':self.provider is not None,'provider':getattr(self.provider,'name','custom') if self.provider is not None else 'offline',
                'model':getattr(self.provider,'model',None),'unavailable':unavailable,'rows':rows,'dropped':self.dropped,'limit':self.limit}

    def close(self):
        self.stop.set()
        if self.thread:self.thread.join(timeout=1)
