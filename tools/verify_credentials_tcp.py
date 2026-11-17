"""Production-mode TCP credential restart checks on owned fixture files only."""
from datetime import datetime,timezone
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import subprocess
import sys
from urllib.parse import urlencode

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def serve(scope):
    from app import create_app
    from werkzeug.serving import make_server,WSGIRequestHandler
    class Quiet(WSGIRequestHandler):
        def log_request(self,*args,**kwargs):pass
    app=create_app({'FILES_ROOT':scope/'shared','DATABASE':scope/'audit.sqlite3',
        'ADMIN_HASH_FILE':scope/'admin_password.hash','AUDITOR_HASH_FILE':scope/'auditor_password.hash',
        'ADMIN_PASSWORD':None,'SECRET_KEY':os.environ['H07_FIXTURE_SESSION_KEY']})
    server=make_server('127.0.0.1',0,app)
    print(server.server_port,flush=True)
    server.serve_forever()


def main():
    from tools.pytest_runtime import create_runtime
    from tools.manage_credentials import store_password
    from werkzeug.security import check_password_hash
    scope=create_runtime(ROOT,'pytest')['root']
    (scope/'shared').mkdir();(scope/'shared/ok.txt').write_text('PUBLIC')
    old,new=secrets.token_urlsafe(24),secrets.token_urlsafe(24)
    store_password(old,scope/'admin_password.hash')
    env=dict(os.environ,H07_FIXTURE_SESSION_KEY=secrets.token_hex(32))
    protected=[ROOT/'data/paths_synthetic.csv',ROOT/'artifacts/model.joblib',ROOT/'instance/events.sqlite3',ROOT/'instance/admin_password.hash']
    before={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected if p.is_file()}
    checks=[]
    def check(name,ok):checks.append({'name':name,'result':'PASS' if ok else 'FAIL'})
    def start():
        process=subprocess.Popen([sys.executable,__file__,'--serve',str(scope)],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        line=process.stdout.readline().strip()
        if not line.isdigit():
            process.terminate();process.wait(timeout=10)
            raise RuntimeError('Fixture server failed to start')
        return process,int(line)
    cookie=''
    def request(port,path,form=None):
        nonlocal cookie
        connection=http.client.HTTPConnection('127.0.0.1',port,timeout=20)
        headers={'Cookie':cookie}
        if form is not None:headers['Content-Type']='application/x-www-form-urlencoded'
        connection.request('POST' if form is not None else 'GET',path,urlencode(form) if form is not None else None,headers)
        response=connection.getresponse();data=response.read();status=response.status
        if response.getheader('Set-Cookie'):cookie=response.getheader('Set-Cookie').split(';',1)[0]
        connection.close()
        check('No password reflected in '+path,old.encode() not in data and new.encode() not in data)
        return status,data
    def token(port,path):
        status,data=request(port,path)
        return re.search(rb'name="csrf_token" value="([^"]+)"',data)[1].decode()
    for cycle in [1,2]:
        process,port=start()
        try:
            if cycle==1:
                status,_=request(port,'/login',{'csrf_token':token(port,'/login'),'password':old})
                check('First process accepts original password',status==302)
                status,_=request(port,'/account/password',{'csrf_token':token(port,'/account/password'),'current_password':old,'new_password':new,'confirm_password':new})
                check('First process commits new password',status==302)
                check('Hash contains new password only through verification',check_password_hash((scope/'admin_password.hash').read_text().strip(),new))
            else:
                status,_=request(port,'/login',{'csrf_token':token(port,'/login'),'password':old})
                check('Restart rejects old password',status==200)
                status,_=request(port,'/login',{'csrf_token':token(port,'/login'),'password':new})
                check('Restart accepts persisted new password',status==302)
                check('Restart grants dashboard after valid login',request(port,'/dashboard')[0]==200)
                check('Download still valid',request(port,'/download?path=ok.txt')[0]==200)
                check('Encoded traversal still rejected',request(port,'/download?path=%252e%252e%252fsecret.txt')[0]==403)
        finally:
            process.terminate();process.wait(timeout=10)
            process.stdout.close();process.stderr.close()
    with sqlite3.connect(scope/'audit.sqlite3') as db:
        events=repr(db.execute('SELECT * FROM security_events').fetchall())
    check('Audit contains change success without passwords','password_change_success' in events and old not in events and new not in events)
    unchanged={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest for name,digest in before.items()}
    out=ROOT/'docs/auth/evidence'/('restart_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+secrets.token_hex(3));out.mkdir(parents=True)
    result={'mode':'Two separate OS processes, real TCP localhost, TESTING=False, isolated credentials and SQLite',
       'checks':checks,'protected_unchanged':unchanged,'passed':sum(c['result']=='PASS' for c in checks),'failed':sum(c['result']=='FAIL' for c in checks)}
    (out/'results.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2));print('Evidence:',out.relative_to(ROOT))
    return int(result['failed']>0 or not all(unchanged.values()))


if __name__=='__main__':
    if len(sys.argv)==3 and sys.argv[1]=='--serve':
        candidate=Path(sys.argv[2]).resolve()
        if candidate.parent!=ROOT.resolve() or not candidate.name.startswith('.test_runtime_pytest_'):raise ValueError('Owned fixture root required')
        serve(candidate)
    else:raise SystemExit(main())
