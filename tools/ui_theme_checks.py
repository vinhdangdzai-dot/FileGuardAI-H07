"""Optional Playwright checks; real localhost UI, no model/data mutation."""
import json
from pathlib import Path
from tools.pytest_runtime import create_runtime

ROOT=Path(__file__).resolve().parents[1]


def verify_themes(browser,url,context,check,out,results,browser_path,launch_args):
    def attach(page):
        page.on('pageerror',lambda error:results['browser_errors'].append(str(error)))
        page.on('response',lambda response:results['static_errors'].append({'url':response.url,'status':response.status}) if '/static/' in response.url and response.status>=400 else None)
        page.add_init_script('''window.__themeBoot=[];document.addEventListener('fileguard:themechange',()=>window.__themeBoot.push({theme:document.documentElement.dataset.bsTheme,ready:document.readyState,styles:document.styleSheets.length}));''')
    page=context.new_page()
    attach(page)

    def choose(view,mode):
        view.locator('#theme-toggle').click()
        view.locator('[data-theme-choice="'+mode+'"]').click()
        view.wait_for_function('(mode)=>document.documentElement.dataset.themePreference===mode',arg=mode)
        view.wait_for_function('''() => [...document.querySelectorAll('canvas')].every(canvas=>{
          if(!canvas.width||!canvas.height||typeof Chart==='undefined'||!Chart.getChart(canvas))return false;
          const pixels=canvas.getContext('2d').getImageData(0,0,canvas.width,canvas.height).data;
          return pixels.some((value,index)=>index%4===3&&value>0);
        })''')

    def chart_state(view):
        return view.evaluate('''() => typeof Chart==='undefined'?[]:[...document.querySelectorAll('canvas')].map(canvas=>{
          const chart=Chart.getChart(canvas);return chart?{canvas:canvas.id,id:chart.id,values:chart.data.datasets.map(d=>d.data),colors:chart.data.datasets.map(d=>d.backgroundColor),text:chart.options.color}:null;
        })''')

    def no_clip(view,label):
        values=view.evaluate('''() => ({width:innerWidth,scroll:document.documentElement.scrollWidth,bad:[...document.querySelectorAll('.topbar a,.topbar button')].filter(n=>n.getClientRects().length).filter(n=>{const r=n.getBoundingClientRect();return r.left<0||r.right>innerWidth+1||n.scrollWidth>n.clientWidth+1;}).map(n=>n.textContent.trim())})''')
        check(label+' no page/nav clipping',values['scroll']<=values['width']+1 and not values['bad'],values)

    def colors(view,label):
        data=view.evaluate('''() => {
          const node=document.querySelector('.panel')||document.querySelector('main');
          const c=getComputedStyle(node),body=getComputedStyle(document.body);
          return {theme:document.documentElement.dataset.bsTheme,body:body.backgroundColor,surface:c.backgroundColor,text:c.color,muted:getComputedStyle(document.documentElement).getPropertyValue('--muted').trim()};
        }''')
        check(label+' correct background palette',data['body']==('rgb(244, 247, 251)' if data['theme']=='light' else 'rgb(9, 14, 26)'),data)

    def snapshot(view,name):
        view.screenshot(path=str(out/(name+'.png')),full_page=True)
        results['screenshots'].append(name+'.png')

    pages=[('/','public'),('/login','login'),('/dashboard','dashboard'),('/dashboard/ai-evaluation','evaluation'),('/dashboard/ai-training','training')]
    for width,height in [(1440,1000),(768,1024),(390,844)]:
        page.set_viewport_size({'width':width,'height':height})
        for path,name in pages:
            page.goto(url+path,wait_until='networkidle')
            for theme in ['light','dark']:
                before=chart_state(page)
                page.evaluate('window.__themeDocumentMarker="same-document"')
                choose(page,theme)
                check(name+' '+str(width)+' '+theme+' immediate preference',page.evaluate('(mode)=>document.documentElement.dataset.bsTheme===mode&&localStorage.getItem("fg-theme")===mode&&window.__themeDocumentMarker==="same-document"',theme))
                no_clip(page,name+' '+str(width)+' '+theme)
                colors(page,name+' '+str(width)+' '+theme)
                after=chart_state(page)
                check(name+' '+str(width)+' '+theme+' chart values/instances preserved',all(item is not None for item in after) and [(item['id'],item['values']) for item in before]==[(item['id'],item['values']) for item in after])
                if after:
                    expected=page.evaluate('getComputedStyle(document.documentElement).getPropertyValue("--muted").trim()')
                    check(name+' '+str(width)+' '+theme+' chart text recolored',all(item['text']==expected for item in after),[item['text'] for item in after])
                if width in (1440,390): snapshot(page,'theme_'+theme+'_'+name+'_'+str(width))

    page.set_viewport_size({'width':1440,'height':1000})
    page.goto(url+'/dashboard',wait_until='networkidle')
    choose(page,'light')
    light=chart_state(page)
    choose(page,'dark')
    dark=chart_state(page)
    check('theme changes chart palette without changing numbers',[x['colors'] for x in light]!=[x['colors'] for x in dark] and [x['values'] for x in light]==[x['values'] for x in dark])
    page.emulate_media(color_scheme='dark')
    choose(page,'light')
    page.goto(url+'/login',wait_until='networkidle')
    boot=page.evaluate('window.__themeBoot[0]')
    check('stored light applies before CSS despite dark OS',boot=={'theme':'light','ready':'loading','styles':0},boot)
    page.locator('#theme-toggle').focus()
    page.keyboard.press('ArrowDown')
    check('theme menu keyboard opens on selected choice',page.locator('[data-theme-choice=light]').evaluate('(n)=>n===document.activeElement'))
    page.keyboard.press('ArrowDown')
    page.keyboard.press('Enter')
    check('theme menu keyboard selects dark and returns focus',page.evaluate('document.documentElement.dataset.bsTheme==="dark"&&document.activeElement.id==="theme-toggle"'))
    page.locator('#theme-toggle').click()
    page.keyboard.press('Escape')
    check('theme menu Escape closes',page.locator('#theme-menu').is_hidden() and page.locator('#theme-toggle').get_attribute('aria-expanded')=='false')
    choose(page,'system')
    page.emulate_media(color_scheme='light')
    page.wait_for_function('() => document.documentElement.dataset.bsTheme==="light"')
    check('system preference follows live OS light',page.evaluate('document.documentElement.dataset.themePreference==="system"'))
    page.emulate_media(color_scheme='dark')
    page.wait_for_function('() => document.documentElement.dataset.bsTheme==="dark"')
    check('system preference follows live OS dark',page.evaluate('document.documentElement.dataset.bsTheme==="dark"&&document.documentElement.dataset.themePreference==="system"'))
    choose(page,'light')
    page.emulate_media(color_scheme='dark')
    check('explicit preference overrides OS',page.evaluate('document.documentElement.dataset.bsTheme==="light"'))

    other=context.new_page()
    attach(other)
    other.goto(url+'/login',wait_until='networkidle')
    choose(page,'dark')
    other.wait_for_function('() => document.documentElement.dataset.bsTheme==="dark"')
    check('preference synchronizes across tabs',other.evaluate('document.documentElement.dataset.themePreference==="dark"'))
    other.close()

    # Actual headless browser close/reopen with a test-only owned profile.
    runtime=create_runtime(ROOT)
    profile=runtime['root']/'theme_browser_profile'
    first=browser.browser_type.launch_persistent_context(str(profile),executable_path=str(browser_path),headless=True,color_scheme='dark',args=launch_args)
    first_page=first.pages[0]
    attach(first_page)
    first_page.goto(url+'/login',wait_until='networkidle')
    choose(first_page,'light')
    first.close()
    reopened=browser.browser_type.launch_persistent_context(str(profile),executable_path=str(browser_path),headless=True,color_scheme='dark',args=launch_args)
    restored=reopened.pages[0]
    attach(restored)
    restored.goto(url+'/login',wait_until='networkidle')
    check('preference survives real browser restart',restored.evaluate('document.documentElement.dataset.bsTheme==="light"&&localStorage.getItem("fg-theme")==="light"'))
    reopened.close()

    blocked=browser.new_context(color_scheme='light')
    unavailable=blocked.new_page()
    attach(unavailable)
    unavailable.add_init_script('''Storage.prototype.getItem=function(){throw new DOMException('Storage denied','SecurityError')};Storage.prototype.setItem=function(){throw new DOMException('Storage denied','SecurityError')};''')
    unavailable.goto(url+'/login',wait_until='networkidle')
    check('blocked storage falls back to system without crashing',unavailable.evaluate('document.documentElement.dataset.themePreference==="system"&&document.documentElement.dataset.bsTheme==="light"'))
    choose(unavailable,'dark')
    check('blocked storage still allows in-page switching',unavailable.evaluate('document.documentElement.dataset.bsTheme==="dark"'))
    blocked.close()

    # Real backend 503 on a fixture logging outage; never fake an HTTP response.
    from unittest.mock import patch
    import sqlite3
    for theme in ['light','dark']:
        choose(page,theme)
        for path,code in [('/download?path=../private-secret.txt',403),('/download?path=missing.txt',404)]:
            response=page.goto(url+path,wait_until='networkidle')
            check(theme+' error '+str(code)+' themed',response.status==code and page.evaluate('(mode)=>document.documentElement.dataset.bsTheme===mode',theme))
            snapshot(page,'theme_'+theme+'_error_'+str(code))
        with patch('app.web.insert_log',side_effect=sqlite3.OperationalError('fixture-only log outage')):
            response=page.goto(url+'/download?path=b%C3%A1o%20c%C3%A1o.txt',wait_until='networkidle')
        check(theme+' error 503 themed',response.status==503 and page.evaluate('(mode)=>document.documentElement.dataset.bsTheme===mode',theme))
        snapshot(page,'theme_'+theme+'_error_503')
    page.close()
