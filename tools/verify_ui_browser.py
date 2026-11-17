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
    app = create_app({'FILES_ROOT':public, 'DATABASE':runtime['root']/'ui.sqlite3', 'ADMIN_PASSWORD':password})
    server = make_server('127.0.0.1', 0, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = 'http://127.0.0.1:'+str(server.server_port)
    results = {'created_at_utc':datetime.now(timezone.utc).isoformat(), 'transport':'TCP localhost, real Chromium',
               'fixture_note':'Screenshots use isolated UI files and real fixture requests, original training/model artifacts read-only; no business DB.',
               'checks':[], 'browser_errors':[], 'static_errors':[], 'browser':str(args.browser), 'screenshots':[]}
    def check(name, passed, actual=None):
        results['checks'].append({'name':name, 'result':'PASS' if passed else 'FAIL', 'actual':actual})
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(executable_path=str(args.browser), headless=True)
            results['browser_version'] = browser.version
            context = browser.new_context(viewport={'width':1440,'height':1000}, device_scale_factor=1, accept_downloads=True)
            page = context.new_page()
            page.on('pageerror', lambda error:results['browser_errors'].append(str(error)))
            page.on('response',lambda response:results['static_errors'].append({'url':response.url,'status':response.status}) if '/static/' in response.url and response.status>=400 else None)
            def shot(name):
                page.screenshot(path=str(out/(name+'.png')), full_page=True)
                results['screenshots'].append(name+'.png')
            def no_overflow(name):
                values = page.evaluate('({width:innerWidth,scroll:document.documentElement.scrollWidth})')
                check(name, values['scroll']<=values['width']+1, values)
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
            check('login CSRF present', bool(page.locator('form input[name=csrf_token]').input_value()))
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
            check('evaluation metrics and confusion images',page.locator('.stat-grid .stat-card').count()==4 and page.locator('img.img-fluid').count()==3)
            check('evaluation comparison chart rendered',page.evaluate("!!Chart.getChart('metricsChart')"))
            page.goto(url+'/dashboard/ai-training',wait_until='networkidle')
            shot('06_training_desktop')
            check('training real features and read-only labels', 'view_max_parent_components' in page.content() and 'READ-ONLY' in page.content())
            actual=page.evaluate("({data:Chart.getChart('labelsChart').data.datasets[0].data,source:JSON.parse(document.getElementById('training-label-data').textContent)})")
            check('training chart equals CSV counts',actual['data']==[actual['source'].get(k,0) for k in ('0','1')],actual)
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
