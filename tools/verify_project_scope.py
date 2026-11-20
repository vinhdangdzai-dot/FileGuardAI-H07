"""Real localhost TCP/Chrome H07 scenarios; isolated DB, real deployed LR, no API."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import http.client
import json
from pathlib import Path
import re
import secrets
import sqlite3
import sys
import threading
from urllib.parse import urlencode

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'.verification/gemini_browser_lib')]
from app import create_app
from tools.mfa_fixture import Authenticator
from tools.pytest_runtime import create_runtime
from werkzeug.serving import make_server


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--browser',action='store_true');args=parser.parse_args()
    runtime=create_runtime(ROOT);out=ROOT/'docs/h07/evidence'/('scope_tcp_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+secrets.token_hex(3));out.mkdir()
    protected=[ROOT/'data/paths_synthetic.csv',ROOT/'artifacts/model.joblib',ROOT/'instance/events.sqlite3',ROOT/'instance/admin_password.hash',ROOT/'docs/evaluations/latest.json']
    before={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in protected if p.is_file()}
    files=runtime['root']/'shared';files.mkdir()
    for name,content in [('public.txt',b'PUBLIC'),('báo cáo.txt',b'UNICODE'),('docs/chapter.txt',b'NESTED'),('etc/passwd',b'DUMMY-IN-ROOT'),('restricted/internal-secret.txt',b'PRIVATE-SENTINEL')]:
        p=files/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(content)
    (runtime['root']/'outside.txt').write_bytes(b'OUTSIDE-SENTINEL')
    password=secrets.token_urlsafe(24);user_password=secrets.token_urlsafe(24)
    app=create_app({'TESTING':True,'CSRF_ENABLED':True,'SECRET_KEY':secrets.token_hex(32),
                    'FILES_ROOT':files,'DATABASE':runtime['root']/'events.sqlite3','ADMIN_PASSWORD':password})
    server=make_server('127.0.0.1',0,app,threaded=True);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base='http://127.0.0.1:'+str(server.server_port);cookie=''
    result={'transport':'localhost TCP','lr_model':'artifacts/model.joblib (read only)','gemini':'offline; no external API calls',
            'checks':[],'downloads':[],'screenshots':[],'browser_errors':[],'static_errors':[]}
    def check(name,passed,actual=None):result['checks'].append({'name':name,'result':'PASS' if passed else 'FAIL','actual':actual})
    def fetch(path,form=None):
        nonlocal cookie
        connection=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=15)
        headers={'Cookie':cookie}
        if form is not None:headers['Content-Type']='application/x-www-form-urlencoded'
        try:
            connection.request('POST' if form is not None else 'GET',path,urlencode(form) if form is not None else None,headers)
            response=connection.getresponse();body=response.read()
            if response.getheader('Set-Cookie'):cookie=response.getheader('Set-Cookie').split(';',1)[0]
            return response.status,body
        finally:connection.close()
    def csrf(path='/login'):
        _,body=fetch(path);return re.search(rb'name="csrf_token" value="([^"]+)"',body)[1].decode()
    def rows(sql):
        with sqlite3.connect(app.config['DATABASE']) as db:
            db.row_factory=sqlite3.Row;return [dict(r) for r in db.execute(sql)]
    def download(name,uri,expected,content=None):
        status,body=fetch(uri);event=rows('SELECT id,ml_score,ml_label,action,http_status FROM access_logs ORDER BY id DESC LIMIT 1')[0]
        passed=status==expected and event['http_status']==status and b'OUTSIDE-SENTINEL' not in body
        if content is not None:passed=passed and body==content
        if expected!=200:passed=passed and b'PRIVATE-SENTINEL' not in body
        row={'TC':f'DL{len(result["downloads"])+1:02}','name':name,'input':uri,'expected_http':expected,'actual_http':status,
             'result':'PASS' if passed else 'FAIL','event':event}
        result['downloads'].append(row);check(name,passed,status)
    try:
        status,home=fetch('/');check('Guest public home hides restricted names',status==200 and b'public.txt' in home and b'internal-secret.txt' not in home)
        for name,uri,expected,content in [
            ('public','/download?path=public.txt',200,b'PUBLIC'),('Unicode','/download?'+urlencode({'path':'báo cáo.txt'}),200,b'UNICODE'),
            ('subfolder','/download?path=docs/chapter.txt',200,b'NESTED'),('restricted guest','/download?path=restricted/internal-secret.txt',403,None),
            ('restricted nonexistent guest','/download?path=restricted/absent.txt',403,None),('direct traversal','/download?path=../outside.txt',403,None),
            ('Windows separator','/download?'+urlencode({'path':'..\\outside.txt'}),403,None),('Windows absolute','/download?path=C:/Windows/win.ini',403,None),
            ('URL encoded','/download?path=%2e%2e%2foutside.txt',403,None),('double encoded','/download?path=%252e%252e%252foutside.txt',403,None),
            ('missing public','/download?path=absent.txt',404,None),('legitimate lexical passwd','/download?path=etc/passwd',200,b'DUMMY-IN-ROOT')]:
            download(name,uri,expected,content)
        check('Guest admin denied',fetch('/admin')[0]==302 and fetch('/admin/documents')[0]==302)
        status,_=fetch('/login',{'csrf_token':csrf(),'password':password});check('Admin password step',status==302)
        check('Partial Admin cannot enter admin',fetch('/admin')[0]==302)
        download('Partial Admin restricted denied','/download?path=restricted/internal-secret.txt',403)
        status,form=fetch('/login/mfa');authenticator=Authenticator();form=form.decode('utf-8')
        status,codes=fetch('/login/mfa',{'csrf_token':re.search(r'name="csrf_token" value="([^"]+)"',form)[1],'code':authenticator.factor(form)})
        authenticator.remember(codes.decode('utf-8'));check('Admin TOTP verified',status==200)
        admin_cookie=cookie
        check('Admin area and classification',fetch('/admin')[0]==200 and fetch('/admin/documents')[0]==200)
        check('Admin event detail includes local offline recommendations',b'../outside.txt' in fetch('/dashboard/events/6')[1])
        download('Admin traversal still blocked','/download?path=../outside.txt',403)
        cookie=''
        status,_=fetch('/register',{'csrf_token':csrf(),'username':'scope-reader','email':'scope-reader@example.test','password':user_password,'confirm_password':user_password})
        check('Registration always User',status==302 and rows('SELECT role FROM auth_users')==[{'role':'user'}])
        status,_=fetch('/login',{'csrf_token':csrf(),'identifier':'scope-reader@example.test','password':user_password,'role':'admin'})
        check('User login cannot choose admin',status==302 and fetch('/admin')[0]==403)
        user_cookie=cookie
        download('User restricted allowed','/download?path=restricted/internal-secret.txt',200,b'PRIVATE-SENTINEL')
        check('User private analysis denied',all(fetch(p)[0]==403 for p in ['/admin/documents','/dashboard/events/1','/dashboard/ai-evaluation']))
        for _ in range(2):download('Repeated traversal keeps Event ID','/download?path=../outside.txt',403)
        all_ids=[r['id'] for r in rows('SELECT id FROM access_logs ORDER BY id')]
        check('Every download has a unique preserved Event ID',all_ids==[r['event']['id'] for r in result['downloads']])
        check('Context linked to every Event ID',len(rows('SELECT * FROM download_context'))==len(all_ids))
        check('Repeated alert grouping retains links',bool(rows('SELECT id FROM alerts WHERE occurrences>=3')) and len(rows('SELECT DISTINCT event_id FROM alert_events'))==len(rows('SELECT event_id FROM alert_events')))
        result['observed_lr_disagreements']=[{'TC':d['TC'],'http':d['actual_http'],'score':d['event']['ml_score'],'label':d['event']['ml_label']} for d in result['downloads']
            if d['name']=='legitimate lexical passwd' and d['event']['ml_label']=='suspicious' or d['name'] in {'direct traversal','Windows separator','Windows absolute','URL encoded','double encoded'} and d['event']['ml_label']=='benign']
        if args.browser:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as playwright:
                browser=playwright.chromium.launch(executable_path=str(ROOT/'.verification/chrome_for_testing/157.0.8103.78/chrome-win64/chrome.exe'),headless=True,args=['--disable-gpu'])
                for owner,route,auth_cookie in [('guest','/',''),('user','/',user_cookie),('admin','/admin',admin_cookie),('documents','/admin/documents',admin_cookie),('event','/dashboard/events/6',admin_cookie)]:
                    context=browser.new_context()
                    if auth_cookie:context.add_cookies([{'name':'session','value':auth_cookie.split('=',1)[1],'url':base,'httpOnly':True,'sameSite':'Lax'}])
                    page=context.new_page();page.on('pageerror',lambda error:result['browser_errors'].append('runtime_error'))
                    page.on('response',lambda response:result['static_errors'].append(response.status) if '/static/' in response.url and response.status>=400 else None)
                    response=page.goto(base+route);page.wait_for_load_state('networkidle');check(owner+' page HTTP 200',response.status==200)
                    for theme in ['light','dark']:
                        for width in [1440,768,390]:
                            page.set_viewport_size({'width':width,'height':1000});page.locator('#theme-toggle').click();page.locator('[data-theme-choice='+theme+']').click()
                            check(owner+' '+theme+' '+str(width)+' responsive',page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'))
                            name=f'{owner}_{theme}_{width}.png';page.screenshot(path=str(out/name),full_page=True);result['screenshots'].append(name)
                    context.close()
                browser.close()
            check('No browser JS or static errors',not result['browser_errors'] and not result['static_errors'])
    except Exception:
        check('Scope verification completed',False,'Diagnostic text omitted to protect fixture credentials and TOTP')
    finally:
        server.shutdown();server.server_close();thread.join(timeout=5)
        app.extensions['recovery_mail'].close();app.extensions['ai_explanations'].close()
        result['protected_unchanged']={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==value for p,value in before.items()}
        result['passed']=sum(r['result']=='PASS' for r in result['checks']);result['failed']=sum(r['result']=='FAIL' for r in result['checks'])
        (out/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        with (out/'download_cases.csv').open('w',encoding='utf-8-sig',newline='') as handle:
            writer=csv.DictWriter(handle,fieldnames=['TC','name','input','expected_http','actual_http','result']);writer.writeheader();writer.writerows({k:d[k] for k in writer.fieldnames} for d in result['downloads'])
    print('Scope TCP/Chrome:',result['passed'],'PASS,',result['failed'],'FAIL');print('Evidence:',out.relative_to(ROOT))
    return int(result['failed']>0 or not all(result['protected_unchanged'].values()))


if __name__=='__main__':raise SystemExit(main())
