"""Isolated bounty board acceptance; synthetic listings never touch catalog.json."""
import json,socket,subprocess,time
from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[2]
today=time.strftime('%Y-%m-%d',time.gmtime())
def item(i):
 return dict(id=f'fixture-{i}',title=f'Fixture task {i}',description='<img src=x onerror=alert(1)> is literal text.',category='Documentation',difficulty='beginner',acceptance_criteria=['Reproduce the documented steps.'],submission_instructions='Discuss before starting.\nThen submit a change.',discussion_url='https://example.test/discuss',status='open',review_status='awaiting-submission',updated_at=today,maintainer='Fixture maintainer',reviewed_by='Fixture reviewer',reward_currency='XMZ',reward_atomic='1',funding_status='proposed',funding_evidence_url=None,funding_checked_at=None,completion_evidence_url=None,completion_checked_at=None,payment_evidence_url=None,payment_checked_at=None)
records=[item(i) for i in range(25)]
records[1]['title']='x'*160
records[1]['acceptance_criteria']=['y'*1000]
records[0].update(category='Bug fixes',funding_status='funded',funding_evidence_url='https://example.test/funding',funding_checked_at=today)
records[2].update(status='completed',review_status='accepted',funding_status='paid',funding_evidence_url='https://example.test/fund-paid',funding_checked_at=today,completion_evidence_url='https://example.test/completion',completion_checked_at=today,payment_evidence_url='https://example.test/payment',payment_checked_at=today)
data=dict(schema='monzero-bounties-v1',updated_at=today,records=records)
with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
server=subprocess.Popen(['php','-S',f'127.0.0.1:{port}','-t',str(root/'website')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
try:
 for _ in range(50):
  try:
   with socket.create_connection(('127.0.0.1',port),timeout=.2):break
  except OSError:time.sleep(.1)
 else:raise RuntimeError('Preview unavailable')
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
  for width in (390,1440):
   page=browser.new_page(viewport={'width':width,'height':900});page.clock.install();errors=[];page.on('pageerror',lambda e:errors.append(str(e)));mode=['normal'];held=[]
   def respond(route):
    if mode[0]=='hold':held.append(route);return
    if mode[0]=='oversized':route.fulfill(content_type='application/json',body=' '*4194305);return
    if mode[0]=='outage':route.fulfill(status=503,body='Unavailable');return
    payload=data if mode[0]=='normal' else {**data,'records':[]} if mode[0]=='empty' else {**data,'records':[{**item(1),'funding_status':'funded'}]}
    route.fulfill(content_type='application/json',body=json.dumps(payload))
   page.route('**/bounties/catalog.json',respond);page.goto(f'http://127.0.0.1:{port}/community/bounties/')
   page.wait_for_function("document.querySelectorAll('#list article').length===20")
   assert page.locator('#list img').count()==0
   assert '0.00000000001 XMZ' in page.locator('#list article').first.inner_text()
   assert page.locator('#list a[href="https://example.test/funding"]').count()==1
   assert page.locator('#list a[href="https://example.test/completion"]').count()==1
   assert page.locator('#list a[href="https://example.test/payment"]').count()==1
   page.click('#more');assert page.locator('#list article').count()==25
   assert page.locator('#list article').nth(20).evaluate('(el)=>el===document.activeElement')
   assert page.locator('#more').is_hidden()
   page.select_option('#category','Bug fixes');assert page.locator('#list article').count()==1
   page.select_option('#funding','proposed');assert page.locator('#list article').count()==0
   assert 'No tasks match' in page.locator('#status').inner_text()
   page.select_option('#category','');page.select_option('#funding','');page.fill('#search','task 24');assert page.locator('#list article').count()==1
   page.select_option('#state','completed');assert page.locator('#list article').count()==0
   page.fill('#search','');page.select_option('#state','')
   for state in ('malformed','outage','oversized','empty'):
    mode[0]=state;page.click('#refresh');expected='No reviewed' if state=='empty' else 'unavailable'
    page.wait_for_function('(text)=>document.getElementById("status").textContent.includes(text)',arg=expected)
    assert page.locator('#list article').count()==0
   mode[0]='normal';page.click('#refresh');page.wait_for_function("document.querySelectorAll('#list article').length===20")
   # Refresh stays focusable throughout a pending request and timeout.
   mode[0]='hold';page.click('#refresh');page.wait_for_timeout(100)
   assert held
   assert page.locator('#refresh').evaluate('(el)=>el===document.activeElement')
   assert page.locator('#refresh').get_attribute('aria-disabled')=='true'
   page.clock.fast_forward(10001)
   page.wait_for_function("document.getElementById('status').textContent.includes('unavailable')")
   assert page.locator('#refresh').evaluate('(el)=>el===document.activeElement')
   for route in held:
    try:route.abort()
    except Exception:pass
   mode[0]='normal';page.click('#refresh');page.wait_for_function("document.querySelectorAll('#list article').length===20")
   assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
   assert page.evaluate('document.querySelector("header").getBoundingClientRect().bottom<=document.querySelector("main").getBoundingClientRect().top')
   assert not errors,errors
   page.close()
  page=browser.new_page(java_script_enabled=False);page.goto(f'http://127.0.0.1:{port}/community/bounties/');assert page.locator('#search').is_disabled();browser.close()
finally:
 server.terminate();server.wait(timeout=5)
print('Bounties: desktop/mobile filters, pagination, exact rewards, literal text, evidence, malformed/outage/empty recovery and no-JS passed')
