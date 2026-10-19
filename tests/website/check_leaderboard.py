"""Leaderboard acceptance with fixture reports; the real reporting service is never contacted."""
import json,socket,subprocess,time,shutil
from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[2]
now=int(time.time())
miners=[dict(name=f'Miner {i:08X}',hashrate=1000.0-i,blocks_found=i%4,active=True,last_seen=now-i) for i in range(60)]
miners[0]['name']='Miner 0000000A'
report=dict(status='OK',generated_at=now,active_miners=60,total_hashrate=0,total_blocks=0,miners=miners)
with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
server=subprocess.Popen(['php','-S',f'127.0.0.1:{port}','-t',str(root/'website')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
try:
 for _ in range(50):
  try:
   with socket.create_connection(('127.0.0.1',port),timeout=.2):break
  except OSError:time.sleep(.1)
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True,executable_path=shutil.which('chromium'))
  for width in (390,1440):
   page=browser.new_page(viewport={'width':width,'height':900});errors=[];page.on('pageerror',lambda e:errors.append(str(e)));mode=['ok']
   def respond(route):
    if mode[0]=='ok':route.fulfill(content_type='application/json',body=json.dumps(report))
    elif mode[0]=='empty':route.fulfill(content_type='application/json',body=json.dumps({**report,'miners':[]}))
    elif mode[0]=='bad':route.fulfill(content_type='application/json',body=json.dumps({**report,'miners':[{**miners[1],'name':'<b>FabcAddress</b>'}]}))
    else:route.fulfill(status=503,body=json.dumps({'status':'NOT_CONFIGURED'}))
   page.route('**/api/miner-stats/',respond);page.goto(f'http://127.0.0.1:{port}/mining/leaderboard/')
   page.wait_for_function("document.querySelectorAll('#by-hashrate tr').length===50")
   first=page.locator('#by-hashrate tr').first.inner_text();assert 'Miner 0000000A' in first and '1.00 KH/s' in first,first
   assert page.locator('#by-blocks tr').count()==45  # 15 of 60 report zero blocks
   assert '60 opted-in miners' in page.locator('#status').inner_text()
   for m,expect in [('empty','No opted-in miner'),('bad',None),('down',None)]:
    mode[0]=m;page.click('#refresh');page.wait_for_function("!document.getElementById('refresh').disabled")
    if expect:assert expect in page.locator('#by-hashrate').inner_text()
    else:assert 'unavailable' in page.locator('#status').inner_text() and page.locator('#by-hashrate tr').count()==0
   assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),width
   assert not errors,errors;page.close()
  browser.close()
finally:server.terminate();server.wait(timeout=5)
print('Leaderboard: rankings, 50-row cap, zero-block exclusion, empty/invalid/outage states passed')
