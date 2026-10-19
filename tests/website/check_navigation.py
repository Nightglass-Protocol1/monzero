"""Shared navigation acceptance; external data requests are blocked."""
import importlib.util, socket, subprocess, time, shutil
from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[2]
routes=['/developers/api/','/ecosystem/','/exchanges/','/markets/','/payments/request/','/developers/payments/','/developers/','/community/bounties/','/community/','/network/','/','/explorer/','/stats/','/wallets/','/app/','/founder/','/fund/','/roadmap/','/security/','/mining/calculator/','/mining/dashboard/','/mining/benchmarks/']
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
    menu=page.locator('.site-header .menu-toggle');links=page.locator('.site-header nav a')
    assert links.count()>0,path
    if js and menu.count() and menu.is_visible():
     menu.click();assert page.locator('#site-nav').is_visible(),path
     page.keyboard.press('Escape');assert not page.locator('#site-nav').is_visible(),path
    if width==1440:
     assert page.locator('.site-header nav').is_visible(),path
    if path.startswith('/mining/'):
     assert page.locator('.site-header nav').is_visible(),path
     assert page.locator('.brand-coin').evaluate('(img)=>img.complete && img.naturalWidth > 0'),path
    if path in ['/developers/api/','/ecosystem/','/exchanges/','/markets/','/developers/payments/','/developers/','/community/bounties/','/community/','/network/']:
     assert page.locator('.site-header nav').is_visible(),path
     assert page.locator('.brand img').evaluate('(img)=>img.complete && img.naturalWidth > 0'),path
     assert page.evaluate('document.querySelector("header nav").getBoundingClientRect().bottom <= document.querySelector("main").getBoundingClientRect().top'),(path,width,js)
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),(path,width,js)
    page.close()
   print(f'{width}px JS={js}: all {len(routes)} pages passed navigation visibility/menu/logo/no overflow')
  browser.close()
finally:server.terminate();server.wait(timeout=5)
