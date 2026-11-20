"""Real HTTP/UI change on owned credentials only; never business credentials."""
import secrets


def verify_password_change(browser,url,context,check,out,results,password):
    page=context.new_page()
    page.on('pageerror',lambda error:results['browser_errors'].append(str(error)))
    page.goto(url+'/account/password',wait_until='networkidle')
    check('account link visible for admin',page.locator('.account-link').count()==1)
    for mode in ['light','dark']:
        page.locator('#theme-toggle').click();page.locator('[data-theme-choice='+mode+']').click()
        for width in [1440,768,390]:
            page.set_viewport_size({'width':width,'height':1000})
            check(f'password form {mode} {width} responsive',page.evaluate('document.documentElement.scrollWidth<=innerWidth+1') and page.locator('input[type=password]').count()==3)
            name=f'password_{mode}_{width}.png';page.screenshot(path=str(out/name),full_page=True);results['screenshots'].append(name)
    for field in ['current_password','new_password','confirm_password']:
        button=page.locator('[data-reveal='+field+']');button.focus();page.keyboard.press('Space')
        check('password keyboard reveal '+field,page.locator('#'+field).get_attribute('type')=='text')
        page.keyboard.press('Space')
    other=browser.new_context(storage_state=context.storage_state())
    check('other admin session valid before password change',other.request.get(url+'/dashboard',max_redirects=0).status==200)
    csrf=page.locator('form[action="/account/password"] input[name=csrf_token]').input_value()
    rejected=context.request.post(url+'/account/password',form={'current_password':password})
    check('password TCP CSRF rejected',rejected.status==403)
    bad='incorrect-fixture-'+secrets.token_hex(12)
    wrong=context.request.post(url+'/account/password',form={'csrf_token':csrf,'current_password':bad,'new_password':bad,'confirm_password':bad})
    check('password TCP incorrect current rejected without reflection',wrong.status==403 and bad not in wrong.text())
    new=secrets.token_hex(3)
    page.locator('#current_password').fill(password);page.locator('#new_password').fill(new);page.locator('#confirm_password').fill(new)
    page.locator('form[action="/account/password"] button[type=submit]').click();page.wait_for_url('**/login');page.wait_for_load_state('networkidle')
    check('password UI success forces reauthentication','role="status"' in page.content() and page.locator('input[name=csrf_token]').count()==1)
    check('previous admin session revoked by server',other.request.get(url+'/dashboard',max_redirects=0).status==302)
    page.locator('#pw').fill(password);page.locator('.login-panel button[type=submit]').click();page.wait_for_load_state('networkidle')
    check('old password rejected after change',page.url.endswith('/login') and page.locator('.login-feedback').count()==1)
    page.locator('#pw').fill(new);page.locator('.login-panel button[type=submit]').click()
    from tools.mfa_fixture import complete_browser
    complete_browser(page)
    page.wait_for_url('**/dashboard');page.wait_for_load_state('networkidle')
    check('new password immediately authenticates',page.url.endswith('/dashboard'))
    page.close();other.close()
