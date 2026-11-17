"""Optional real Chromium UI checks/screenshots on isolated localhost fixtures.

Install Playwright separately for development; it is not an app dependency.
Uses existing Chrome/Edge, never downloads a browser or touches business DB.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import secrets
import sys
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'.verification/ui_browser_lib'), str(ROOT)]
from tools.pytest_runtime import create_runtime, runtime_environment
from ml.evaluate import sha256
from app import create_app
from werkzeug.serving import make_server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', type=Path, default=Path('C:/Program Files/Google/Chrome/Application/chrome.exe'))
    parser.add_argument('--software-rendering',action='store_true',help='Disable GPU only in the owned headless test browsers')
    args = parser.parse_args()
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as error:
        parser.error('Optional Playwright unavailable (installation/access/import): '+str(error)+'. No browser checks claimed.')
    out = ROOT/'docs/ui'/('browser_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+secrets.token_hex(3))
    out.mkdir(parents=True)
    runtime = create_runtime(ROOT)
    os.environ.update(runtime_environment(runtime))
    tempfile.tempdir = str(runtime['temporary'])
    public = runtime['root']/'shared_files'
    public.mkdir()
    names = ['báo cáo.txt','bao_cao_H07.pdf','architecture.pdf','README.txt','training_metrics.csv','evaluation.json','tailieu/chuong_1.txt','tailieu/chuong_2.txt']
    for name in names:
        file = public/name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text('PUBLIC UI FIXTURE: '+name, encoding='utf-8')
    sentinel = 'OUTSIDE-SENTINEL-'+secrets.token_hex(16)
    (runtime['root']/'private-secret.txt').write_text(sentinel)
    protected = [ROOT/'data/paths_synthetic.csv', ROOT/'artifacts/model.joblib',
                 ROOT/'docs/evaluations/20261116T154448Z_7a27a7/improved_model.joblib', ROOT/'instance/events.sqlite3']
    before = {str(path.relative_to(ROOT)):sha256(path) for path in protected if path.is_file()}
    password = secrets.token_hex(24)
    app = create_app({'FILES_ROOT':public, 'DATABASE':runtime['root']/'ui.sqlite3', 'ADMIN_HASH_FILE':runtime['root']/'admin_password.hash', 'AUDITOR_HASH_FILE':runtime['root']/'auditor_password.hash', 'ADMIN_PASSWORD':password})
    server = make_server('127.0.0.1', 0, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = 'http://127.0.0.1:'+str(server.server_port)
    results = {'created_at_utc':datetime.now(timezone.utc).isoformat(), 'transport':'TCP localhost, real Chromium',
               'fixture_note':'Screenshots use isolated UI files and real fixture requests, original training/model artifacts read-only; no business DB.',
               'checks':[], 'browser_errors':[], 'static_errors':[], 'browser':str(args.browser),
               'launch_args':['--disable-gpu'] if args.software_rendering else [],'screenshots':[]}
    def check(name, passed, actual=None):
        results['checks'].append({'name':name, 'result':'PASS' if passed else 'FAIL', 'actual':actual})
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(executable_path=str(args.browser), headless=True,args=results['launch_args'])
            results['browser_version'] = browser.version
            context = browser.new_context(viewport={'width':1440,'height':1000}, device_scale_factor=1, accept_downloads=True)
            page = context.new_page()
            page.on('pageerror', lambda error:results['browser_errors'].append(str(error)))
            page.on('response',lambda response:results['static_errors'].append({'url':response.url,'status':response.status}) if '/static/' in response.url and response.status>=400 else None)
            def shot(name,view=None):
                (view or page).screenshot(path=str(out/(name+'.png')), full_page=True)
                results['screenshots'].append(name+'.png')
            def navigation_bounds(view,name):
                bounds=view.evaluate('''() => {
                  const controls=[...document.querySelectorAll('.topbar a,.topbar button')].filter(n=>n.getClientRects().length);
                  return controls.filter(n=>{const r=n.getBoundingClientRect();return r.left<0||r.right>innerWidth+1||n.scrollWidth>n.clientWidth+1;}).map(n=>({text:n.textContent.trim(),width:n.clientWidth,scroll:n.scrollWidth}));
                }''')
                check(name+' navbar text/buttons not clipped',not bounds,bounds)
            def no_overflow(name):
                values = page.evaluate('({width:innerWidth,scroll:document.documentElement.scrollWidth})')
                check(name, values['scroll']<=values['width']+1, values)
                navigation_bounds(page,name)
            def contrast(selectors):
                return page.evaluate('''selectors => {
                  const rgb=text=>text.match(/[\\d.]+/g).map(Number);
                  const luminance=color=>rgb(color).slice(0,3).map(n=>{n/=255;return n<=.04045?n/12.92:((n+.055)/1.055)**2.4;}).reduce((sum,n,i)=>sum+n*[.2126,.7152,.0722][i],0);
                  return selectors.map(selector=>{
                    const node=document.querySelector(selector);let ancestor=node;let background='rgb(9,14,26)';
                    while(ancestor){const value=getComputedStyle(ancestor).backgroundColor;const parts=rgb(value);if(parts.length===3||parts[3]===1){background=value;break;}ancestor=ancestor.parentElement;}
                    const style=getComputedStyle(node),a=luminance(style.color),b=luminance(background);
                    return {selector,color:style.color,background,ratio:(Math.max(a,b)+.05)/(Math.min(a,b)+.05),font_px:parseFloat(style.fontSize)};
                  });
                }''',selectors)
            page.goto(url, wait_until='networkidle')
            shot('01_public_desktop')
            no_overflow('public desktop no document overflow')
            page.locator('#file-search').fill('báo cáo')
            visible = page.locator('[data-file-path]:visible').count()
            check('NFC Unicode file search', visible==1, visible)
            page.locator('#file-search').fill('not-present-in-list')
            check('search empty state', page.locator('#file-no-match').is_visible())
            page.locator('#file-search').fill('')
            page.locator('#file-type').select_option('pdf')
            check('extension filter', page.locator('[data-file-path]:visible').count()==2)
            page.locator('#file-type').select_option('')
            with page.expect_download() as info:
                page.locator('[data-file-path="báo cáo.txt"] a').click()
            download = info.value
            check('native Unicode download exact body', Path(download.path()).read_text(encoding='utf-8')=='PUBLIC UI FIXTURE: báo cáo.txt')
            check('download status does not fabricate success', 'Backend sẽ xác minh' in page.locator('#download-feedback').inner_text())
            page.locator('#download-path').fill('../private-secret.txt')
            with page.expect_response(lambda r:'/download?' in r.url) as info:
                page.locator('[data-download-form] button').click()
            response = info.value
            page.wait_for_load_state('networkidle')
            check('native form traversal rejected', response.status==403, response.status)
            shot('02_blocked_request')
            for payload in ['%2e%2e%2fprivate-secret.txt','%252e%252e%252fprivate-secret.txt','missing.txt']:
                response = context.request.get(url+'/download?path='+payload)
                expected = 404 if payload=='missing.txt' else 403
                check('HTTP '+payload, response.status==expected and sentinel not in response.text(), response.status)
            page.goto(url+'/login', wait_until='networkidle')
            shot('03_login_desktop')
            no_overflow('login desktop no document overflow')
            check('login CSRF present', bool(page.locator('form input[name=csrf_token]').input_value()))
            measured=contrast(['.login-panel .form-label','.login-panel>p','.login-panel #password-help','.login-visual>p','.password-toggle'])
            check('critical login text contrast at least 4.5 to 1',all(value['ratio']>=4.5 for value in measured),measured)
            check('presentation login labels and descriptions enlarged',measured[0]['font_px']>=15 and measured[1]['font_px']>=16 and measured[2]['font_px']>=14,measured[:3])
            page.locator('#pw').fill('visibility-fixture-only')
            page.locator('#password-toggle').focus()
            page.keyboard.press('Space')
            check('keyboard reveals password without submitting',page.locator('#pw').get_attribute('type')=='text' and page.locator('#password-toggle').get_attribute('aria-pressed')=='true' and page.url.endswith('/login'))
            page.keyboard.press('Enter')
            check('keyboard hides password and preserves value',page.locator('#pw').get_attribute('type')=='password' and page.locator('#pw').input_value()=='visibility-fixture-only')
            page.locator('#pw').fill('wrong-fixture-password')
            # Observe after ui.js's submit handler, without blocking or mocking
            # navigation/response. Record no input values or credentials.
            loading_states=[]
            page.expose_function('__recordLoginState',lambda state:loading_states.append(state))
            page.evaluate('''() => document.querySelector('.login-panel form').addEventListener('submit',() => {
              const button=document.querySelector('.login-panel button[type=submit]');
              window.__recordLoginState({busy:button.getAttribute('aria-busy'),label:button.textContent,revealBusy:document.getElementById('password-toggle').getAttribute('aria-busy')});
            })''')
            with page.expect_response(lambda r:r.url==url+'/login' and r.request.method=='POST') as info:
                page.locator('.login-panel button[type=submit]').click()
            page.wait_for_load_state('networkidle')
            check('real login submit shows loading on submit, not reveal',bool(loading_states) and loading_states[0]['busy']=='true' and 'Đang xác thực' in loading_states[0]['label'] and loading_states[0]['revealBusy'] is None,loading_states)
            check('failed login is clear and generic',info.value.status==200 and 'Đăng nhập không thành công' in page.locator('[role=alert]').inner_text() and 'wrong-fixture-password' not in page.content() and 'Traceback' not in page.content())
            shot('login_error_desktop')
            page.locator('#pw').fill(password)
            page.locator('.login-panel button[type=submit]').click()
            page.wait_for_url('**/dashboard')
            page.wait_for_load_state('networkidle')
            shot('04_dashboard_desktop')
            no_overflow('dashboard desktop no document overflow')
            check('four real overview cards', page.locator('.stat-grid .stat-card').count()==4)
            charts = page.evaluate("typeof Chart !== 'undefined' && !!Chart.getChart('eventsChart') && !!Chart.getChart('trendChart')")
            check('dashboard charts rendered', bool(charts), {'charts_rendered':charts})
            if charts:
                actual = page.evaluate("({data:Chart.getChart('eventsChart').data.datasets[0].data,source:JSON.parse(document.getElementById('chart-data').textContent)})")
                check('chart data equals backend counts',actual['data']==[actual['source'][k] for k in ('allowed','blocked','missed')],actual)
            page.locator('.sidebar-toggle').click()
            check('desktop sidebar collapses',page.locator('.sidebar-toggle').get_attribute('aria-expanded')=='false')
            check('compact sidebar keeps accessible links',page.get_by_role('link',name='AI Training',exact=True).count()==1)
            page.locator('.sidebar-toggle').click()
            page.locator('#action').select_option('BLOCK')
            page.locator('[data-navigation-form] button').click()
            page.wait_for_load_state('networkidle')
            check('filtered log rows BLOCK', all('BLOCK' in text for text in page.locator('.logs-table tbody tr').all_inner_texts()))
            with page.expect_download() as info:
                page.locator('form[action="/dashboard/logs/export"] button').click()
            exported = Path(info.value.path()).read_text(encoding='utf-8-sig')
            check('filtered CSV export', 'BLOCK' in exported and ',ALLOW,' not in exported and ',MISS,' not in exported)
            page.goto(url+'/dashboard/ai-evaluation',wait_until='networkidle')
            shot('05_evaluation_desktop')
            no_overflow('evaluation desktop no document overflow')
            check('evaluation metrics and confusion images',page.locator('.stat-grid .stat-card').count()==4 and page.locator('img.img-fluid').count()==3)
            check('evaluation comparison chart rendered',page.evaluate("!!Chart.getChart('metricsChart')"))
            check('scientific warning visible',page.locator('.science-warning').is_visible() and 'không chứng minh hệ thống phát hiện hoặc ngăn chặn 100%' in page.locator('.science-warning').inner_text())
            measured=contrast(['.science-warning p','.science-warning h2','.context-facts dt','.context-note'])
            check('scientific warning and metadata text contrast at least 4.5 to 1',all(value['ratio']>=4.5 for value in measured),measured)
            options=page.locator('#evaluation-run option').evaluate_all('(nodes)=>nodes.map(n=>n.value).filter(Boolean)')
            artifacts={name:json.loads((ROOT/'docs/evaluations'/name/'results.json').read_text(encoding='utf-8')) for name in options}
            old=next((name for name,data in artifacts.items() if not data.get('selection')),None)
            strict=next((name for name,data in artifacts.items() if data.get('experiment_type')=='canonical_grouped_validation'),None)
            check('selector includes historical and strict canonical runs',bool(old and strict))
            for kind,run in [('legacy',old),('strict',strict)]:
                if run is None: continue
                page.locator('#evaluation-run').select_option(run)
                page.locator('.run-picker button[type=submit]').click()
                page.wait_for_load_state('networkidle')
                data=artifacts[run]
                selection=data.get('selection') or {}
                values=page.locator('[data-field]').evaluate_all('(nodes)=>Object.fromEntries(nodes.map(n=>[n.dataset.field,n.textContent.trim()]))')
                expected={'fit_samples':selection.get('fit_samples') if selection else data['train_samples'],
                          'validation_samples':selection.get('validation_samples'),'test_samples':data['test_samples'],
                          'refit_samples':data['train_samples'],'canonical_overlap':len(data['split']['canonical_overlap']) if 'canonical_overlap' in data['split'] else None}
                check(kind+' run metadata is exact without fabricated validation',values['run']==run and all(values[key]==(str(value) if value is not None else 'Không được cung cấp') for key,value in expected.items()),{key:values[key] for key in expected})
                source=page.evaluate("JSON.parse(document.getElementById('evaluation-data').textContent)")
                check(kind+' run metrics equal its results.json',source['v1']==data['logistic_regression'] and source['regex']==data['regex'] and source['v2']==data.get('improved_logistic_regression'))
                plotted=page.evaluate("Chart.getChart('metricsChart').data.datasets.map(d=>d.data)")
                methods=[data['logistic_regression']]+([data['improved_logistic_regression']] if 'improved_logistic_regression' in data else [])+[data['regex']]
                check(kind+' run plotted metrics equal source',plotted==[[method[key]*100 for key in ('accuracy','precision','recall','f1')] for method in methods])
                pinned=page.locator('img.img-fluid').evaluate_all('(nodes)=>nodes.map(n=>new URL(n.src).searchParams.get("run"))')
                check(kind+' run image sources remain pinned',len(pinned)==3 and all(name==run for name in pinned),pinned)
                shot('evaluation_'+kind+'_desktop')
            page.locator('.glossary summary').click()
            check('glossary expands with all key terms',page.locator('.glossary').get_attribute('open') is not None and page.locator('.glossary dt').count()==8)
            invalid=context.request.get(url+'/dashboard/ai-evaluation?run=..%2F..%2Finstance')
            check('invalid run does not expose or silently substitute data',invalid.status==200 and 'evaluation-data' not in invalid.text())
            page.goto(url+'/dashboard/ai-training',wait_until='networkidle')
            shot('06_training_desktop')
            no_overflow('training desktop no document overflow')
            check('training real features and read-only labels', 'view_max_parent_components' in page.content() and 'READ-ONLY' in page.content())
            actual=page.evaluate("({data:Chart.getChart('labelsChart').data.datasets[0].data,source:JSON.parse(document.getElementById('training-label-data').textContent)})")
            check('training chart equals CSV counts',actual['data']==[actual['source'].get(k,0) for k in ('0','1')],actual)
            from app.training_view import read_dataset, dataset_page, evaluation_history
            source_rows=read_dataset(app.config['TRAINING_DATA_PATH'])
            check('training first page contains 50 of 10000 real rows',len(source_rows)==10000 and page.locator('#dataset-table tbody tr').count()==50)
            strict_run=next((r['run'] for r in evaluation_history(app.config['EVALUATION_ROOT']) if r.get('experiment_type')=='canonical_grouped_validation'),None)
            check('training defaults to newest validated strict run',bool(strict_run) and page.locator('[data-field=run]').inner_text()==strict_run)
            page.goto(url+'/dashboard/ai-training?page=100&per_page=100',wait_until='networkidle')
            indices=page.locator('#dataset-table tbody tr td:first-child').all_text_contents()
            check('training TCP last page has original CSV indices',indices==[str(i) for i in range(9901,10001)])
            check('training last page disables next navigation',page.locator('a[rel=next]').count()==0 and page.locator('a[rel=prev]').count()==1)
            page.locator('#dataset-q').fill('TXT')
            page.locator('#dataset-label').select_option('1')
            page.locator('#dataset-family').select_option('1-00')
            page.locator('form:has(#dataset-q) button[type=submit]').click()
            page.wait_for_load_state('networkidle')
            expected=dataset_page(source_rows,{'q':'TXT','label':'1','family':'1-00','per_page':'100'})
            indices=page.locator('#dataset-table tbody tr td:first-child').all_text_contents()
            check('training TCP combined search label family matches CSV',indices==[str(r['index']) for r in expected['items']])
            token=page.locator('form:has(input[value=dataset]) input[name=csrf_token]').input_value()
            exported=context.request.post(url+'/dashboard/ai-training/export',form={'kind':'dataset','csrf_token':token})
            import csv, io
            exported_rows=list(csv.DictReader(io.StringIO(exported.body().decode('utf-8-sig'))))
            check('training filtered page exports full 10000 rows via CSRF',exported.status==200 and len(exported_rows)==10000)
            page.goto(url+'/dashboard/ai-training?q=nonexistent-dataset-row',wait_until='networkidle')
            check('training TCP empty results remain truthful','0 / 10000' in page.locator('#dataset-page-summary').inner_text() and 'Không có mẫu phù hợp' in page.locator('#dataset-table').inner_text())
            for width,height,label in [(768,1024,'tablet'),(390,844,'mobile')]:
                page.set_viewport_size({'width':width,'height':height})
                for path,name in [('/','public'),('/dashboard','dashboard'),('/dashboard/ai-evaluation','evaluation'),('/dashboard/ai-training','training'),('/login','login')]:
                    page.goto(url+path,wait_until='networkidle')
                    no_overflow(name+' '+label+' no document overflow')
                    if label=='mobile': shot(name+'_mobile')
                page.goto(url+'/dashboard',wait_until='networkidle')
                check(label+' sidebar initially closed', page.locator('.sidebar-toggle').get_attribute('aria-expanded')=='false')
                page.locator('.sidebar-toggle').click()
                check(label+' sidebar opens',page.locator('.sidebar-toggle').get_attribute('aria-expanded')=='true')
                if label=='mobile': shot('sidebar_mobile')
                page.keyboard.press('Escape')
                check(label+' sidebar Escape closes',page.locator('.sidebar-toggle').get_attribute('aria-expanded')=='false')
            # Public/no-JS and CDN-blocked cases keep native actions and tables.
            offline = browser.new_context(java_script_enabled=False, viewport={'width':390,'height':844})
            native = offline.new_page()
            native.goto(url,wait_until='networkidle')
            check('no-JS native file links available',native.locator('[data-download-link]').count()==len(names))
            offline.close()
            guest=browser.new_context()
            guest_page=guest.new_page()
            for width,height in [(1440,1000),(768,1024),(390,844)]:
                guest_page.set_viewport_size({'width':width,'height':height})
                guest_page.goto(url+'/login',wait_until='networkidle')
                navigation_bounds(guest_page,'guest login '+str(width))
                check('guest login '+str(width)+' no document overflow',guest_page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'))
                shot('login_guest_'+str(width),guest_page)
            guest.close()
            from tools.ui_theme_checks import verify_themes
            verify_themes(browser,url,context,check,out,results,args.browser,results['launch_args'])
            from tools.ui_text_size_checks import verify_text_sizes
            verify_text_sizes(browser,url,context,check,out,results)
            from tools.ui_brand_checks import verify_branding
            verify_branding(browser,url,context,check,out,results)
            from tools.ui_password_checks import verify_password_change
            verify_password_change(browser,url,context,check,out,results,password)
            check('no JavaScript runtime errors',not results['browser_errors'],results['browser_errors'])
            check('all local static assets load',not results['static_errors'],results['static_errors'])
            context.close()
            browser.close()
    except Exception as error:
        check('browser suite completed',False,str(error))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=10)
        results['protected_unchanged'] = {path:sha256(ROOT/path)==digest for path,digest in before.items()}
        results['passed'] = sum(c['result']=='PASS' for c in results['checks'])
        results['failed'] = sum(c['result']=='FAIL' for c in results['checks'])
        (out/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
        (out/'manifest.json').write_text(json.dumps({p.name:sha256(p) for p in out.iterdir() if p.is_file()},indent=2),encoding='utf-8')
    print('Browser checks:',results['passed'],'PASS,',results['failed'],'FAIL')
    print('Evidence:',out.relative_to(ROOT))
    return int(results['failed']>0 or not all(results['protected_unchanged'].values()))


if __name__=='__main__':
    raise SystemExit(main())
