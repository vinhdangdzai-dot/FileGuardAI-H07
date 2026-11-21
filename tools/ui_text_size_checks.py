"""Live typography and reflow checks; zoom emulation is explicitly identified."""

def verify_text_sizes(browser,url,context,check,out,results):
    page=context.new_page()
    page.on('pageerror',lambda error:results['browser_errors'].append(str(error)))
    routes=[('/','public'),('/login','login'),('/dashboard','dashboard'),('/dashboard/ai-evaluation','evaluation'),('/dashboard/ai-training','training')]
    for mode in ['light','dark']:
        for width in [1440,768,390]:
            page.set_viewport_size({'width':width,'height':1000})
            for route,name in routes:
                page.goto(url+route,wait_until='networkidle')
                page.locator('#theme-toggle').click();page.locator('[data-theme-choice='+mode+']').click()
                for size,pixels in [('small',16),('medium',18),('large',20)]:
                    page.locator('button[data-text-size='+size+']').click()
                    data=page.evaluate('''() => {
                      const root=parseFloat(getComputedStyle(document.documentElement).fontSize);
                      const controls=[...document.querySelectorAll('.topbar button,.topbar a')].filter(n=>n.getClientRects().length);
                      const clipped=controls.filter(n=>{const r=n.getBoundingClientRect();return r.left<0||r.right>innerWidth+1||n.scrollWidth>n.clientWidth+1;}).map(n=>n.textContent);
                      const fonts=Object.fromEntries(['body','h1','h2','.btn','.form-control','.table','.table th','.status','.side-link','.context-note'].map(s=>[s,document.querySelector(s)?parseFloat(getComputedStyle(document.querySelector(s)).fontSize):null]));
                      return {root,clipped,overflow:document.documentElement.scrollWidth>innerWidth+1,fonts};
                    }''')
                    check(f'type {mode} {width} {name} {size}: scale and reflow',data['root']==pixels and not data['overflow'] and not data['clipped'] and all(value is None or value>=pixels*8/9-.01 for value in data['fonts'].values()),data)
                    if width in [1440,390] and size in ['medium','large'] and mode=='dark':
                        filename=f'type_{size}_{name}_{width}.png'
                        page.screenshot(path=str(out/filename),full_page=True);results['screenshots'].append(filename)
    page.goto(url+'/dashboard',wait_until='networkidle')
    old=page.evaluate("Chart.getChart('eventsChart').data.datasets[0].data.slice()")
    page.locator('button[data-text-size=medium]').focus();page.keyboard.press('Enter')
    page.locator('button[data-text-size=large]').focus();page.keyboard.press('Space')
    check('text controls keyboard and chart labels scale',page.locator('button[data-text-size=large]').get_attribute('aria-pressed')=='true' and page.evaluate("Chart.getChart('eventsChart').options.plugins.legend.labels.font.size")>=17.77 and page.evaluate("Chart.getChart('eventsChart').data.datasets[0].data")==old)
    page.reload(wait_until='networkidle')
    check('text preference persists through reload',page.evaluate('getComputedStyle(document.documentElement).fontSize')=='20px')
    # Desktop browser zoom reduces the CSS viewport. Emulate the same layout
    # width and raster scale through CDP; do not claim native Ctrl+plus coverage.
    session=context.new_cdp_session(page)
    results['text_zoom_method']='CDP viewport/device-scale emulation of desktop zoom reflow; native browser zoom shortcuts not verified'
    for width in [1440,768,390]:
        for zoom in [1.25,1.5,2]:
            session.send('Emulation.setDeviceMetricsOverride',{'width':int(width/zoom),'height':int(1000/zoom),'deviceScaleFactor':zoom,'mobile':False})
            for route,name in routes:
                page.goto(url+route,wait_until='networkidle')
                info=page.evaluate('''() => ({width:innerWidth,scroll:document.documentElement.scrollWidth,buttons:[...document.querySelectorAll('.topbar button')].filter(n=>n.getClientRects().length).every(n=>{const r=n.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth+1;})})''')
                check(f'zoom reflow emulated {width} {zoom*100:g}% {name}',info['scroll']<=info['width']+1 and info['buttons'],info)
    session.send('Emulation.clearDeviceMetricsOverride')
    session.detach();page.close()
