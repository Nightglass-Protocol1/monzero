"""API v1 integration: actual PHP endpoints against a fixture node; never reaches the public node."""
import http.server,json,shutil,socket,subprocess,tempfile,threading,time,urllib.request,urllib.error
from pathlib import Path
root=Path(__file__).resolve().parents[2]
H=lambda n:f'{n:064x}'
def header(h,depth=0):return dict(height=h,hash=H(h+1),prev_hash=H(h),timestamp=1787690983+120*h,difficulty=30000+h,reward=326000000000,num_txes=h%3,block_size=300,block_weight=300,depth=depth,orphan_status=False,major_version=16,minor_version=16,nonce=1,miner_tx_hash=H(9))
state={'tip':99,'mode':'ok','calls':[]}
class Node(http.server.BaseHTTPRequestHandler):
 def do_POST(self):
  req=json.loads(self.rfile.read(int(self.headers['Content-Length'])));m=req['method'];p=req.get('params',{});state['calls'].append(m);tip=state['tip']
  if state['mode']=='down':self.send_response(500);self.end_headers();return
  if m=='get_info':r=dict(status='OK',height=tip+1,difficulty=36000,nettype='testnet' if state['mode']=='testnet' else 'mainnet',synchronized=True,top_block_hash=H(tip+1),tx_pool_size=2)
  elif m=='get_last_block_header':r=dict(status='OK',block_header=header(tip))
  elif m=='get_block_header_by_height':r=dict(status='OK',block_header=header(p['height'],tip-p['height']))
  elif m=='get_block_headers_range':
   hs=[header(h,tip-h) for h in range(p['start_height'],p['end_height']+1)]
   if state['mode']=='broken':hs[3]['prev_hash']=H(0)
   r=dict(status='OK',headers=hs)
  else:r=None
  body=json.dumps({'jsonrpc':'2.0','id':req['id'],'result':r}).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(body)
 def log_message(self,*a):pass
node=http.server.ThreadingHTTPServer(('127.0.0.1',0),Node);threading.Thread(target=node.serve_forever,daemon=True).start()
def get(port,path,method='GET'):
 try:r=urllib.request.urlopen(urllib.request.Request(f'http://127.0.0.1:{port}{path}',method=method),timeout=15)
 except urllib.error.HTTPError as e:r=e
 with r:
  body=r.read();return r.status,r.headers,(json.loads(body) if body else None)
with tempfile.TemporaryDirectory() as tmp:
 site=Path(tmp)/'site';shutil.copytree(root/'website/api/v1',site/'api/v1')
 for c in ['exchanges/catalog.json','ecosystem/catalog.json','mining/benchmarks/catalog.json']:(site/c).parent.mkdir(parents=True,exist_ok=True);shutil.copy(root/'website'/c,site/c)
 lib=site/'api/v1/lib.php';src=lib.read_text();assert "'http://node.monzero.org:6175'" in src
 lib.write_text(src.replace('http://node.monzero.org:6175',f'http://127.0.0.1:{node.server_port}').replace('V1_CLIENT_LIMIT = 60','V1_CLIENT_LIMIT = 25'))
 with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
 env={'TMPDIR':str(Path(tmp)/'state')};(Path(tmp)/'state').mkdir()
 server=subprocess.Popen(['php','-S',f'127.0.0.1:{port}','-t',str(site)],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 try:
  for _ in range(50):
   try:
    with socket.create_connection(('127.0.0.1',port),timeout=.2):break
   except OSError:time.sleep(.1)
  status,h,body=get(port,'/api/v1/network/stats/');d=body['data']
  assert status==200 and body['schema']=='monzero-api-v1' and body['source'] and isinstance(body['observed_at'],int)
  assert d['height']==100 and d['top_block_height']==99 and d['difficulty']=='36000' and d['hashrate_estimate']==300.0 and d['top_block_reward_atomic']=='326000000000'
  assert h['Access-Control-Allow-Origin']=='*' and h['X-Content-Type-Options']=='nosniff' and 'max-age=15' in h['Cache-Control']
  calls=len(state['calls']);get(port,'/api/v1/network/hashrate/');get(port,'/api/v1/network/difficulty/');assert len(state['calls'])==calls,'network observation must be cached'
  status,_,body=get(port,'/api/v1/blocks/latest/?count=5');bl=body['data']['blocks']
  assert status==200 and [b['height'] for b in bl]==[99,98,97,96,95] and bl[0]['reward_atomic']=='326000000000' and 'pow_hash' not in bl[0] and 'nonce' not in bl[0]
  status,_,body=get(port,'/api/v1/blocks/?height=10');assert status==200 and body['data']['block']['height']==10 and body['data']['block']['depth']==89
  for path,code in [('/api/v1/blocks/?height=100',404),('/api/v1/blocks/?height=-1',400),('/api/v1/blocks/?height=01',400),('/api/v1/blocks/',400),('/api/v1/blocks/?height[]=1',400),('/api/v1/blocks/latest/?count=31',400),('/api/v1/blocks/latest/?count=0',400),('/api/v1/network/stats/?debug=1',400),('/api/v1/lib.php',404)]:
   status,_,body=get(port,path);assert status==code,(path,status,body)
   if code!=404 or 'lib' not in path:assert body['error']['code'] and body['error']['message'],path
  status,h,_=get(port,'/api/v1/network/stats/','POST');assert status==405 and 'GET' in h['Allow']
  status,_,body=get(port,'/api/v1/exchanges/');assert status==200 and all(r['status']!='live' for r in body['data']['records'])
  status,_,body=get(port,'/api/v1/mining/pools/');assert status==200 and any(p['url']=='https://pool.monzero.org/' for p in body['data']['pools'])
  status,_,body=get(port,'/api/v1/mining/benchmarks/');assert status==200 and isinstance(body['data']['records'],list)
  status,_,body=get(port,'/api/v1/');assert status==200 and '/api/v1/network/stats/' in body['data']['endpoints']
  # Fresh cache directory for failure cases: malformed upstream data is unavailable, never partial.
  for mode,path in [('testnet','/api/v1/network/stats/'),('down','/api/v1/network/stats/'),('broken','/api/v1/blocks/latest/')]:
   for f in (Path(tmp)/'state').glob('monzero-api-v1-*/cache-*'):f.unlink()
   state['mode']=mode;status,h,body=get(port,path);assert status==502 and body['error']['code']=='node_unavailable' and 'data' not in body,(mode,status,body)
   assert h['Cache-Control']=='no-store' and h['Retry-After']
  state['mode']='ok'
  seen=[get(port,'/api/v1/')[0] for _ in range(30)];assert 429 in seen,seen
  status,h,body=get(port,'/api/v1/');assert status==429 and body['error']['code']=='rate_limited' and int(h['Retry-After'])>=1
  stored=json.loads(next((Path(tmp)/'state').glob('monzero-api-v1-*/throttle.json')).read_text())
  assert '127.0.0.1' not in json.dumps(stored)
 finally:server.terminate();server.wait(timeout=5);node.shutdown()
print('API v1: envelopes, caching, linked ranges, validation, 405/404/400, outage/testnet/broken refusal, rate limit, no stored IPs passed')
