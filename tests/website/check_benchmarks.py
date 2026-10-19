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
   page=browser.new_page(viewport={'width':width,'height':1000});errors=[]
   page.on('pageerror',lambda error:errors.append(str(error)))
   fixture={'id':'fixture-a','manufacturer':'Fixture','model':'Synthetic A','cores':4,'threads':8,'hashrate_hps':2000,'power_watts':100,'power_basis':'wall','os':'Fixture OS','miner':'Fixture miner','miner_version':'1','methodology':'Synthetic browser fixture only','date':'2026-10-18','status':'community','source_url':'https://example.test/a','verified_by':None,'verification_url':None}
   catalog={'schema':'monzero-randomx-benchmarks-v1','updated_at':'2026-10-19','records':[]}
   page.route('**/catalog.json',lambda r:r.fulfill(json=catalog))
   url=f'http://127.0.0.1:{port}/mining/benchmarks/'
   page.goto(url);page.wait_for_function("document.querySelector('#status').textContent.includes('No sourced')")
   catalog['records']=[{**fixture,'id':'fixture-'+letter,'model':'Synthetic '+letter.upper(),'power_basis':'cpu-package' if letter=='b' else 'wall'} for letter in 'abcd']
   catalog['records'][3].update(status='verified',verified_by='Fixture reviewer',verification_url='https://example.test/reproduction')
   page.reload();page.wait_for_function("document.querySelectorAll('#records tr').length===4")
   assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
   page.locator('#records input').first.check()
   assert page.locator('#compare-fixture-a').evaluate('(e)=>e===document.activeElement')
   page.locator('#compare-fixture-b').check();page.locator('#compare-fixture-c').check()
   assert page.locator('#compare-fixture-d').is_disabled()
   page.locator('#compare-fixture-b').uncheck();page.locator('#compare-fixture-c').uncheck()
   assert page.locator('#compare-fixture-d').is_enabled()
   assert 'Synthetic A' in page.locator('#comparison').inner_text()
   page.locator('#query').fill('Synthetic B');assert page.locator('#records tr').count()==1
   assert 'Synthetic A' in page.locator('#comparison').inner_text(), 'Filtering lost selection'
   page.locator('#status-filter').select_option('verified');assert page.locator('#records tr').count()==0
   page.locator('#query').fill('');assert page.locator('#records tr').count()==1
   assert page.locator('#records a').count()==2
   assert 'Reproduction: Fixture Synthetic D' in page.locator('#records').inner_text()
   page.locator('#comparison button').click();assert page.locator('#comparison article').count()==0
   assert not errors,errors
   print(f'{width}px: empty catalog, filters, comparison retention/removal and layout passed')
   page.close()
  browser.close()
finally:server.terminate();server.wait(timeout=5)
