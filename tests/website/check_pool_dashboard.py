import json, socket, subprocess, time, shutil
from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[2]/'website'
with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
server=subprocess.Popen(['php','-S',f'127.0.0.1:{port}','-t',str(root)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
try:
 for _ in range(50):
  try:
   with socket.create_connection(('127.0.0.1',port),timeout=.2):break
  except OSError:time.sleep(.1)
 else:raise RuntimeError('Preview unavailable')
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True,executable_path=shutil.which('chromium'))
  for width in (1440,390):
   context=browser.new_context(viewport={'width':width,'height':1000})
   page=context.new_page();calls=[];errors=[]
   page.on('pageerror',lambda error:errors.append(str(error)))
   state={'status':200}
   fixture={'schema':'monzero-pool-miner-view-v1','observed_at':int(time.time()),'hashrate_hps':1000,'active_workers':1,'pool_share_percent':50,'pending_atomic':'9007199254740993','paid_atomic':'0','workers':[{'name':'Worker connection 1','label_id':'b'*64}],'payments':[{'txid':'a'*64,'timestamp':100,'amount_atomic':'123456789012'}]}
   def route(r):
    calls.append(r.request.post_data_json)
    r.fulfill(status=state['status'],json=fixture if state['status']==200 else {'error':'fixture outage'})
   page.route('**/dashboard/api.php',route)
   page.goto(f'http://127.0.0.1:{port}/mining/dashboard/')
   assert not calls
   page.locator('#address').fill('F'+'1'*94);page.locator('#lookup button[type=submit]').click()
   page.wait_for_function("document.querySelector('#results').children.length===10")
   assert calls==[{'address':'F'+'1'*94}]
   assert '90071.99254740993 XMZ' in page.locator('#results').inner_text()
   assert page.locator('#payments a').get_attribute('href')=='../../explorer/#/tx/'+'a'*64
   assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
   label=page.locator('#workers input');label.fill('Desk CPU');page.locator('#workers button').click()
   assert page.evaluate('localStorage.length')==0
   page.locator('#save-labels').check()
   saved=page.evaluate('localStorage.getItem("monzero-pool-worker-labels-v1")')
   assert json.loads(saved)=={'b'*64:'Desk CPU'} and ('F'+'1'*94) not in saved
   other=page.context.new_page();other.goto(f'http://127.0.0.1:{port}/mining/dashboard/')
   assert not other.locator('#save-labels').is_checked()
   other.locator('#forget-labels').click()
   page.wait_for_function("!document.querySelector('#save-labels').checked && document.querySelector('#label-status').textContent.includes('another tab')")
   page.locator('#workers input').fill('Desk CPU');page.locator('#workers button').click()
   assert page.evaluate('localStorage.length')==0
   other.close();page.locator('#save-labels').check()
   page.locator('#save-labels').uncheck();assert page.evaluate('localStorage.length')==0
   page.locator('#workers input').fill('Desk CPU');page.locator('#workers button').click();page.locator('#save-labels').check()
   page.locator('#forget-labels').click();assert page.evaluate('localStorage.length')==0
   assert page.locator('#workers input').input_value()==''
   page.evaluate("() => {window.originalStorageSet=Storage.prototype.setItem;Storage.prototype.setItem=()=>{throw new Error('fixture blocked storage')};}")
   page.locator('#save-labels').click();assert not page.locator('#save-labels').is_checked()
   assert 'could not be accessed' in page.locator('#label-status').inner_text()
   page.evaluate('() => {Storage.prototype.setItem=window.originalStorageSet;}')
   page.locator('#workers input').fill('Temporary label');page.locator('#workers button').click();page.locator('#save-labels').check()
   page.get_by_text('Manage saved labels, including disconnected workers',exact=True).click()
   page.locator('#saved-label-list button').click()
   assert page.locator('#workers input').input_value()==''
   assert json.loads(page.evaluate('localStorage.getItem("monzero-pool-worker-labels-v1")'))=={}
   page.evaluate("() => {window.originalStorageRemove=Storage.prototype.removeItem;Storage.prototype.removeItem=()=>{throw new Error('fixture blocked deletion')};}")
   page.locator('#forget-labels').click()
   assert 'could not be cleared' in page.locator('#label-status').inner_text()
   assert page.evaluate('localStorage.length')==1
   assert not page.locator('#save-labels').is_checked()
   page.evaluate('() => {Storage.prototype.removeItem=window.originalStorageRemove;}')
   page.locator('#forget-labels').click();assert page.evaluate('localStorage.length')==0
   assert not page.locator('#collect-history').is_checked()
   assert page.locator('#session-history svg').count()==0
   page.locator('#collect-history').check();assert len(calls)==1
   page.locator('#lookup button[type=submit]').click()
   page.wait_for_function("document.querySelector('#session-history tbody')?.children.length===1")
   fixture['observed_at']+=60;fixture['hashrate_hps']=1500
   page.locator('#lookup button[type=submit]').click()
   page.wait_for_function("document.querySelector('#session-history tbody')?.children.length===2")
   assert page.locator('#session-history svg').count()==2
   assert '90071.99254740993 XMZ' in page.locator('#session-history table').text_content()
   assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
   page.locator('#session-history').screenshot(path=f'/tmp/monzero-session-charts-{width}.png')
   page.locator('#collect-history').uncheck();assert page.locator('#session-history svg').count()==0
   page.locator('#collect-history').check();assert page.locator('#session-history svg').count()==0
   page.locator('#lookup button[type=submit]').click();page.wait_for_function("document.querySelector('#session-history tbody')?.children.length===1")
   page.locator('#address').fill('F'+'2'*94);assert page.locator('#session-history svg').count()==0
   state['status']=502;page.locator('#lookup button[type=submit]').click()
   page.wait_for_function("document.querySelector('#status').textContent.includes('unavailable')")
   assert page.locator('#results dd').count()==0
   assert 'Last lookup failed' in page.locator('#history-state').inner_text()
   page.locator('#clear').click();assert page.locator('#session-history svg').count()==0;assert not page.locator('#collect-history').is_checked();assert page.locator('#address').input_value()==''
   assert page.evaluate('localStorage.length')==0
   assert page.evaluate('sessionStorage.length')==0
   assert not page.context.cookies()
   assert not errors,errors
   print(f'{width}px: explicit lookup, opt-in labels, atomic precision, charts, outage and clearing passed')
   context.close()
  page=browser.new_page(java_script_enabled=False);page.goto(f'http://127.0.0.1:{port}/mining/dashboard/')
  assert page.locator('#address').is_disabled();assert page.locator('#lookup button[type=submit]').is_disabled()
  browser.close()
finally:server.terminate();server.wait(timeout=5)
