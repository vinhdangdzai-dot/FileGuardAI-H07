"""Real browser/TCP checks with an explicitly fake provider; no API key/network."""
import threading
from app.ai_explanations import ProviderError


class FixtureProvider:
    identity='fixture-adapter-no-external-api'
    def __init__(self):
        self.started=threading.Event();self.release=threading.Event();self.calls=[];self.error=None
    def analyze(self,features):
        self.calls.append(features);self.started.set()
        if not self.release.wait(30):raise ProviderError('timeout')
        if self.error:raise self.error
        return {'why':'Adapter fixture: coarse parent/encoding indicators; no real external API call.',
                'traversal_type':'structural indicators only','risk':'high',
                'recommendations':'Keep independent safe path checks. This is a fixture explanation, not a live provider result.'}


def verify_ai_analysis(browser,url,context,check,out,results,service,provider):
    page=context.new_page()
    page.goto(url+'/dashboard',wait_until='networkidle')
    form=page.locator('form[action="/dashboard/ai-analysis/settings"]')
    check('AI explanation starts disabled',form.locator('select').input_value()=='0' and not provider.calls)
    rejected=context.request.post(url+'/dashboard/ai-analysis/settings',form={'enabled':'1'})
    check('AI settings TCP enforces CSRF',rejected.status==403)
    form.locator('select').select_option('1');form.locator('button[type=submit]').click();page.wait_for_load_state('networkidle')
    check('Admin enables API supplement through real form',service.snapshot()['enabled'])
    sentinel='PRIVATE_PATH_PASSWORD_TOKEN_317829'
    response=context.request.get(url+'/download',params={'path':'../'+sentinel},timeout=2000)
    check('blocked response completes while API provider is still waiting',response.status==403 and provider.started.wait(2) and not provider.release.is_set())
    live=context.request.get(url+'/dashboard/alerts/feed?after=0').json()
    check('local alert exists before Gemini completes',bool(live['items']) and not provider.release.is_set())
    check('provider received no raw path IP token or filename',sentinel not in str(provider.calls) and '127.0.0.1' not in str(provider.calls) and set(provider.calls[0])=={'decision','ml_alert','parent_components','absolute_style','backslash','structural_encoding','remaining_decode_changes','length_bucket'})
    provider.release.set()
    done=threading.Event();threading.Thread(target=lambda:(service.queue.join(),done.set()),daemon=True).start()
    check('background explanation completes',done.wait(5))
    page.reload(wait_until='networkidle')
    check('Dashboard shows validated fixture explanation',page.locator('#ai-analysis').get_by_text('Adapter fixture:',exact=False).count()>0)
    event_id=service.snapshot()['rows'][0]['event_id']
    detail=context.new_page()
    detail.on('pageerror',lambda error:results['browser_errors'].append(str(error)))
    for mode in ['light','dark']:
        for width in [1440,768,390]:
            detail.set_viewport_size({'width':width,'height':1000})
            detail.goto(url+'/dashboard/events/'+str(event_id),wait_until='networkidle')
            detail.locator('#theme-toggle').click()
            detail.locator('[data-theme-choice='+mode+']').click()
            check('event detail theme '+mode+' '+str(width),detail.locator('html').get_attribute('data-bs-theme')==mode)
            check('event detail '+mode+' '+str(width)+' displays fixture explanation',detail.get_by_text('Adapter fixture:',exact=False).count()>0)
            bounds=detail.evaluate('({width:innerWidth,scroll:document.documentElement.scrollWidth})')
            check('event detail '+mode+' '+str(width)+' no document overflow',bounds['scroll']<=bounds['width']+1,bounds)
            filename='event_detail_fixture_'+mode+'_'+str(width)+'.png'
            detail.screenshot(path=str(out/filename),full_page=True);results['screenshots'].append(filename)
    detail.close()
    alerts=context.new_page()
    alerts.on('pageerror',lambda error:results['browser_errors'].append(str(error)))
    alerts.goto(url+'/dashboard/alerts',wait_until='networkidle')
    alerts.locator('#alert-live-status').filter(has_text='nhóm').wait_for(timeout=10000)
    before=context.request.get(url+'/dashboard/alerts/feed').json()
    context.request.get(url+'/download',params={'path':'../../'+sentinel})
    from playwright.sync_api import expect
    expect(alerts.locator('#alert-live-items')).to_contain_text('Cảnh báo #',timeout=15000)
    check('Dashboard polling displays a new local alert',alerts.locator('#alert-live-items a').count()>0)
    for mode in ['light','dark']:
        for width in [1440,768,390]:
            alerts.set_viewport_size({'width':width,'height':1000})
            alerts.locator('#theme-toggle').click();alerts.locator('[data-theme-choice='+mode+']').click()
            bounds=alerts.evaluate('({width:innerWidth,scroll:document.documentElement.scrollWidth})')
            check('alert manager '+mode+' '+str(width)+' fits screen',bounds['scroll']<=bounds['width']+1,bounds)
            filename='alerts_fixture_'+mode+'_'+str(width)+'.png';alerts.screenshot(path=str(out/filename),full_page=True);results['screenshots'].append(filename)
    form=alerts.locator('form[action^="/dashboard/alerts/"][action$="/state"]').first
    action=form.get_attribute('action')
    form.locator('select').select_option('seen');form.locator('button').click();alerts.wait_for_load_state('networkidle')
    check('Admin updates alert through real form',alerts.locator('form[action="'+action+'"]').locator('select').input_value()=='seen')
    alerts.close()
    for mode in ['light','dark']:
        page.locator('#theme-toggle').click();page.locator('[data-theme-choice='+mode+']').click()
        page.locator('#ai-analysis details').first.locator('summary').click()
        filename='ai_analysis_mock_'+mode+'.png';page.locator('#ai-analysis').screenshot(path=str(out/filename));results['screenshots'].append(filename)
        page.locator('#ai-analysis details').first.locator('summary').click()
    provider.error=ProviderError('quota')
    response=context.request.get(url+'/download',params={'path':'C:/'+sentinel},timeout=2000)
    done=threading.Event();threading.Thread(target=lambda:(service.queue.join(),done.set()),daemon=True).start()
    check('API quota failure keeps HTTP403 and local enforcement',response.status==403 and done.wait(5) and service.snapshot()['rows'][0]['status']=='quota')
    page.reload(wait_until='networkidle');form=page.locator('form[action="/dashboard/ai-analysis/settings"]')
    form.locator('select').select_option('0');form.locator('button[type=submit]').click();page.wait_for_load_state('networkidle')
    count=len(provider.calls);context.request.get(url+'/download',params={'path':'../../'+sentinel})
    done=threading.Event();threading.Thread(target=lambda:(service.queue.join(),done.set()),daemon=True).start()
    check('Admin disabling stops new provider calls',done.wait(5) and len(provider.calls)==count and not service.snapshot()['enabled'])
    page.close()
