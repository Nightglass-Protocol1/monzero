"""Shared navigation acceptance; external data requests are blocked."""
import importlib.util, socket, subprocess, time, shutil
from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('nav',root/'utils/website/sync_navigation.py');nav=importlib.util.module_from_spec(spec);spec.loader.exec_module(nav)
routes=['/','/explorer/','/stats/','/wallets/','/app/','/founder/','/fund/','/roadmap/','/security/','/mining/calculator/','/mining/dashboard/','/mining/benchmarks/']
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
  for js,width in [(True,1440),(True,390),(False,390)]:
   for path in routes:
    page=browser.new_page(java_script_enabled=js,viewport={'width':width,'height':1000})
    def intercept(r):
     if '.php' in r.request.url or not r.request.url.startswith(f'http://127.0.0.1:{port}/'):r.fulfill(status=503,json={'error':'fixture offline'})
     else:r.continue_()
    page.route('**/*',intercept);page.goto(f'http://127.0.0.1:{port}'+path)
    menu=page.locator('.site-header .menu-toggle');links=page.locator('#site-nav a')
    assert links.count()==len(nav.LINKS),path
    assert links.evaluate_all('(links)=>links.map(a=>a.getAttribute("href"))')==[x[0] for x in nav.LINKS],path
    assert page.locator('#site-nav [aria-current=page]').get_attribute('href')==path,path
    if js:
     page.wait_for_function("document.querySelector('.site-header').classList.contains('navigation-ready')")
     assert not page.locator('#site-nav').is_visible(),path
     menu.focus();page.keyboard.press('Enter');assert page.locator('#site-nav').is_visible(),path
     if path=='/':page.screenshot(path=f'/tmp/monzero-navigation-{width}.png')
     page.keyboard.press('Tab');assert links.first.evaluate('(e)=>e===document.activeElement'),(path,page.evaluate('document.activeElement.tagName'))
     page.keyboard.press('Escape');assert menu.evaluate('(e)=>e===document.activeElement'),path
     assert not page.locator('#site-nav').is_visible(),path
    else:
     assert page.locator('#site-nav').is_visible(),path
     assert not menu.is_visible(),path
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),(path,width,js)
    page.close()
   print(f'{width}px JS={js}: all {len(routes)} pages passed links/current page/menu/focus/no overflow')
  browser.close()
finally:server.terminate();server.wait(timeout=5)
