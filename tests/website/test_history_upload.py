"""Network history upload: real collector exports bundled and signed by history_upload.py, ingest
signature/replay/source/order checks, atomic public files, and the /network/ page rendering them."""
import gzip,hashlib,hmac,importlib.util,json,os,secrets,shutil,socket,subprocess,sys,tempfile,time
from pathlib import Path
import requests
root=Path(__file__).resolve().parents[2]
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,root/path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
h=load('history','utils/website/network_history.py');up=load('upload','utils/website/history_upload.py')
def sample(at,height,difficulty):
 return {'schema':'monzero-chain-charts-v2','network':'mainnet','target_seconds':120,'height':height,'generated_at':at,'synchronized':True,
         'blocks':[{'height':n,'timestamp':at-120*(height-1-n),'difficulty':difficulty,'transactions':0} for n in range(max(1,height-720),height)]}

with tempfile.TemporaryDirectory() as tmp:
 tmp=Path(tmp);now=int(time.time())
 db=h.connect(tmp/'collector/history.sqlite')
 for i in range(60):h.record(db,sample(now-3600+i*60,13000+i,40000000+i*1000),'live',now-3600+i*60)
 public=tmp/'public';h.publish(db,public,now)
 pre=h.connect(tmp/'preview/history.sqlite');h.record(pre,sample(now-60,13000,40000000),'preview',now-60);preview_public=tmp/'preview-public';h.publish(pre,preview_public,now)
 private=tmp/'private';private.mkdir();data=tmp/'docroot-data'
 secret=secrets.token_hex(32);(private/'network-history-config.php').write_text(f"<?php return ['secret' => '{secret}'];\n")
 with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
 base=f'http://127.0.0.1:{port}'
 env={**os.environ,'MONZERO_PRIVATE_DIR':str(private),'MONZERO_NETWORK_DATA_DIR':str(data)}
 server=subprocess.Popen(['php','-S',f'127.0.0.1:{port}','-t',str(root/'website')],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 try:
  for _ in range(100):
   try:
    with socket.create_connection(('127.0.0.1',port),timeout=.2):break
   except OSError:time.sleep(.1)
  def raw(body,key=secret,ts=None,nonce=None):
   ts=str(ts or int(time.time()));nonce=nonce or secrets.token_hex(16)
   sig=hmac.new(key.encode(),f'{ts}\n{nonce}\n'.encode()+body,hashlib.sha256).hexdigest()
   return requests.post(base+'/api/network-history/',data=body,headers={'X-History-Timestamp':ts,'X-History-Nonce':nonce,'X-History-Signature':sig})
  body=up.bundle(public)
  assert requests.get(base+'/api/network-history/').status_code==405
  assert raw(body,key=secrets.token_hex(32)).status_code==401
  assert raw(body,ts=int(time.time())-1000).status_code==401
  code,reply=up.upload(base,secret,body);assert code==200 and sorted(reply['written'])==sorted(up.RANGES),(code,reply)
  for name in up.RANGES:
   served=json.loads((data/f'{name}.json').read_text());assert served==json.loads((public/f'{name}.json').read_text()),name
   assert oct((data/f'{name}.json').stat().st_mode&0o777)=='0o644'
  assert not list(data.glob('.history-upload-*'))
  # Same generation again: accepted but nothing replaced. Replayed nonce: refused.
  nonce=secrets.token_hex(16);r=raw(body,nonce=nonce);assert r.status_code==200 and r.json()['written']==[]
  assert raw(body,nonce=nonce).status_code==409
  # Preview-source archives, unknown ranges, too many points and garbage are refused.
  assert raw(up.bundle(preview_public)).status_code==400
  bad=json.loads(gzip.decompress(body));bad['5y']=bad['24h'];assert raw(gzip.compress(json.dumps(bad).encode())).status_code==400
  bad=json.loads(gzip.decompress(body));bad['24h']['points']=bad['24h']['points']*40;assert len(bad['24h']['points'])>721;bad['24h']['generated_at']+=1
  assert raw(gzip.compress(json.dumps({'24h':bad['24h']}).encode())).status_code==400
  assert raw(b'not gzip').status_code==400
  # Newer generation replaces the files.
  h.record(db,sample(now+60,13060,41000000),'live',now+60);h.publish(db,public,now+60)
  code,reply=up.upload(base,secret,up.bundle(public));assert code==200 and len(reply['written'])==6
  assert json.loads((data/'24h.json').read_text())['generated_at']==now+60

  # The existing /network/ page renders the uploaded files.
  from playwright.sync_api import sync_playwright
  with sync_playwright() as p:
   browser=p.chromium.launch(headless=True,executable_path=shutil.which('chromium'))
   page=browser.new_page(viewport={'width':1440,'height':900});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
   page.route('**/network/data/*.json*',lambda r:r.fulfill(status=200,content_type='application/json',body=(data/(r.request.url.split('/network/data/')[1].split('?')[0])).read_text()))
   page.goto(base+'/network/');page.wait_for_function("document.querySelectorAll('#rows tr').length>0",timeout=15000)
   assert page.locator('#results').is_visible() and not errors,errors
   browser.close()
 finally:server.terminate();server.wait(timeout=5);db.close();pre.close()
print('History upload: signed bundle, signature/replay/source/range/points checks, atomic public files, newer-only replacement, /network/ renders uploads passed')
