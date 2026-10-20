"""v1.0.0 upgrade: /api/v1/network/upgrade/ against a fixture node (before, at and after block 21,000,
node readiness), the /upgrade/ countdown page, and the banner on public pages (countdown, active
notice, gone a day after the fork, hidden for a day by "Hide", absent on /upgrade/ and /admin/)."""
import http.server,json,shutil,socket,subprocess,tempfile,threading,time,urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[2]
H=lambda n:f'{n:064x}'
state={'tip':13142,'voting':17}
class Node(http.server.BaseHTTPRequestHandler):
 def do_POST(self):
  req=json.loads(self.rfile.read(int(self.headers['Content-Length'])));m=req['method'];tip=state['tip']
  head=dict(height=tip,hash=H(tip+1),prev_hash=H(tip),timestamp=int(time.time())-60,difficulty=40000000,reward=18600000000000,num_txes=0,block_size=300,block_weight=300,depth=0,orphan_status=False,major_version=16,minor_version=17,nonce=1,miner_tx_hash=H(7))
  r={'get_info':dict(status='OK',height=tip+1,difficulty=40000000,nettype='mainnet',synchronized=True,top_block_hash=H(tip+1),tx_pool_size=0),
     'get_last_block_header':dict(status='OK',block_header=head),
     'hard_fork_info':dict(status='OK',version=16,voting=state['voting'],earliest_height=21000,enabled=False)}.get(m)
  b=json.dumps({'jsonrpc':'2.0','id':req['id'],'result':r}).encode();self.send_response(200);self.end_headers();self.wfile.write(b)
 def log_message(self,*a):pass
node=http.server.ThreadingHTTPServer(('127.0.0.1',0),Node);threading.Thread(target=node.serve_forever,daemon=True).start()
with tempfile.TemporaryDirectory() as tmp:
 site=Path(tmp)/'site';shutil.copytree(root/'website',site,ignore=shutil.ignore_patterns('downloads','data'))
 lib=site/'api/v1/lib.php';lib.write_text(lib.read_text().replace('http://node.monzero.org:6175',f'http://127.0.0.1:{node.server_port}'))
 with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
 base=f'http://127.0.0.1:{port}';(Path(tmp)/'state').mkdir()
 server=subprocess.Popen(['php','-S',f'127.0.0.1:{port}','-t',str(site)],env={'TMPDIR':str(Path(tmp)/'state'),'PATH':'/usr/bin:/bin'},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 def api():
  for f in (Path(tmp)/'state').rglob('cache-*.json'):f.unlink()  # skip the 15/60-second caches between scenarios
  return json.loads(urllib.request.urlopen(base+'/api/v1/network/upgrade/',timeout=15).read())['data']
 try:
  for _ in range(100):
   try:
    with socket.create_connection(('127.0.0.1',port),timeout=.2):break
   except OSError:time.sleep(.1)
  d=api();assert d['height']==13143 and d['blocks_left']==7857 and not d['active'] and d['public_node_ready'] is True,d
  assert abs(d['estimated_at']-(int(time.time())-60+7857*120))<5
  state['voting']=16;assert api()['public_node_ready'] is False;state['voting']=17
  with sync_playwright() as p:
   browser=p.chromium.launch(headless=True,executable_path=shutil.which('chromium'))
   def page(path,width=1440):
    ctx=browser.new_context(viewport={'width':width,'height':900});pg=ctx.new_page();errors=[];pg.on('pageerror',lambda e:errors.append(str(e)))
    pg.route('**/news/data/*',lambda r:r.fulfill(status=404,body=''))
    for f in (Path(tmp)/'state').rglob('cache-*.json'):f.unlink()
    pg.goto(base+path);pg.wait_for_timeout(1200);return ctx,pg,errors
   ctx,pg,errors=page('/network/nodes/')
   b=pg.locator('.upgrade-banner');assert b.count()==1 and 'Network upgrade in 7,857 blocks' in b.inner_text() and 'Pool miners need to do nothing' in b.inner_text(),b.inner_text() if b.count() else None
   assert b.locator('a').get_attribute('href')=='/upgrade/'
   assert pg.evaluate("document.querySelector('.upgrade-banner').getBoundingClientRect().bottom <= document.querySelector('.site-header').getBoundingClientRect().top+1")
   pg.locator('.upgrade-hide').click();assert pg.locator('.upgrade-banner').count()==0
   pg.reload();pg.wait_for_timeout(1000);assert pg.locator('.upgrade-banner').count()==0  # hidden for a day
   assert not errors,errors;ctx.close()
   ctx,pg,errors=page('/',width=390);assert pg.locator('.upgrade-banner').is_visible() and pg.evaluate('document.documentElement.scrollWidth <= innerWidth') and not errors;ctx.close()
   for path in ['/upgrade/','/admin/']:
    ctx,pg,errors=page(path);assert pg.locator('.upgrade-banner').count()==0,path;ctx.close()
   ctx,pg,errors=page('/upgrade/')
   assert '7,857 blocks to go' in pg.locator('#count').inner_text() and 'ready for the upgrade' in pg.locator('#node-ready').inner_text() and not errors;ctx.close()
   # At the fork: active notice. A day later: nothing.
   state['tip']=21050
   assert api()['active'] is True and api()['blocks_left']==0 and api()['estimated_at'] is None
   ctx,pg,errors=page('/stats/');assert 'upgrade is active' in pg.locator('.upgrade-banner').inner_text() and 'active' in pg.locator('.upgrade-banner').get_attribute('class');ctx.close()
   ctx,pg,errors=page('/upgrade/');assert 'The upgrade is active' in pg.locator('#count').inner_text();ctx.close()
   state['tip']=21800
   ctx,pg,errors=page('/stats/');assert pg.locator('.upgrade-banner').count()==0;ctx.close()
   browser.close()
 finally:server.terminate();server.wait(timeout=5);node.shutdown()
print('Upgrade: API before/at/after the fork and node readiness, /upgrade/ countdown, banner countdown/active/gone, hide for a day, not on /upgrade/ or /admin/ passed')
