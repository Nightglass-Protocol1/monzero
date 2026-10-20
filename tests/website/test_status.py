"""Service status: checks against fake node/pool, faucet worker heartbeat (ok, low funds, halted, silent),
census and history ages, signed node check-ins (signature, replay), alert emails on change only
(dedupe and recovery), the status_ping client and the /status/ page."""
import hashlib,hmac,http.server,json,os,secrets,shutil,socket,subprocess,sys,tempfile,threading,time
from pathlib import Path
import requests
root=Path(__file__).resolve().parents[2]

node={'height':13000,'tip_age':60,'sync':True}
class Node(http.server.BaseHTTPRequestHandler):
 def do_POST(self):
  m=json.loads(self.rfile.read(int(self.headers['Content-Length'])))['method']
  r={'height':node['height'],'synchronized':node['sync'],'nettype':'mainnet'} if m=='get_info' else {'block_header':{'height':node['height']-1,'timestamp':int(time.time())-node['tip_age']}}
  b=json.dumps({'jsonrpc':'2.0','id':0,'result':r}).encode();self.send_response(200);self.end_headers();self.wfile.write(b)
 def log_message(self,*a):pass
pool={'height':13000,'up':True}
class Pool(http.server.BaseHTTPRequestHandler):
 def do_GET(self):
  if not pool['up']:self.send_response(503);self.end_headers();return
  b=json.dumps({'network':{'height':pool['height']},'pool':{'miners':3}}).encode();self.send_response(200);self.end_headers();self.wfile.write(b)
 def log_message(self,*a):pass
def serve(h):
 s=http.server.ThreadingHTTPServer(('127.0.0.1',0),h);threading.Thread(target=s.serve_forever,daemon=True).start();return s
node_server,pool_server=serve(Node),serve(Pool)

with tempfile.TemporaryDirectory() as tmp:
 tmp=Path(tmp);private=tmp/'private';private.mkdir();data=tmp/'data';data.mkdir();mail=tmp/'mail.jsonl'
 secret=secrets.token_hex(32);worker_secret=secrets.token_hex(32)
 (private/'status-config.php').write_text(f"<?php return ['secret' => '{secret}', 'alert_to' => 'owner@example.org', 'node_rpc' => 'http://127.0.0.1:{node_server.server_port}', 'pool_url' => 'http://127.0.0.1:{pool_server.server_port}/api/stats'];\n")
 def faucet_config(enabled=True):(tmp/'faucet-config.php').write_text(f"<?php return ['enabled' => {'true' if enabled else 'false'}, 'amount_atomic' => '10000000000', 'daily_cap_atomic' => '500000000000', 'turnstile_site_key' => 'k', 'turnstile_secret' => 's', 'worker_secret' => '{worker_secret}', 'base_url' => 'http://127.0.0.1'];\n")
 faucet_config()
 now=int(time.time())
 (private/'node-census').mkdir();(private/'node-census/latest.json').write_text(json.dumps({'schema':'monzero-node-census-v1','observed_at':now-300,'window_seconds':86400,'totals':{'observed':7,'reachable':2,'connected':7},'countries':{},'geo_database':'x'}))
 (data/'24h.json').write_text(json.dumps({'generated_at':now-120}))
 with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
 base=f'http://127.0.0.1:{port}'
 env={**os.environ,'MONZERO_PRIVATE_DIR':str(private),'MONZERO_NODE_CENSUS_DIR':str(private/'node-census'),'MONZERO_NETWORK_DATA_DIR':str(data),
      'MONZERO_FAUCET_CONFIG':str(tmp/'faucet-config.php'),'MONZERO_FAUCET_DB':str(tmp/'faucet.sqlite'),'MONZERO_FAUCET_HEARTBEAT':str(private/'faucet-heartbeat.json'),
      'MONZERO_STATUS_MAIL_LOG':str(mail)}
 server=subprocess.Popen(['php','-d','opcache.enable=0','-S',f'127.0.0.1:{port}','-t',str(root/'website')],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 def mails():return [json.loads(l) for l in mail.read_text().splitlines()] if mail.exists() else []
 def signed(path,payload,key,prefix,nonce=None,ts=None):
  body=json.dumps(payload).encode();ts=str(ts or int(time.time()));nonce=nonce or secrets.token_hex(16)
  sig=hmac.new(key.encode(),f'{ts}\n{nonce}\n'.encode()+body,hashlib.sha256).hexdigest()
  return requests.post(base+path,data=body,headers={f'X-{prefix}-Timestamp':ts,f'X-{prefix}-Nonce':nonce,f'X-{prefix}-Signature':sig})
 def ping(n='eu',**kw):return signed('/api/status/',{'node':n},secret,'Status',**kw)
 def beat(balance='2999044290000',halted=None):
  p={'action':'heartbeat','balance_atomic':balance,'unlocked_atomic':balance,'need_atomic':'110000000000','payouts':True}
  if halted:p['halted']=halted
  return signed('/api/faucet/worker/',p,worker_secret,'Faucet')
 def states():
  r=ping();assert r.status_code==200,r.text
  return {c['id']:c['state'] for c in requests.get(base+'/api/status/').json()['checks']}
 try:
  for _ in range(100):
   try:
    with socket.create_connection(('127.0.0.1',port),timeout=.2):break
   except OSError:time.sleep(.1)
  assert requests.put(base+'/api/status/').status_code==405
  assert ping(nonce='0'*32,ts=int(time.time())-1000).status_code==401
  assert signed('/api/status/',{'node':'eu'},secrets.token_hex(32),'Status').status_code==401
  assert ping('mars').status_code==400
  n=secrets.token_hex(16);assert ping(nonce=n).status_code==200 and ping(nonce=n).status_code==409
  st=states();assert st=={'node':'ok','pool':'ok','faucet':'down','census':'ok','history':'ok','ping-eu':'ok','ping-us':'down'},st
  first=mails();assert len(first)==1 and first[0]['to']=='owner@example.org' and 'Faucet' in first[0]['body'] and 'US node' in first[0]['body'],first
  assert 'EU node' not in first[0]['body']  # ok checks are not reported
  states();assert len(mails())==1  # no change, no mail
  # Heartbeat: ok, low funds (warn), halted (down); bad heartbeat input refused.
  assert signed('/api/faucet/worker/',{'action':'heartbeat','balance_atomic':12},worker_secret,'Faucet').status_code==400
  assert beat().status_code==200;ping('us');st=states();assert st['faucet']=='ok' and st['ping-us']=='ok',st
  recovered=mails()[-1];assert 'RECOVERED' in recovered['body'] and 'Faucet' in recovered['body'],recovered
  assert beat('900000000000').status_code==200;assert states()['faucet']=='warn'
  assert beat('2999044290000',halted='claim 7: transfer outcome unknown').status_code==200
  body=requests.get(base+'/api/status/').json();st=states();assert st['faucet']=='down',st
  assert 'halted' in mails()[-1]['body'] and 'claim 7' in mails()[-1]['body']
  # Old heartbeat: silent worker is down. Paused by the owner: ok.
  hb=json.loads((private/'faucet-heartbeat.json').read_text());hb['at']=now-3600;hb['halted']=None;(private/'faucet-heartbeat.json').write_text(json.dumps(hb))
  assert states()['faucet']=='down'
  faucet_config(False);assert states()['faucet']=='ok';faucet_config()
  # Node, pool, census and history faults.
  node['tip_age']=4000;assert states()['node']=='warn';node['tip_age']=9000;assert states()['node']=='down';node['tip_age']=60
  node['sync']=False;assert states()['node']=='warn';node['sync']=True
  pool['height']=12990;assert states()['pool']=='warn';pool['up']=False;assert states()['pool']=='down';pool['up']=True;pool['height']=13000
  (data/'24h.json').write_text(json.dumps({'generated_at':now-7200}));assert states()['history']=='down'
  # Public output never contains secrets or the config.
  text=requests.get(base+'/api/status/').text;assert secret not in text and worker_secret not in text and 'owner@example.org' not in text
  # The node-side client.
  (tmp/'secret').write_text(secret)
  out=subprocess.run([sys.executable,str(root/'utils/website/status_ping.py'),'--node','us','--secret-file',str(tmp/'secret'),'--site-url',base],capture_output=True,text=True,timeout=60)
  assert out.returncode==0 and 'checked in' in out.stdout,out.stdout+out.stderr
  # Page.
  from playwright.sync_api import sync_playwright
  with sync_playwright() as p:
   browser=p.chromium.launch(headless=True,executable_path=shutil.which('chromium'))
   for width in (390,1440):
    page=browser.new_page(viewport={'width':width,'height':900});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(base+'/status/');page.wait_for_selector('#checks li')
    assert page.locator('#checks li').count()==7 and 'Not working' in page.locator('#checks').inner_text()
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth') and not errors,errors;page.close()
   browser.close()
 finally:server.terminate();server.wait(timeout=5);node_server.shutdown();pool_server.shutdown()
print('Status: node/pool/faucet/census/history/check-in states, signed check-ins, heartbeat, change-only alerts with recovery, client and page passed')
