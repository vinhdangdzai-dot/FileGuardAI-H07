"""Optional advisory explanations. Raw paths never enter queues or providers."""
from contextlib import closing, contextmanager
import hashlib
import json
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
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None


class ChatCompletionProvider:
    """HTTPS OpenAI-compatible adapter; endpoint/model configured by operator."""
    def __init__(self,key,endpoint,model,timeout=3,opener=None):
        parsed=urlsplit(endpoint)
        if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError('AI endpoint must be a credential-free HTTPS URL')
        if not re.fullmatch(r'[A-Za-z0-9._:/-]{1,120}',model):raise ValueError('Invalid AI model identifier')
        if not isinstance(key,str) or not re.fullmatch(r'[!-~]{1,4096}',key):raise ValueError('Invalid AI key format')
        self.key,self.endpoint,self.model,self.timeout=key,endpoint,model,min(10,max(.1,float(timeout)))
        self.opener=opener or build_opener(NoRedirect())
        self.identity=hashlib.sha256((endpoint+'|'+model).encode()).hexdigest()

    def analyze(self,features):
        prompt=('Explain security indicators in Vietnamese from coarse boolean/count features only. '
                'No original path or exploit success is known. AI is advisory and cannot authorize downloads. '
                'Return ONLY a JSON object with why (string), traversal_type (string), risk '
                '(low, medium, high or unknown), recommendations (string). Do not invent filenames or people.')
        body=json.dumps({'model':self.model,'messages':[{'role':'system','content':prompt},
                        {'role':'user','content':json.dumps(features,sort_keys=True)}],
                        'max_completion_tokens':600,'store':False}).encode()
        request=Request(self.endpoint,data=body,headers={'Authorization':'Bearer '+self.key,'Content-Type':'application/json'},method='POST')
        try:
            with self.opener.open(request,timeout=self.timeout) as response:
                raw=response.read(65537)
                if len(raw)>65536:raise ProviderError('invalid_response')
            content=json.loads(raw)['choices'][0]['message']['content']
            if not isinstance(content,str) or self.key in content:raise ProviderError('invalid_response')
            result=validate_output(json.loads(content))
            if any(self.key in value for value in result.values()):raise ProviderError('invalid_response')
            return result
        except HTTPError as error:
            code=error.code
            error.close()
            raise ProviderError('quota' if code==429 else 'authentication' if code in [401,403] else 'provider_error') from None
        except (TimeoutError,socket.timeout):raise ProviderError('timeout') from None
        except (URLError,OSError):raise ProviderError('network') from None
        except (ValueError,KeyError,TypeError,IndexError,UnicodeError):raise ProviderError('invalid_response') from None


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
CREATE TABLE IF NOT EXISTS analyses(event_id INTEGER PRIMARY KEY,created REAL NOT NULL,fingerprint TEXT NOT NULL,status TEXT NOT NULL,output TEXT);'''


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
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            cached=db.execute('SELECT * FROM cache WHERE fingerprint=?',(fingerprint,)).fetchone()
            if cached and ((cached['status']=='success' and cached['created']>now-86400) or (cached['status']=='pending' and cached['created']>now-30)):
                db.execute('INSERT OR IGNORE INTO analyses VALUES(?,?,?,?,?)',(event_id,now,fingerprint,'cached' if cached['status']=='success' else 'waiting',cached['output']))
                return
            if cached and cached['status'] not in {'pending','success'} and cached['created']>now-60:
                db.execute('INSERT OR IGNORE INTO analyses VALUES(?,?,?,?,NULL)',(event_id,now,fingerprint,cached['status']));return
            if db.execute('SELECT COUNT(*) FROM calls WHERE created>?',(now-3600,)).fetchone()[0]>=self.limit:
                db.execute('INSERT OR IGNORE INTO analyses VALUES(?,?,?,?,NULL)',(event_id,now,fingerprint,'rate_limited'));return
            db.execute('INSERT INTO calls VALUES(?)',(now,))
            db.execute('INSERT INTO cache VALUES(?,?,?,NULL) ON CONFLICT(fingerprint) DO UPDATE SET created=excluded.created,status=excluded.status,output=NULL',(fingerprint,now,'pending'))
            db.execute('INSERT OR IGNORE INTO analyses VALUES(?,?,?,?,NULL)',(event_id,now,fingerprint,'pending'))
        status,output='canceled',None
        if self._enabled():
            try:
                output=json.dumps(validate_output(self.provider.analyze(features)),ensure_ascii=False);status='success'
            except ProviderError as error:status=str(error) if str(error) in {'quota','authentication','network','timeout','invalid_response','provider_error'} else 'provider_error'
            except Exception:status='provider_error'  # Never persist exception text, headers or response bodies.
        with self._connect() as db:
            db.execute('UPDATE cache SET status=?,output=? WHERE fingerprint=?',(status,output,fingerprint))
            db.execute('UPDATE analyses SET status=?,output=? WHERE event_id=?',(status,output,event_id))

    def _run(self):
        while not self.stop.is_set():
            try:item=self.queue.get(timeout=.2)
            except queue.Empty:continue
            try:self._process(*item)
            except Exception:self.dropped+=1  # Sidecar outage never affects authorization.
            finally:self.queue.task_done()

    def snapshot(self):
        enabled=False;rows=[];unavailable=False
        try:
            enabled=self._enabled()
            if self.path.is_file():
                with closing(sqlite3.connect(self.path,timeout=2)) as db:
                    db.row_factory=sqlite3.Row
                    for row in db.execute("SELECT a.event_id,a.created,CASE WHEN a.status='waiting' THEN COALESCE(c.status,'pending') ELSE a.status END AS status,CASE WHEN a.status='waiting' THEN c.output ELSE a.output END AS output FROM analyses a LEFT JOIN cache c USING(fingerprint) ORDER BY a.created DESC LIMIT 20"):
                        item=dict(row);output=item.pop('output');item['analysis']=json.loads(output) if output else None
                        if item['status']=='pending' and item['created']<time.time()-30:item['status']='interrupted'
                        rows.append(item)
        except (sqlite3.Error,OSError,ValueError,TypeError):unavailable=True
        return {'enabled':enabled,'configured':self.provider is not None,'unavailable':unavailable,'rows':rows,'dropped':self.dropped,'limit':self.limit}

    def close(self):
        self.stop.set()
        if self.thread:self.thread.join(timeout=1)
