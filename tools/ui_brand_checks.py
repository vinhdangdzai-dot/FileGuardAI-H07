"""Visible product identity, native responsive controls and real screenshots."""

def verify_branding(browser,url,context,check,out,results):
    page=context.new_page()
    page.on('pageerror',lambda error:results['browser_errors'].append(str(error)))
    expected='CANH G\u00c1C S\u1ed0'
    routes=[('/','public'),('/login','login'),('/dashboard','dashboard'),('/dashboard/ai-training','training'),('/dashboard/ai-evaluation','evaluation'),('/account/password','account')]
    for mode in ['light','dark']:
        for width in [1440,768,390]:
            page.set_viewport_size({'width':width,'height':1000})
            for route,name in routes:
                page.goto(url+route,wait_until='networkidle')
                page.locator('#theme-toggle').click();page.locator('[data-theme-choice='+mode+']').click()
                management=page.locator('.management-shell').count()>0
                if management and width<=900:
                    page.locator('.sidebar-toggle').click()
                    page.wait_for_function('() => document.getElementById("sidebar").getBoundingClientRect().left >= -1')
                if management and width>900 and page.locator('body').evaluate('(node)=>node.classList.contains("sidebar-collapsed")'):page.locator('.sidebar-toggle').click()
                actual=page.locator('.brand').evaluate('''node=>({name:node.querySelector('.brand-title').textContent,author:node.querySelector('.brand-author').textContent,bounds:[...node.querySelectorAll('.brand-title,.brand-author,.brand-svg')].map(n=>{const r=n.getBoundingClientRect();return {left:r.left,right:r.right,visible:!!n.getClientRects().length};})})''')
                check(f'brand {mode} {width} {name}: exact identity title and bounds',actual['name']==expected and actual['author']=='by HuuVinh' and expected in page.title() and all(n['visible'] and n['left']>=0 and n['right']<=width+1 for n in actual['bounds']),actual)
                if management and width<=900:
                    if width==390 and name=='dashboard':
                        filename=f'brand_{mode}_sidebar_390.png';page.screenshot(path=str(out/filename),full_page=True);results['screenshots'].append(filename)
                    page.keyboard.press('Escape')
                    page.wait_for_function('() => document.getElementById("sidebar").getBoundingClientRect().right <= 1')
                if width in [1440,390]:
                    filename=f'brand_{mode}_{name}_{width}.png';page.screenshot(path=str(out/filename),full_page=True);results['screenshots'].append(filename)
    page.set_viewport_size({'width':1440,'height':1000});page.goto(url+'/dashboard',wait_until='networkidle')
    if page.locator('body').evaluate('(n)=>n.classList.contains("sidebar-collapsed")'):page.locator('.sidebar-toggle').click()
    page.locator('.sidebar-toggle').click()
    check('collapsed sidebar keeps shield logo and hides brand copy',page.locator('.sidebar .brand-svg').is_visible() and not page.locator('.sidebar .brand-copy').is_visible())
    page.locator('.sidebar-toggle').click();page.close()
