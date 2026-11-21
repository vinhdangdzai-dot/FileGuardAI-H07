"""Focused real Chrome/TCP alerts checks; isolated data, no external provider."""
import json
from pathlib import Path
import secrets
import sys
import threading
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'.verification/gemini_browser_lib'),str(ROOT)]
from playwright.sync_api import sync_playwright,expect
from werkzeug.serving import make_server
from app import create_app
from tools.pytest_runtime import create_runtime


def main():
    runtime=create_runtime(ROOT)
    out=ROOT/'docs/ui'/('alerts_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+secrets.token_hex(3));out.mkdir()
    files=runtime['root']/'public';files.mkdir();(files/'ok.txt').write_bytes(b'PUBLIC')
    password=secrets.token_hex(16)
    app=create_app({'TESTING':True,'CSRF_ENABLED':True,'DATABASE':runtime['root']/'events.sqlite3','FILES_ROOT':files,'ADMIN_PASSWORD':password,'MODEL_PATH':runtime['root']/'missing.joblib'})
    server=make_server('127.0.0.1',0,app,threaded=True);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base='http://127.0.0.1:'+str(server.server_port)
    results={'checks':[],'browser_errors':[],'note':'Isolated offline fixtures; real browser/TCP, no Gemini network call.'}
    def check(name,value,actual=None):results['checks'].append({'name':name,'result':'PASS' if value else 'FAIL','actual':actual})
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path=str(ROOT/'.verification/chrome_for_testing/157.0.8103.78/chrome-win64/chrome.exe'),headless=True,args=['--disable-gpu'])
            context=browser.new_context(viewport={'width':1440,'height':1000})
            page=context.new_page();page.on('pageerror',lambda error:results['browser_errors'].append(str(error)))
            page.goto(base+'/login');page.locator('#pw').fill(password);page.locator('button[type=submit]').click()
            from tools.mfa_fixture import complete_browser
            complete_browser(page)
            page.wait_for_url(base+'/dashboard')
            expect(page.locator('#alert-live-status')).to_contain_text('nhóm',timeout=10000)
            response=context.request.get(base+'/download?path=../outside')
            expect(page.locator('#alert-live-items')).to_contain_text('Cảnh báo #',timeout=15000)
            check('polling shows immediate offline alert',response.status==403)
            context.request.get(base+'/download?path=../outside')
            page.goto(base+'/dashboard/alerts');check('grouped two events',context.request.get(base+'/dashboard/alerts/feed?after=0').json()['items'][0]['occurrences']==2)
            for mode in ['light','dark']:
                for width in [1440,768,390]:
                    page.set_viewport_size({'width':width,'height':1000})
                    page.locator('#theme-toggle').click();page.locator('[data-theme-choice='+mode+']').click()
                    overflow=page.evaluate('''() => ({width:innerWidth,scroll:document.documentElement.scrollWidth,scrollers:[...document.querySelectorAll('body *')].filter(n=>n.scrollWidth>n.clientWidth+1).map(n=>({tag:n.tagName,cls:n.className,width:n.clientWidth,scroll:n.scrollWidth,overflow:getComputedStyle(n).overflow,contain:getComputedStyle(n).contain})).slice(0,18),offenders:[...document.querySelectorAll('body *')].filter(n=>n.getBoundingClientRect().right>innerWidth+1 && !n.closest('.table-responsive')).map(n=>({tag:n.tagName,cls:n.className,width:n.getBoundingClientRect().width,right:n.getBoundingClientRect().right,overflow:getComputedStyle(n).overflow,position:getComputedStyle(n).position,text:n.textContent.slice(0,70)})).slice(0,12)})''')
                    check('alerts '+mode+' '+str(width)+' no document overflow',overflow['scroll']<=width+1,overflow)
                    page.screenshot(path=str(out/(mode+'_'+str(width)+'.png')),full_page=True)
            form=page.locator('form[action$="/state"]').first;action=form.get_attribute('action')
            form.locator('select').select_option('seen');form.locator('button').click();page.wait_for_load_state('networkidle')
            check('seen status saved for exact alert',page.locator('form[action="'+action+'"]').locator('select').input_value()=='seen')
            form=page.locator('form[action="'+action+'"]');form.locator('select').select_option('resolved');form.locator('button').click();page.wait_for_load_state('networkidle')
            check('resolved status saved',page.locator('form[action="'+action+'"]').locator('select').input_value()=='resolved')
            setting=page.locator('form[action="/dashboard/alerts/settings"]');setting.locator('select').select_option('0');setting.locator('button').click();page.wait_for_load_state('networkidle')
            check('Admin disables notifications',not context.request.get(base+'/dashboard/alerts/feed').json()['enabled'])
            setting=page.locator('form[action="/dashboard/alerts/settings"]');setting.locator('select').select_option('1');setting.locator('button').click();page.wait_for_load_state('networkidle')
            page.goto(base+'/dashboard');expect(page.locator('#alert-live-status')).to_contain_text('nhóm',timeout=10000)
            for depth in range(1,5):context.request.get(base+'/download',params={'path':'../'*depth+'fixture'})
            expect(page.locator('#alert-live-items a')).to_have_count(3,timeout=15000)
            check('UI rate limit keeps at most three notifications',page.locator('#alert-live-items a').count()==3)
            check('rate limit does not drop persisted alerts',context.request.get(base+'/dashboard/alerts/feed').json()['new_count']>=4)
            page.route('**/dashboard/alerts/feed*',lambda route:route.abort())
            expect(page.locator('#alert-live-status')).to_contain_text('Chưa cập nhật',timeout=12000)
            check('polling network failure is visible',True)
            page.unroute('**/dashboard/alerts/feed*')
            expect(page.locator('#alert-live-status')).to_contain_text('nhóm',timeout=20000)
            check('polling recovers after network failure',True)
            check('no JavaScript error',not results['browser_errors'])
            context.close();browser.close()
    except Exception as error:check('browser suite completed',False,str(error))
    finally:
        server.shutdown();server.server_close();thread.join(timeout=5)
        results['passed']=sum(c['result']=='PASS' for c in results['checks']);results['failed']=sum(c['result']=='FAIL' for c in results['checks'])
        (out/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Browser alerts:',results['passed'],'PASS,',results['failed'],'FAIL');print('Evidence:',out.relative_to(ROOT))
    return int(results['failed']>0)


if __name__=='__main__':raise SystemExit(main())
