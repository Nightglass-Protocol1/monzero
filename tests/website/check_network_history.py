"""Isolated network-history browser acceptance with actual collector exports."""
from playwright.sync_api import sync_playwright
import importlib.util,json,socket,subprocess,tempfile,time
from pathlib import Path
root=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('history',root/'utils/website/network_history.py')
history=importlib.util.module_from_spec(spec);spec.loader.exec_module(history)
with tempfile.TemporaryDirectory(prefix='monzero-history-browser-') as directory:
 db=history.connect(Path(directory)/'private/archive.sqlite')
 now=int(time.time());first=now-4000;last=now-500
 with db:
  for timestamp,height in [(first,30),(last,29)]:
   db.execute('INSERT INTO observations VALUES (?,?,?,?,?,?,?)',(timestamp,height,timestamp-200,'1200',1,'preview','fixture'))
 exports={name:history.export(db,name,now) for name in history.RANGES};db.close()
 with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
 server=subprocess.Popen(['php','-S',f'127.0.0.1:{port}','-t',str(root/'website')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 try:
  for _ in range(50):
   try:
    with socket.create_connection(('127.0.0.1',port),timeout=.2):break
   except OSError:time.sleep(.1)
  else:raise RuntimeError('Preview did not start')
  with sync_playwright() as p:
   browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
   for width in (390,1440):
    page=browser.new_page(viewport={'width':width,'height':900});errors=[]
    page.on('pageerror',lambda error:errors.append(str(error)))
    mode=['normal'];held=[]
    def respond(route):
     name=route.request.url.rsplit('/',1)[-1].split('.')[0]
     if mode[0]=='hold':held.append(route);return
     data=exports[name]
     if mode[0]=='oversized':route.fulfill(content_type='application/json',body=' '*1048577);return
     if mode[0]=='outage':route.fulfill(status=503,body='Unavailable');return
     if mode[0]=='malformed':data={**data,'archive_last_observed_at':now}
     if mode[0]=='empty':data={**data,'archive_samples':0,'archive_first_observed_at':None,'archive_last_observed_at':None,'sources':[],'points':[]}
     route.fulfill(content_type='application/json',body=json.dumps(data))
    block_mode=['normal']
    block_fixture={'schema':'monzero-chain-charts-v2','network':'mainnet','target_seconds':120,'generated_at':now,'height':4,'synchronized':True,'blocks':[{'height':i+1,'timestamp':now-240+i*120,'difficulty':1200,'transactions':0} for i in range(3)]}
    def block_response(route):
     if block_mode[0]=='outage':route.fulfill(status=503,body='Unavailable');return
     route.fulfill(content_type='application/json',body=json.dumps(block_fixture))
    page.route('**/stats/api.php',block_response)
    page.route('**/network/data/*.json',respond)
    page.goto(f'http://127.0.0.1:{port}/network/')
    page.wait_for_function("document.getElementById('block-summary').textContent.includes('30 blocks/hour')")
    assert page.locator('#block-distribution tbody tr').count()==5
    assert page.locator('#block-distribution svg rect').count()==5
    assert page.locator('#block-distribution svg rect').nth(2).get_attribute('width')=='370'
    block_fixture['synchronized']=False;block_fixture['blocks'][-1]['timestamp']=now+120
    page.click('#refresh-blocks')
    page.wait_for_function("document.getElementById('block-summary').textContent.includes('Syncing node')")
    assert 'ahead of observation time' in page.locator('#block-summary').inner_text()
    block_fixture['synchronized']=True;block_fixture['blocks'][-1]['timestamp']=now
    block_mode[0]='outage';page.click('#refresh-blocks')
    page.wait_for_function("document.getElementById('block-status').textContent.includes('unavailable')")
    assert page.locator('#block-summary').inner_text()==''
    block_mode[0]='normal';page.click('#refresh-blocks')
    page.wait_for_function("document.getElementById('block-summary').textContent.includes('30 blocks/hour')")
    for name in history.RANGES:
     page.select_option('#range',name)
     page.wait_for_function("document.getElementById('status').textContent.includes('Historical data')")
     expected=len(exports[name]['points'])
     assert page.locator('#rows tr').count()==expected
     assert page.locator('svg circle').count()==expected*2
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    assert page.evaluate('document.querySelector("header nav").getBoundingClientRect().bottom <= document.querySelector("main").getBoundingClientRect().top')
    assert page.evaluate('document.querySelector("header").getBoundingClientRect().bottom <= document.querySelector("main").getBoundingClientRect().top')
    # Real exporter fixtures test ranges independently of local runtime archives.
    page.select_option('#range','24h')
    page.wait_for_function("document.querySelectorAll('#rows tr').length === 2")
    for state in ('malformed','outage','oversized','empty'):
     mode[0]=state;page.click('#refresh')
     expected='No observations' if state=='empty' else 'unavailable'
     page.wait_for_function('(expected)=>document.getElementById("status").textContent.includes(expected)',arg=expected)
     assert page.locator('#results').is_hidden()
    mode[0]='normal';page.click('#refresh')
    page.wait_for_function("document.getElementById('status').textContent.includes('Historical data')")
    # A pending request must not replace a subsequently selected range.
    mode[0]='hold';page.select_option('#range','7d')
    page.wait_for_timeout(100)
    assert held
    mode[0]='normal';page.select_option('#range','all')
    page.wait_for_function("document.getElementById('status').textContent.includes('Historical data')")
    assert page.locator('#range').input_value()=='all'
    try:held.pop().fulfill(content_type='application/json',body=json.dumps(exports['7d']))
    except Exception:pass  # Browser may have already cancelled the old route.
    assert f"Bucket width: {exports['all']['bucket_seconds']} seconds" in page.locator('#coverage').inner_text()
    # Advance browser timers rather than waiting ten seconds for the timeout.
    page.clock.install()
    mode[0]='hold';page.click('#refresh');page.wait_for_timeout(100)
    page.clock.fast_forward(10001)
    page.wait_for_function("document.getElementById('status').textContent.includes('unavailable')")
    assert page.locator('#results').is_hidden()
    for route in held:
     try:route.abort()
     except Exception:pass
    mode[0]='normal';page.click('#refresh')
    page.wait_for_function("document.getElementById('status').textContent.includes('Historical data')")
    assert not errors,errors
    page.close()
   page=browser.new_page(java_script_enabled=False)
   page.goto(f'http://127.0.0.1:{port}/network/')
   assert page.locator('#range').is_disabled()
   assert 'JavaScript must be enabled' in page.locator('#status').inner_text()
   browser.close()
 finally:
  server.terminate()
  try:server.wait(timeout=5)
  except subprocess.TimeoutExpired:server.kill();server.wait(timeout=5)
print('Network history: exporter fixtures, six ranges, mobile/desktop, malformed/empty/outage recovery, no-JS passed')
