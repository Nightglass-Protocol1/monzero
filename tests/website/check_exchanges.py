"""Exchanges/markets acceptance; fixture records never touch catalog.json."""
import json,socket,subprocess,time,shutil
from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[2]
today=time.strftime('%Y-%m-%d',time.gmtime())
real=json.loads((root/'website/exchanges/catalog.json').read_text())
live=dict(id='fixture',exchange='<img src=x onerror=alert(1)>',status='live',note='Fixture venue.',updated_at=today,application_date=today,listing_fee=None,funding=None,announcements=[],pair='XMZ/USDT',trading_url='https://exchange.example/trade',deposits='enabled',withdrawals='disabled',trading='active',last_verified=today,verification_url='https://exchange.example/verify')
with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
server=subprocess.Popen(['php','-S',f'127.0.0.1:{port}','-t',str(root/'website')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
origin=f'http://127.0.0.1:{port}'
try:
 for _ in range(50):
  try:
   with socket.create_connection(('127.0.0.1',port),timeout=.2):break
  except OSError:time.sleep(.1)
 else:raise RuntimeError('Preview unavailable')
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True,executable_path=shutil.which('chromium'))
  for width in (390,1440):
   page=browser.new_page(viewport={'width':width,'height':900});errors=[];page.on('pageerror',lambda e:errors.append(str(e)));mode=['real']
   def respond(route):
    if mode[0]=='real':route.continue_()
    elif mode[0]=='outage':route.fulfill(status=503,body='down')
    elif mode[0]=='invalid':route.fulfill(content_type='application/json',body=json.dumps({**real,'records':[{**live,'verification_url':None}]}))
    else:route.fulfill(content_type='application/json',body=json.dumps({**real,'updated_at':today,'records':[live]+real['records']}))
   page.route('**/exchanges/catalog.json',respond);page.goto(origin+'/exchanges/')
   page.wait_for_function("document.getElementById('status').textContent.includes('verified venue')")
   assert 'not trading on any verified exchange' in page.locator('#venues').inner_text()
   tracker=page.locator('#tracker').inner_text()
   assert 'Biconomy' in tracker and 'Planned' in tracker and 'Not submitted' in tracker and 'Not published' in tracker and '$15,000' in tracker,tracker
   assert page.locator('#tracker a[href="/fund/"]').count()>=1
   mode[0]='fixture';page.click('#refresh');page.wait_for_function("document.querySelectorAll('#venues article').length===1")
   venue=page.locator('#venues').inner_text()
   assert '<img src=x' in venue and page.locator('#venues img').count()==0
   assert 'Disabled' in venue and page.locator('#venues a[href="https://exchange.example/trade"]').get_attribute('rel')=='noopener noreferrer'
   for m in ('invalid','outage'):
    mode[0]=m;page.click('#refresh');page.wait_for_function("document.getElementById('status').textContent.includes('unavailable')")
    assert page.locator('#venues article').count()==0 and page.locator('#tracker article').count()==0
   assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),width
   assert not errors,errors;page.close()
  page=browser.new_page();page.goto(origin+'/markets/');assert 'No verified market price' in page.inner_text('main')
  browser.close()
finally:server.terminate();server.wait(timeout=5)
print('Exchanges: real tracker, fixture venue, literal text, invalid/outage clearing, markets unavailable state passed')
