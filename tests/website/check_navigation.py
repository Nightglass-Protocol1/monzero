"""Shared navigation acceptance; external data requests are blocked."""
import importlib.util, socket, subprocess, time, shutil
from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[2]
routes=['/faucet/','/mining/leaderboard/','/developers/api/','/ecosystem/','/exchanges/','/markets/','/payments/request/','/developers/payments/','/developers/','/community/bounties/','/community/','/network/','/','/explorer/','/stats/','/wallets/','/app/','/founder/','/fund/','/roadmap/','/security/','/mining/calculator/','/mining/dashboard/','/mining/benchmarks/','/network/nodes/','/mining/benchmarks/submission.html']
submenu_paths={'/','/network/nodes/','/faucet/','/mining/calculator/'}
def check_submenus(page,js,width,path):
 mining=page.locator('#site-nav .nav-group:has(> a:text-is("Mining"))');sub=mining.locator('.nav-sub');toggle=mining.locator('.nav-sub-toggle')
 assert sub.locator('a').all_inner_texts()==['How to mine','Mining calculator','Your mining','CPU benchmarks','Mining leaderboard','Faucet'],path
 if not js:return
 if width>=1340:
  assert not sub.is_visible(),path
  mining.locator('> a').hover();assert sub.is_visible(),path
  page.mouse.move(5,900);assert not sub.is_visible(),path
  explorer=page.locator('#site-nav .nav-group:has(> a:text-is("Explorer"))')
  explorer.locator('.nav-sub-toggle').click();assert explorer.locator('.nav-sub').is_visible() and explorer.locator('.nav-sub-toggle').get_attribute('aria-expanded')=='true',path
  page.mouse.move(5,900);assert explorer.locator('.nav-sub').is_visible(),path  # clicked open stays open
  page.keyboard.press('Escape');assert not explorer.locator('.nav-sub').is_visible() and explorer.locator('.nav-sub-toggle').get_attribute('aria-expanded')=='false',path
  # Keyboard: Tab from the top link reaches the toggle, then the first submenu link, which shows the submenu.
  explorer.locator('> a').focus();page.keyboard.press('Tab');assert explorer.locator('.nav-sub-toggle').evaluate('b=>b===document.activeElement'),path
  page.keyboard.press('Tab');assert explorer.locator('.nav-sub a').first.evaluate('a=>a===document.activeElement') and explorer.locator('.nav-sub').is_visible(),path
  page.keyboard.press('Escape');assert not explorer.locator('.nav-sub').is_visible(),path
 else:
  page.locator('.site-header .menu-toggle').click();assert not sub.is_visible(),path
  toggle.click();assert sub.is_visible() and toggle.get_attribute('aria-expanded')=='true',path
  assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),path
  toggle.click();assert not sub.is_visible(),path
  page.keyboard.press('Escape')
with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
server=subprocess.Popen(['php','-S',f'127.0.0.1:{port}','-t',str(root/'website')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
try:
 for _ in range(50):
  try:
   with socket.create_connection(('127.0.0.1',port),timeout=.2):break
  except OSError:time.sleep(.1)
 else:raise RuntimeError('Preview unavailable')
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True,executable_path=shutil.which('chromium'))
  for js,width in [(True,1440),(True,1300),(True,390),(False,390)]:
   for path in routes:
    page=browser.new_page(java_script_enabled=js,viewport={'width':width,'height':1000})
    def intercept(r):
     if '.php' in r.request.url or not r.request.url.startswith(f'http://127.0.0.1:{port}/'):r.fulfill(status=503,json={'error':'fixture offline'})
     else:r.continue_()
    page.route('**/*',intercept);page.goto(f'http://127.0.0.1:{port}'+path)
    menu=page.locator('.site-header .menu-toggle');links=page.locator('.site-header nav a')
    assert links.count()>0,path
    if js and menu.count() and menu.is_visible():
     menu.click();assert page.locator('#site-nav').is_visible(),path
     page.keyboard.press('Escape');assert not page.locator('#site-nav').is_visible(),path
    if width==1440:
     assert page.locator('.site-header nav').is_visible(),path
    # Every page uses the homepage header: logo, the same twelve links and the Download button.
    assert page.locator('.site-header .brand img').evaluate('(img)=>img.complete && img.naturalWidth > 0'),path
    if path!='/':
     assert [a.strip() for a in page.locator('#site-nav > a, #site-nav > .nav-group > a').all_inner_texts()]==['Home','Explorer','Stats','Public wallets','Studio','Roadmap','Whitepaper','Mining','Pool','Founder','Donate','Security'],path
    if width<1340:assert menu.count()==1,path
    # Every page reaches every public route through the menu or its submenus.
    hrefs={h.split('?')[0] for h in page.locator('#site-nav a').evaluate_all('(as)=>as.map(a=>new URL(a.getAttribute("href"),location.href).pathname)')}
    missing=[r for r in routes if r.split('#')[0] not in hrefs and r!='/mining/benchmarks/submission.html'];assert not missing,(path,missing)
    if path in submenu_paths:check_submenus(page,js,width,path)
    if path not in ['/','/explorer/']:
     assert page.evaluate('document.querySelector(".site-header").getBoundingClientRect().bottom <= document.querySelector("main").getBoundingClientRect().top+1'),(path,width,js)
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),(path,width,js)
    page.close()
   print(f'{width}px JS={js}: all {len(routes)} pages passed navigation visibility/menu/logo/no overflow')
  browser.close()
finally:server.terminate();server.wait(timeout=5)
