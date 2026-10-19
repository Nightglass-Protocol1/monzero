"""Payment request page acceptance: on-page QR decodes to the link, no network use, no-JS safe."""
import socket,subprocess,time,shutil,tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[2]
primary='FWPbFrwvRqpWTMDJAAeT3wAGsCUvERHyEAZJySDBDTKJJxr4q9gNStxSZghEAmtgvd49oySaDP9WGV1KVDeDXFBfM748KwK'
integrated='Fg6GGfmR37LWTMDJAAeT3wAGsCUvERHyEAZJySDBDTKJJxr4q9gNStxSZghEAmtgvd49oySaDP9WGV1KVDeDXFBfWmsEXGUWcB6U3NP9sa'
with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
server=subprocess.Popen(['php','-S',f'127.0.0.1:{port}','-t',str(root/'website')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
origin=f'http://127.0.0.1:{port}'
try:
 for _ in range(50):
  try:
   with socket.create_connection(('127.0.0.1',port),timeout=.2):break
  except OSError:time.sleep(.1)
 else:raise RuntimeError('Preview unavailable')
 with sync_playwright() as p, tempfile.TemporaryDirectory() as tmp:
  browser=p.chromium.launch(headless=True,executable_path=shutil.which('chromium'))
  for width in (390,1440):
   page=browser.new_page(viewport={'width':width,'height':1000},accept_downloads=True);errors=[];requests=[]
   page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:requests.append(r.url))
   page.goto(origin+'/payments/request/');page.wait_for_function("!document.getElementById('inputs').disabled")
   assert page.locator('#result').is_hidden()
   page.fill('#address',primary[:-1]+'L');assert 'checksum' in page.locator('#address-status').inner_text()
   assert page.locator('#result').is_hidden()
   page.fill('#address',primary);page.fill('#amount','1.5');page.fill('#name','Shop & co');page.fill('#description','Order #7 = ü?')
   expected=f'monzero:{primary}?tx_amount=1.50000000000&recipient_name=Shop%20%26%20co&tx_description=Order%20%237%20%3D%20%C3%BC%3F'
   assert page.input_value('#uri')==expected,page.input_value('#uri')
   assert 'Valid standard address' in page.locator('#address-status').inner_text()
   png=Path(tmp)/f'qr-{width}.png';page.locator('#qr').screenshot(path=str(png))
   decoded=subprocess.run(['zbarimg','-q','--raw','-Sbinary',str(png)],capture_output=True).stdout.decode()
   assert decoded==expected,(decoded,expected)
   with page.expect_download() as d:page.click('#download-png')
   saved=Path(tmp)/f'dl-{width}.png';d.value.save_as(saved)
   assert subprocess.run(['zbarimg','-q','--raw','-Sbinary',str(saved)],capture_output=True).stdout.decode()==expected
   with page.expect_download() as d:page.click('#download-svg')
   assert d.value.suggested_filename=='monzero-payment-request.svg'
   page.fill('#amount','1.000000000001');assert '11 decimal' in page.locator('#error').inner_text();assert page.locator('#result').is_hidden()
   page.fill('#amount','');page.fill('#name','');page.fill('#description','line')
   page.fill('#address',integrated);assert '0123456789abcdef' in page.locator('#summary').inner_text()
   assert page.input_value('#uri')==f'monzero:{integrated}?tx_description=line'
   page.fill('#description','x'*200);page.fill('#name','y'*200);assert page.locator('#result').is_visible()
   assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),width
   assert not errors,errors
   assert all(u.startswith(origin+'/') for u in requests),[u for u in requests if not u.startswith(origin)]
   assert not any('.php' in u for u in requests),requests
   page.close()
  page=browser.new_page(java_script_enabled=False);page.goto(origin+'/payments/request/')
  assert page.evaluate('document.getElementById("inputs").disabled')
  page.goto(origin+'/developers/payments/');assert page.locator('h1').inner_text()=='Accept XMZ with your own wallet'
  browser.close()
finally:server.terminate();server.wait(timeout=5)
print('Payment request: wallet-format links, scanned QR and PNG download match, validation, no network, no-JS disabled passed')
