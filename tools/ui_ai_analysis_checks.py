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
    check('provider received no raw path IP token or filename',sentinel not in str(provider.calls) and '127.0.0.1' not in str(provider.calls) and set(provider.calls[0])=={'decision','ml_alert','parent_components','absolute_style','backslash','structural_encoding','remaining_decode_changes','length_bucket'})
    provider.release.set()
    done=threading.Event();threading.Thread(target=lambda:(service.queue.join(),done.set()),daemon=True).start()
    check('background explanation completes',done.wait(5))
    page.reload(wait_until='networkidle')
    check('Dashboard shows validated fixture explanation',page.locator('#ai-analysis').get_by_text('Adapter fixture:',exact=False).count()>0)
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
