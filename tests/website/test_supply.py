"""Exact supply (/api/v1/supply/ and the plain-number endpoints) against a fixture chain: rule-checked
rewards, fees subtracted, locked newest 60 blocks, over-minting refused, the audited checkpoint and a
moved checkpoint that is reorganised away (falls back to the audited one)."""
import http.server,json,shutil,socket,subprocess,tempfile,threading,time,urllib.request,urllib.error
from pathlib import Path
root=Path(__file__).resolve().parents[2]
SEED_H,SEED_G,SEED_HASH=12949,243976348592396971,'0044914f6efe48a9a2ae3c3f7fa8de51532edcda3811be62c6810ed4874851d7'
MS,SHIFT,TAIL=10**19,19,326000000000
FEE_H,FEE=12960,7_000_000
chain={'tip':13100,'overmint':None,'fork':set()}
def build():
 g=SEED_G;out={SEED_H:dict(height=SEED_H,hash='f'*64 if SEED_H in chain['fork'] else SEED_HASH,reward=0,num_txes=0)};cum={SEED_H:g}
 for h in range(SEED_H+1,chain['tip']+1):
  allowed=max((MS-g)>>SHIFT,TAIL);fee=FEE if h==FEE_H else 0;reward=allowed+fee+(1 if h==chain['overmint'] else 0)
  out[h]=dict(height=h,hash=('f' if h in chain['fork'] else 'a')+f'{h:063x}',reward=reward,num_txes=1 if fee else 0);g+=allowed;cum[h]=g
 return out,cum
class Node(http.server.BaseHTTPRequestHandler):
 def do_POST(self):
  req=json.loads(self.rfile.read(int(self.headers['Content-Length'])));heads,_=build();tip=chain['tip']
  if self.path=='/get_transactions':
   body={'status':'OK','txs':[{'as_json':json.dumps({'version':2,'rct_signatures':{'txnFee':FEE}})}]}
  else:
   m,p=req['method'],req.get('params',{})
   if m=='get_info':r=dict(status='OK',height=tip+1,nettype='mainnet')
   elif m=='get_block_headers_range':r=dict(status='OK',headers=[heads[h] for h in range(p['start_height'],p['end_height']+1) if h in heads])
   elif m=='get_block':r=dict(status='OK',tx_hashes=['b'*64] if p['height']==FEE_H else [])
   else:r=None
   body={'jsonrpc':'2.0','id':req['id'],'result':r}
  b=json.dumps(body).encode();self.send_response(200);self.end_headers();self.wfile.write(b)
 def log_message(self,*a):pass
node=http.server.ThreadingHTTPServer(('127.0.0.1',0),Node);threading.Thread(target=node.serve_forever,daemon=True).start()
with tempfile.TemporaryDirectory() as tmp:
 site=Path(tmp)/'site';shutil.copytree(root/'website/api/v1',site/'api/v1');state=Path(tmp)/'state';state.mkdir()
 lib=site/'api/v1/lib.php';lib.write_text(lib.read_text().replace('http://node.monzero.org:6175',f'http://127.0.0.1:{node.server_port}'))
 with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
 server=subprocess.Popen(['php','-S',f'127.0.0.1:{port}','-t',str(site)],env={**__import__('os').environ,'TMPDIR':str(state)},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 def get(path):
  for f in state.rglob('cache-*.json'):f.unlink()
  try:r=urllib.request.urlopen(f'http://127.0.0.1:{port}{path}',timeout=30)
  except urllib.error.HTTPError as e:r=e
  with r:return r.status,r.headers.get('Content-Type'),r.read().decode()
 xmz=lambda a:(lambda p:p[:-11]+('.'+p[-11:].rstrip('0') if p[-11:].rstrip('0') else ''))(str(a).rjust(12,'0'))
 try:
  for _ in range(100):
   try:
    with socket.create_connection(('127.0.0.1',port),timeout=.2):break
   except OSError:time.sleep(.1)
  _,cum=build();tip=chain['tip']
  code,ctype,body=get('/api/v1/supply/');d=json.loads(body)['data']
  assert code==200 and d['total_atomic']==str(cum[tip]) and d['circulating_atomic']==str(cum[tip-60]) and d['max_supply'] is None and d['height']==tip+1,(code,d)
  assert d['total_supply']==xmz(cum[tip]) and d['circulating_supply']==xmz(cum[tip-60])
  code,ctype,body=get('/api/v1/supply/circulating/');assert code==200 and ctype.startswith('text/plain') and body.strip()==xmz(cum[tip-60])
  code,ctype,body=get('/api/v1/supply/total/');assert body.strip()==xmz(cum[tip])
  assert not list(state.rglob('supply-checkpoint.json'))  # tip-200 is below the seed: no move yet
  # Longer chain: the checkpoint moves to tip-200 and later requests start there.
  chain['tip']=13400;_,cum=build();d=json.loads(get('/api/v1/supply/')[2])['data'];assert d['total_atomic']==str(cum[13400])
  cp=json.loads(next(state.rglob('supply-checkpoint.json')).read_text());assert cp['height']==13200 and cp['generated']==str(cum[13200])
  # The moved checkpoint is reorganised away: refused once, then recomputed from the audited seed.
  chain['fork']={13200};code,_,_=get('/api/v1/supply/');assert code==502 and not list(state.rglob('supply-checkpoint.json'))
  _,cum=build();code,_,body=get('/api/v1/supply/');assert code==200 and json.loads(body)['data']['total_atomic']==str(cum[13400])
  # A block minting one atomic unit too much stops the calculation; so does a chain without the audited block.
  chain['overmint']=13350;[f.unlink() for f in state.rglob('supply-checkpoint.json')]
  code,_,body=get('/api/v1/supply/');assert code==502 and 'node_unavailable' in body
  assert get('/api/v1/supply/total/')[0]==502;chain['overmint']=None
  chain['fork']={SEED_H};[f.unlink() for f in state.rglob('supply-checkpoint.json')];assert get('/api/v1/supply/')[0]==502
 finally:server.terminate();server.wait(timeout=5);node.shutdown()
print('Supply: exact totals with fees, locked newest 60 blocks, plain-number endpoints, checkpoint moves and reorg fallback, over-minting and foreign chain refused passed')
