import json, subprocess, time, tempfile, shutil, socket
from pathlib import Path
from playwright.sync_api import sync_playwright
root=str(Path(__file__).resolve().parents[2] / 'website')
artifacts=Path(tempfile.mkdtemp(prefix='monzero-calculator-check-'))
with socket.socket() as reservation:
 reservation.bind(('127.0.0.1',0)); port=reservation.getsockname()[1]
server=subprocess.Popen(['php','-S',f'127.0.0.1:{port}','-t',root],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
try:
 time.sleep(.5)
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True,executable_path=shutil.which("chromium"))
  for width in (1440,390):
   page=browser.new_page(viewport={'width':width,'height':1000},reduced_motion='reduce')
   errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
   page.route('**/explorer/api.php',lambda route:route.fulfill(json={'info':{'status':'OK','nettype':'mainnet','synchronized':True,'height':100,'target':120},'headers':[{'height':99,'difficulty':3600000,'reward':200000000000,'timestamp':int(time.time())}]}))
   page.goto(f'http://127.0.0.1:{port}/mining/calculator/')
   page.wait_for_function("document.querySelector('#results').children.length === 12")
   assert page.locator('#results dd').first.inner_text()=='2'
   assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), 'horizontal overflow'
   page.locator('[name=hashrate]').fill('0');assert page.locator('#results dd').count()==0
   page.locator('button[type=submit]').click();assert page.locator('#results dd').first.inner_text()=='0'
   page.screenshot(path=str(artifacts/f'calculator-fixture-{width}.png'),full_page=True)
   page.unroute('**/explorer/api.php')
   page.route('**/explorer/api.php',lambda route:route.fulfill(status=502,json={'error':'fixture outage'}))
   page.locator('#refresh').click();page.wait_for_function("document.querySelector('#network-status').textContent.includes('unavailable')")
   assert page.locator('#results dd').count()==0
   assert not errors,errors
   print(f'{width}px: results, input invalidation, zero hashrate, no overflow, outage clearing and JS errors checked')
   page.close()
  browser.close()
finally:
 server.terminate();server.wait(timeout=5)
