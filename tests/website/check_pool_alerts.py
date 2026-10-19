"""Synthetic observations and notification permission; never queries a real pool."""
import shutil, time, socket, subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[2]/'website'
with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
server=subprocess.Popen(['php','-S',f'127.0.0.1:{port}','-t',str(root)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
try:
 for _ in range(50):
  try:
   with socket.create_connection(('127.0.0.1',port),timeout=.2):break
  except OSError:time.sleep(.1)
 else:raise RuntimeError('Preview unavailable')
 with sync_playwright() as p:
  b=p.chromium.launch(executable_path=shutil.which('chromium'),headless=True)
  for width in (390,1440):
   page=b.new_page(viewport={'width':width,'height':1000})
   page.add_init_script("""window.testTime=0; Object.defineProperty(performance,'now',{value:()=>window.testTime});
   window.permissionCalls=0;window.notifications=[];
   window.Notification=class {static permission='default';static async requestPermission(){window.permissionCalls++;this.permission='granted';return 'granted'} constructor(title,options){window.notifications.push({title,options})} close(){}};""")
   data={'schema':'monzero-pool-miner-view-v1','observed_at':1,'hashrate_hps':100,'active_workers':2,'workers':[],'payments':[]}
   errors=[];calls=[];held=[];mode={'hold':False,'status':200}
   page.on('pageerror',lambda e:errors.append(str(e)))
   def route(r):
    calls.append(r.request.post_data_json)
    if mode['hold']:held.append(r)
    else:r.fulfill(status=mode['status'],json=data)
   page.route('**/dashboard/api.php',route)
   page.goto(f'http://127.0.0.1:{port}/mining/dashboard/')
   assert page.locator('#alert-state').inner_text()=='Alerts are off.'
   assert page.evaluate('permissionCalls')==0
   page.locator('#address').fill('F'+'1'*94)
   def lookup():
    page.locator('#lookup button[type=submit]').click();page.wait_for_function("document.querySelector('#status').textContent.startsWith('Pool response retrieved')")
   lookup();page.locator('#alert-settings button[type=submit]').click()
   assert len(calls)==1
   assert page.evaluate('permissionCalls')==0
   page.locator('#desktop-alerts').click();page.wait_for_function('permissionCalls===1')
   data['observed_at']=2;lookup()
   for t in (60000,120000):
    page.evaluate('(t)=>window.testTime=t',t);data.update(observed_at=data['observed_at']+1,hashrate_hps=10,active_workers=0);lookup()
   assert page.locator('#alert-events li').count()==2
   assert len(page.evaluate('notifications'))==2
   assert ('F'+'1'*94) not in str(page.evaluate('notifications'))
   page.evaluate('window.testTime=180000');data['observed_at']+=1;lookup()
   assert page.locator('#alert-events li').count()==2
   assert page.evaluate('localStorage.length+sessionStorage.length')==0
   assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
   page.locator('#address').fill('F'+'2'*94)
   assert page.locator('#alert-events li').count()==0
   assert page.locator('#alert-state').inner_text()=='Alerts are off.'
   assert page.locator('#desktop-alerts').is_disabled()
   lookup();page.locator('#alert-settings button[type=submit]').click()
   page.evaluate("() => {Notification.requestPermission=()=>new Promise(resolve=>window.resolvePermission=resolve);}")
   page.locator('#desktop-alerts').click();page.locator('#stop-alerts').click()
   page.evaluate("window.resolvePermission('granted')")
   assert page.locator('#notification-state').inner_text()=='Browser notifications are off.'
   page.locator('#alert-settings button[type=submit]').click()
   page.evaluate("() => {Notification.requestPermission=async()=> 'denied';}")
   page.locator('#desktop-alerts').click()
   page.wait_for_function("document.querySelector('#notification-state').textContent.includes('not granted')")
   assert page.locator('#alert-state').inner_text().startswith('Session alerts enabled')
   mode['hold']=True;page.locator('#lookup button[type=submit]').click()
   page.wait_for_function("document.querySelector('#status').textContent.includes('Loading')")
   page.locator('#alert-settings button[type=submit]').click()
   assert len(held)==1
   held.pop().fulfill(json=data);mode['hold']=False
   page.wait_for_function("document.querySelector('#status').textContent.startsWith('Pool response retrieved')")
   assert 'Waiting for new observations' in page.locator('#alert-state').inner_text()
   mode['status']=502
   for t in (240000,300000):
    page.evaluate('(t)=>window.testTime=t',t);page.locator('#lookup button[type=submit]').click()
    page.wait_for_function("document.querySelector('#status').textContent.includes('unavailable')")
   assert page.locator('#alert-events li').count()==1
   assert 'lookups failed' in page.locator('#alert-events').inner_text()
   assert len(calls)==9
   page.locator('#clear').click()
   assert page.locator('#alert-events li').count()==0
   assert page.locator('#alert-state').inner_text()=='Alerts are off.'
   mode['status']=200
   data.update(observed_at=100,hashrate_hps=100,active_workers=2,payments=[{'txid':'a'*64,'timestamp':1,'amount_atomic':'100'}])
   page.locator('#address').fill('F'+'3'*94);lookup()
   assert not page.locator('#alert-payments').is_checked()
   page.locator('#alert-payments').check();page.locator('#alert-settings button[type=submit]').click()
   page.evaluate("() => {Notification.requestPermission=async()=> {Notification.permission='granted';return 'granted';};}")
   page.locator('#desktop-alerts').click()
   page.wait_for_function("document.querySelector('#notification-state').textContent.includes('enabled for this visit')")
   page.evaluate('window.testTime=360000');data['observed_at']+=1;lookup()
   assert page.locator('#alert-events li').count()==0
   assert 'Existing history was excluded' in page.locator('#payment-alert-state').inner_text()
   data['payments'].insert(0,{'txid':'b'*64,'timestamp':2,'amount_atomic':'200'})
   page.evaluate('window.testTime=420000');data['observed_at']+=1;lookup()
   assert page.locator('#alert-events li').count()==1
   assert 'confirmations are not verified' in page.locator('#alert-events').inner_text()
   assert page.evaluate("notifications.at(-1).options.tag")=='monzero-session-payments'
   assert ('b'*64) not in str(page.evaluate('notifications'))
   data['payments'].extend([{'txid':c*64,'timestamp':3,'amount_atomic':'300'} for c in ['c','d']])
   page.evaluate('window.testTime=480000');data['observed_at']+=1;lookup()
   assert page.locator('#alert-events li').count()==1
   page.evaluate('window.testTime=1080000');data['observed_at']+=1;lookup()
   assert page.locator('#alert-events li').count()==2
   assert '2 payment transaction' in page.locator('#alert-events li').first.inner_text()
   assert len(calls)==14
   assert page.evaluate('localStorage.length+sessionStorage.length')==0
   page.locator('#clear').click();assert page.locator('#payment-alert-state').inner_text()=='Payment alerts are off.'
   assert not page.locator('#alert-payments').is_checked()
   assert not errors,errors
   print(f'{width}px session-alert opt-in, thresholds, deduplication, privacy and clearing passed')
   page.close()
  b.close()
finally:server.terminate();server.wait(timeout=5)
