"""Real Chrome/TCP account flows on isolated credentials, DB and fake mailbox."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import secrets
import sys
import threading
import time
from urllib.parse import urlsplit,parse_qs

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'.verification/gemini_browser_lib'),str(ROOT)]
from playwright.sync_api import sync_playwright,expect
from werkzeug.serving import make_server
from app import create_app
from tools.pytest_runtime import create_runtime
from tools.mfa_fixture import complete_browser


def main():
    runtime=create_runtime(ROOT)
    out=ROOT/'docs/ui'/('accounts_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+secrets.token_hex(3));out.mkdir()
    protected=[ROOT/'data/paths_synthetic.csv',ROOT/'artifacts/model.joblib',ROOT/'instance/events.sqlite3',ROOT/'instance/admin_password.hash']
    before={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected if p.is_file()}
    public=runtime['root']/'public';public.mkdir();(public/'ok.txt').write_bytes(b'PUBLIC')
    admin_password=secrets.token_urlsafe(24);password=secrets.token_urlsafe(18);changed=secrets.token_urlsafe(18);reset=secrets.token_urlsafe(18)
    mailbox=[]
    app=create_app({'TESTING':True,'CSRF_ENABLED':True,'FILES_ROOT':public,'DATABASE':runtime['root']/'events.sqlite3',
                    'MODEL_PATH':runtime['root']/'missing.joblib','ADMIN_PASSWORD':admin_password,
                    'ACCOUNT_RESET_ORIGIN':'https://example.test','ACCOUNT_MAIL_SENDER':lambda address,url:mailbox.append((address,url))})
    server=make_server('127.0.0.1',0,app,threaded=True);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base='http://127.0.0.1:'+str(server.server_port)
    result={'note':'Real TCP/Chrome; synthetic accounts and mailbox; no SMTP/Gemini calls or business DB writes.',
            'checks':[],'browser_errors':[],'static_errors':[],'screenshots':[]}
    def check(name,value,actual=None):result['checks'].append({'name':name,'result':'PASS' if value else 'FAIL','actual':actual})
    def login(page,identifier,pw):
        page.goto(base+'/login');page.locator('#identifier').fill(identifier);page.locator('#pw').fill(pw)
        page.locator('button[type=submit]').click();page.wait_for_load_state('networkidle')
        complete_browser(page)
    def fill_change(page,current,new):
        for field,value in [('current_password',current),('new_password',new),('confirm_password',new)]:page.locator('#'+field).fill(value)
        page.locator('form[action="/account/password"] button[type=submit]').click();page.wait_for_load_state('networkidle')
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path=str(ROOT/'.verification/chrome_for_testing/157.0.8103.78/chrome-win64/chrome.exe'),headless=True,args=['--disable-gpu'])
            context=browser.new_context(viewport={'width':1440,'height':1000})
            page=context.new_page();page.on('pageerror',lambda error:result['browser_errors'].append('runtime_error'))
            page.on('response',lambda response:result['static_errors'].append(response.status) if '/static/' in response.url and response.status>=400 else None)
            page.goto(base+'/register')
            for name,value in [('username','alice-demo'),('email','alice-demo@example.test'),('display_name','Hữu Vinh'),('password',password),('confirm_password',password)]:page.locator('#'+name).fill(value)
            reveal=page.locator('[data-reveal=password]');reveal.click();check('registration password reveal works',page.locator('#password').get_attribute('type')=='text');reveal.click()
            page.locator('.account-panel button[type=submit]').click();page.wait_for_url('**/login')
            login(page,'alice-demo@example.test',password)
            check('User registered and logged in using email',urlsplit(page.url).path=='/account')
            check('User cannot access Admin endpoints',all(context.request.get(base+path,max_redirects=0).status==403 for path in ['/dashboard','/admin/accounts','/account/mfa','/dashboard/alerts','/dashboard/ai-training']))
            check('User account route enforces CSRF',context.request.post(base+'/account',form={'display_name':'tamper'}).status==403)
            other=browser.new_context(storage_state=context.storage_state())
            page.locator('#display_name').fill('Hữu Vinh — hồ sơ');page.locator('.account-panel form button').click();page.wait_for_load_state('networkidle')
            check('Unicode profile update works',page.locator('#display_name').input_value()=='Hữu Vinh — hồ sơ')
            page.goto(base+'/account/password');fill_change(page,'wrong-fixture',changed)
            check('wrong current password rejected',page.locator('.alert-danger').count()>0)
            fill_change(page,password,changed);page.wait_for_url('**/login')
            check('password change revokes other session',other.request.get(base+'/account',max_redirects=0).status==302);other.close()
            login(page,'alice-demo',changed);check('new password logs in',urlsplit(page.url).path=='/account')
            page.locator('form[action="/logout"] button').click();page.wait_for_load_state('networkidle')
            page.goto(base+'/forgot-password');page.locator('#identifier').fill('alice-demo');page.locator('.account-panel button').click();page.wait_for_load_state('networkidle')
            deadline=time.monotonic()+5
            while not mailbox and time.monotonic()<deadline:time.sleep(.05)
            if not mailbox:raise RuntimeError('fixture mailbox unavailable')
            value=parse_qs(urlsplit(mailbox[-1][1]).fragment)['token'][0]
            page.goto(base+'/reset-password#token='+value);page.wait_for_load_state('networkidle')
            check('reset token stays out of URL and server query',urlsplit(page.url).fragment=='' and page.locator('#reset-token').input_value()==value)
            for name in ['new_password','confirm_password']:page.locator('#'+name).fill(reset)
            page.locator('.account-panel button[type=submit]').click();page.wait_for_url('**/login')
            login(page,'alice-demo',reset);check('reset password logs in',urlsplit(page.url).path=='/account')
            admin=browser.new_context();admin_page=admin.new_page()
            admin_page.goto(base+'/login');admin_page.locator('#pw').fill(admin_password)
            admin_page.locator('.login-panel button[type=submit]').click();admin_page.wait_for_load_state('networkidle')
            check('Admin password alone has no dashboard privilege',admin.request.get(base+'/dashboard',max_redirects=0).status==302)
            check('MFA setup requires CSRF',admin.request.post(base+'/login/mfa',form={'code':'invalid'}).status==403)
            check('MFA QR loads locally',admin.request.get(base+'/login/mfa/qr').status==200)
            for mode in ['light','dark']:
                for width in [1440,768,390]:
                    admin_page.set_viewport_size({'width':width,'height':1000})
                    admin_page.locator('#theme-toggle').click();admin_page.locator('[data-theme-choice='+mode+']').click()
                    check('MFA setup '+mode+' '+str(width)+' fits viewport',admin_page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'))
                    filename='mfa_setup_'+mode+'_'+str(width)+'.png'
                    admin_page.screenshot(path=str(out/filename),full_page=True,mask=[admin_page.locator('#mfa-secret'),admin_page.locator('.mfa-qr')])
                    result['screenshots'].append(filename)
            complete_browser(admin_page)
            check('Admin gains dashboard only after real TOTP',admin.request.get(base+'/dashboard',max_redirects=0).status==200)
            admin_page.goto(base+'/admin/accounts')
            form=admin_page.locator('.account-admin-form').first
            form.locator('[name=current_password]').fill(admin_password);form.locator('button').click();admin_page.wait_for_load_state('networkidle')
            check('Admin lock revokes User immediately',context.request.get(base+'/account',max_redirects=0).status==302)
            form=admin_page.locator('.account-admin-form').first;form.locator('[name=current_password]').fill(admin_password);form.locator('button').click();admin_page.wait_for_load_state('networkidle')
            login(page,'alice-demo',reset);check('Admin unlock restores login',urlsplit(page.url).path=='/account')
            check('downloads and boundary unchanged',context.request.get(base+'/download?path=ok.txt').status==200 and context.request.get(base+'/download?path=../outside').status==403)
            for route,owner in [('/register',context),('/login',context),('/forgot-password',context),('/reset-password',context),('/account',context),('/account/password',context),('/admin/accounts',admin),('/account/mfa',admin)]:
                view=owner.new_page();view.on('pageerror',lambda error:result['browser_errors'].append('runtime_error'))
                view.goto(base+route);view.wait_for_load_state('networkidle')
                for mode in ['light','dark']:
                    for width in [1440,768,390]:
                        view.set_viewport_size({'width':width,'height':1000});view.locator('#theme-toggle').click();view.locator('[data-theme-choice='+mode+']').click()
                        bounds=view.evaluate('({width:innerWidth,scroll:document.documentElement.scrollWidth})')
                        check(route+' '+mode+' '+str(width)+' fits viewport',bounds['scroll']<=width+1,bounds)
                        filename=route.strip('/').replace('/','_')+'_'+mode+'_'+str(width)+'.png';view.screenshot(path=str(out/filename),full_page=True);result['screenshots'].append(filename)
                view.close()
            stolen=browser.new_context(storage_state=admin.storage_state())
            admin_page.goto(base+'/account/mfa');admin_page.locator('form[action="/logout"] button').click();admin_page.wait_for_load_state('networkidle')
            check('Server rejects copied Admin cookie after logout',stolen.request.get(base+'/dashboard',max_redirects=0).status==302)
            stolen.close()
            check('no JavaScript errors',not result['browser_errors']);check('static assets load',not result['static_errors'])
            context.close();admin.close();browser.close()
    except Exception:
        check('browser suite completed',False,'See preceding checks; exception text omitted to protect fixture password/reset token.')
    finally:
        app.extensions['recovery_mail'].close();server.shutdown();server.server_close();thread.join(timeout=5)
        result['protected_unchanged']={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest for name,digest in before.items()}
        result['passed']=sum(c['result']=='PASS' for c in result['checks']);result['failed']=sum(c['result']=='FAIL' for c in result['checks'])
        (out/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Accounts Chrome:',result['passed'],'PASS,',result['failed'],'FAIL');print('Evidence:',out.relative_to(ROOT))
    return int(result['failed']>0 or not all(result['protected_unchanged'].values()))


if __name__=='__main__':raise SystemExit(main())
