"""Ecosystem directory acceptance: real catalog, filters, third-party labelling, outage clearing."""
import json,socket,subprocess,time,shutil
from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[2]
real=json.loads((root/'website/ecosystem/catalog.json').read_text())
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
   page.route('**/ecosystem/catalog.json',lambda r:r.continue_() if mode[0]=='real' else r.fulfill(status=503,body='down'))
   page.goto(origin+'/ecosystem/');page.wait_for_function(f"document.querySelectorAll('#list article').length==={len(real['records'])}")
   page.select_option('#operator','third-party');third=page.locator('#list article')
   assert third.count()==sum(r['operator']=='third-party' for r in real['records'])
   for i in range(third.count()):
    assert 'Third-party service' in third.nth(i).inner_text() and third.nth(i).locator('a').get_attribute('rel')=='noopener noreferrer'
   page.select_option('#operator','');page.select_option('#category','Mining pools');assert 'Monzero Pool' in page.locator('#list').inner_text()
   page.select_option('#category','');page.fill('#search','zzzz-no-match');assert 'No entries match' in page.locator('#status').inner_text()
   page.fill('#search','')
   mode[0]='outage';page.click('#refresh');page.wait_for_function("document.getElementById('status').textContent.includes('unavailable')")
   assert page.locator('#list article').count()==0
   assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),width
   assert not errors,errors;page.close()
  browser.close()
finally:server.terminate();server.wait(timeout=5)
print('Ecosystem: real directory, filters, third-party labels, outage clearing passed')
