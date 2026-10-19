"""Read-only browser fixtures: no nodes, wallets, builds or mining are started."""
import json, shutil, socket, subprocess, time
from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[2]/'website'
with socket.socket() as s:
 s.bind(('127.0.0.1',0));port=s.getsockname()[1]
server=subprocess.Popen(['php','-S',f'127.0.0.1:{port}','-t',str(root)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
try:
 time.sleep(.4)
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True,executable_path=shutil.which('chromium'))
  for width in (1440,390):
   page=browser.new_page(viewport={'width':width,'height':1000});errors=[]
   page.on('pageerror',lambda e:errors.append(str(e)))
   state={'offline':False,'missing':False}
   info={'status':'OK','nettype':'mainnet','height':100,'target':120,'difficulty':3600000,'tip_age_seconds':12,'synchronized':True,'tip_fresh':True,'peer_ready':True,'connections_hidden':True,'restricted':True}
   def route(r):
    url=r.request.url
    if '/api/node-info/' in url:
     if state['offline']:r.fulfill(status=502,json={'error':'fixture outage'})
     else:r.fulfill(json={k:v for k,v in info.items() if not state['missing'] or k not in ('difficulty','target','tip_age_seconds')})
    elif '/explorer/api.php' in url:
     if state['offline']:r.fulfill(status=502,json={'error':'fixture outage'})
     else:r.fulfill(json={'info':info,'headers':[{'height':99,'reward':200000000000,'timestamp':int(time.time()),'num_txes':0}]})
    elif '/api/' in url:r.fulfill(status=503,json={'error':'not part of this fixture'})
    elif not url.startswith(f'http://127.0.0.1:{port}/'):r.abort()
    else:r.continue_()
   page.route('**/*',route)
   page.goto(f'http://127.0.0.1:{port}/')
   page.wait_for_function("document.querySelector('#metric-reward').textContent === '2 XMZ'")
   assert page.locator('#metric-target').inner_text()=='120 seconds'
   assert page.locator('#metric-connections').inner_text()=='Unavailable'
   assert page.locator('a[href="mining/calculator/"]').count()==1
   assert page.locator('a[href="https://t.me/MonzeroOfficial"]').count()==1
   assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'overflow'
   state['missing']=True;page.evaluate('updateNodeStatus()')
   page.wait_for_function("document.querySelector('#metric-target').textContent === 'Unavailable'")
   assert page.locator('#metric-network-hashrate').inner_text()=='Unavailable'
   assert 'unavailable' in page.locator('#metric-tip-age').inner_text()
   state['offline']=True;page.evaluate('updateNetwork()')
   page.wait_for_function("document.querySelector('#metric-reward').textContent === '—' && document.querySelector('#metric-height').textContent === '—'")
   assert page.locator('#chain-strip li').count()==0
   assert not errors,errors
   print(f'{width}px: observed fields, missing values, outage clearing, links and layout passed')
   page.close()
  browser.close()
finally:
 server.terminate();server.wait(timeout=5)
