"""Browser asset-list certainty checks with isolated responses, no upstream RPC."""
import json,socket,subprocess,time
from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[2]
with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
server=subprocess.Popen(['php','-S',f'127.0.0.1:{port}','-t',str(root/'website')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
try:
 for _ in range(50):
  try:
   with socket.create_connection(('127.0.0.1',port),timeout=.2):break
  except OSError:time.sleep(.1)
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
  for width in (390,1440):
   page=browser.new_page(viewport={'width':width,'height':900});errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
   for code,payload,expected in [(502,{'error':'Node request failed'},'Asset registry unavailable'),(200,{'supported':False,'active':False,'total':0,'assets':[]},'Asset registry unavailable'),(200,{'supported':True,'active':False,'total':0,'assets':[]},'No registered assets')]:
    page.unroute('**/explorer/api.php')
    def respond(route):
     action=json.loads(route.request.post_data)['action']
     route.fulfill(status=code if action=='assets' else 502,content_type='application/json',body=json.dumps(payload if action=='assets' else {'error':'Fixture info unavailable'}))
    page.route('**/explorer/api.php',respond)
    page.goto('about:blank')
    page.goto(f'http://127.0.0.1:{port}/explorer/#/assets')
    page.wait_for_function('(text)=>document.getElementById("view").textContent.includes(text)',arg=expected)
    content=page.locator('#view').inner_text()
    if expected!='No registered assets':assert 'Nothing found' not in content and 'No registered assets' not in content and 'Assets are inactive' not in content
    else:assert 'Assets are inactive' in content
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
   assert not errors,errors
   page.close()
  browser.close()
finally:server.terminate();server.wait(timeout=5)
print('Explorer assets: desktop/mobile unavailable vs valid-empty states passed')
