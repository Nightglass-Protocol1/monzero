"""Homepage live tiles: node census, faucet (open with days funded, paused) and service status, each
failing on its own; external requests blocked."""
import json,shutil,socket,subprocess,time
from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[2]
with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
server=subprocess.Popen(['php','-S',f'127.0.0.1:{port}','-t',str(root/'website')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
nodes={'schema':'monzero-api-v1','data':{'stale':False,'totals':{'observed':7,'reachable':2,'connected':7},'countries':{'US':{},'GB':{},'ZZ':{}}},'observed_at':1}
status={'schema':'monzero-status-v1','evaluated_at':1,'overall':'warn','checks':[{'id':'faucet','label':'Faucet','state':'ok','at':1,'detail':'x','days_left':5.9},{'id':'pool','label':'Mining pool','state':'warn','at':1,'detail':'x'}]}
try:
 for _ in range(50):
  try:
   with socket.create_connection(('127.0.0.1',port),timeout=.2):break
  except OSError:time.sleep(.1)
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True,executable_path=shutil.which('chromium'))
  def open_home(faucet,stat=status,census=nodes,width=1440):
   page=browser.new_page(viewport={'width':width,'height':900});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
   def route(r):
    u=r.request.url
    if not u.startswith(f'http://127.0.0.1:{port}/'):return r.fulfill(status=503,body='')
    for path,body in [('/api/v1/network/nodes/',census),('/api/faucet/',faucet),('/api/status/',stat)]:
     if path in u:return r.fulfill(status=200 if body else 503,content_type='application/json',body=json.dumps(body or {}))
    if '.php' in u:return r.fulfill(status=503,body='{}')
    r.continue_()
   page.route('**/*',route);page.goto(f'http://127.0.0.1:{port}/');page.wait_for_function("document.getElementById('tile-status').textContent!=='—'||document.getElementById('tile-status-detail').textContent.includes('unavailable')")
   page.wait_for_timeout(300);return page,errors
  page,errors=open_home({'status':'open'})
  assert page.locator('#tile-nodes').inner_text()=='7' and page.locator('#tile-nodes-detail').inner_text()=='in 2 countries'
  assert page.locator('#tile-faucet').inner_text()=='Open' and 'about 5 days' in page.locator('#tile-faucet-detail').inner_text()
  assert page.locator('#tile-status').inner_text()=='1 needs attention' and page.locator('#tile-status').get_attribute('class')=='warn'
  assert page.locator('.live-tile').nth(0).get_attribute('href')=='network/nodes/' and not errors,errors;page.close()
  page,errors=open_home({'status':'paused'},stat=None,census=None,width=390)
  assert page.locator('#tile-faucet').inner_text()=='Paused' and 'unavailable' in page.locator('#tile-nodes-detail').inner_text() and 'unavailable' in page.locator('#tile-status-detail').inner_text()
  assert page.evaluate('document.documentElement.scrollWidth <= innerWidth') and not errors,errors;page.close()
  browser.close()
finally:server.terminate();server.wait(timeout=5)
print('Homepage tiles: census, faucet open/paused with days funded, status, independent failures, mobile layout passed')
