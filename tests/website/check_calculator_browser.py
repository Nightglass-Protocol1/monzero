"""Synthetic browser fixtures only; no chain processes, builds or mining."""
import subprocess, time, shutil, socket
from pathlib import Path
from playwright.sync_api import sync_playwright
root=str(Path(__file__).resolve().parents[2] / 'website')
with socket.socket() as reservation:
 reservation.bind(('127.0.0.1',0)); port=reservation.getsockname()[1]
server=subprocess.Popen(['php','-S',f'127.0.0.1:{port}','-t',root],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
try:
 for attempt in range(50):
  try:
   with socket.create_connection(('127.0.0.1',port),timeout=.2):break
  except OSError:time.sleep(.1)
 else:raise RuntimeError('PHP preview did not start')
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True,executable_path=shutil.which('chromium'))
  url=f'http://127.0.0.1:{port}/mining/calculator/'
  for width in (1440,390):
   page=browser.new_page(viewport={'width':width,'height':1000},reduced_motion='reduce')
   errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
   info={'status':'OK','nettype':'mainnet','synchronized':True,'height':100,'target':120,
     'difficulty':3600000,'difficulty_top64':0,'tip_height':99,'tip_reward_atomic':200000000000,
     'tip_timestamp':int(time.time()),'tip_fresh':True}
   state={'data':info,'status':200}
   page.route('**/api/node-info/index.php',lambda route:route.fulfill(status=state['status'],json=state['data']))
   page.goto(url)
   page.wait_for_function("document.querySelector('#results').children.length === 12")
   assert page.locator('#results dd').first.inner_text()=='2'
   assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), 'horizontal overflow'
   page.locator('[name=hashrate]').fill('0.00000001');page.locator('button[type=submit]').click()
   assert page.locator('#results dd').first.inner_text()!='0', 'small reward rounded to zero'
   page.locator('[name=hashrate]').fill('0');assert page.locator('#results dd').count()==0
   page.locator('button[type=submit]').click();assert page.locator('#results dd').first.inner_text()=='0'
   for patch in ({'nettype':'testnet'},{'synchronized':False},{'tip_height':98},{'tip_fresh':False},
                 {'tip_reward_atomic':9007199254740992},{'difficulty_top64':1},{'difficulty':None}):
    state['data']={**info,**patch};page.locator('#refresh').click()
    page.wait_for_function("document.querySelector('#network-status').textContent.includes('unavailable') && !document.querySelector('#refresh').disabled")
    assert page.locator('#results dd').count()==0,patch
   state['data']=info;page.locator('#refresh').click()
   page.wait_for_function("document.querySelector('#results').children.length === 12")
   page.evaluate("window.originalNow=Date.now; Date.now=()=>window.originalNow()+310000")
   page.locator('button[type=submit]').click();assert page.locator('#results dd').count()==0
   page.evaluate("Date.now=window.originalNow")
   page.locator('#refresh').click();page.wait_for_function("document.querySelector('#results').children.length === 12")
   page.clock.install();page.clock.fast_forward(310000)
   page.wait_for_function("document.querySelector('#result-status').textContent === 'Estimate expired.'")
   assert page.locator('#results dd').count()==0
   state['status']=502;page.locator('#refresh').click()
   page.wait_for_function("document.querySelector('#network-status').textContent.includes('unavailable')")
   assert not errors,errors
   print(f'{width}px: estimates, small values, invalid observations, expiry, outage and layout passed')
   page.close()
  page=browser.new_page(java_script_enabled=False)
  page.goto(url)
  assert page.locator('button[type=submit]').is_disabled()
  assert page.locator('[name=hashrate]').is_disabled()
  assert page.locator('noscript').is_visible()
  assert '?' not in page.url
  print('No-JavaScript form is disabled; inputs cannot be submitted')
  browser.close()
finally:
 server.terminate();server.wait(timeout=5)
