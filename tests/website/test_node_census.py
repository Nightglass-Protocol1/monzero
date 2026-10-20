"""Node census: collector aggregation and IP filtering, signed ingest (bad signature, replay, bad sums,
older census), the read-only API, no IPs in storage, and the country-only map page under the site CSP."""
import gzip,hashlib,hmac,http.server,json,os,secrets,shutil,socket,subprocess,sys,tempfile,threading,time
from pathlib import Path
import requests
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'utils/nodemap'))
import node_census as nc

def free_port():
 with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]

with tempfile.TemporaryDirectory() as tmp:
 tmp=Path(tmp)
 # Tiny DB-IP style database: 8.8.0.0/16 -> US, 81.2.69.0/24 -> GB, 2001:db8::/32 is documentation (never global).
 db_path=tmp/'dbip-country-lite-test.csv.gz'
 with gzip.open(db_path,'wt') as f:
  f.write('8.8.0.0,8.8.255.255,US\n81.2.69.0,81.2.69.255,GB\n2a00:1450::,2a00:1450:ffff:ffff:ffff:ffff:ffff:ffff,IE\nbad,row,XX\n')
 db=nc.CountryDB(str(db_path))
 assert db.country(nc.public_ip('8.8.4.4'))=='US' and db.country(nc.public_ip('81.2.69.160'))=='GB'
 assert db.country(nc.public_ip('2a00:1450::1'))=='IE' and db.country(nc.public_ip('1.1.1.1'))=='ZZ'
 for private in ['10.0.0.1','192.168.1.5','127.0.0.1','100.64.0.1','::1','fe80::1','abcdef.onion','','2001:db8::1']:assert nc.public_ip(private) is None,private
 assert str(nc.public_ip('::ffff:8.8.8.8'))=='8.8.8.8'

 # Fake node: white list (one stale, one private), gray list ignored, connections include a duplicate and an unknown.
 now=int(time.time())
 peers={'status':'OK','white_list':[
  {'host':'8.8.8.8','last_seen':now-60},{'host':'8.8.4.4','last_seen':now-3600},{'host':'81.2.69.160','last_seen':now-90000},
  {'host':'192.168.0.2','last_seen':now}],'gray_list':[{'host':'81.2.69.1','last_seen':now}]}
 conns={'jsonrpc':'2.0','id':0,'result':{'connections':[{'host':'8.8.8.8'},{'host':'81.2.69.5'},{'host':'1.1.1.1'},{'host':'10.1.1.1'}]}}
 class Node(http.server.BaseHTTPRequestHandler):
  def do_POST(self):
   self.rfile.read(int(self.headers['Content-Length']))
   body=json.dumps(peers if self.path=='/get_peer_list' else conns).encode()
   self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(body)
  def log_message(self,*a):pass
 node=http.server.ThreadingHTTPServer(('127.0.0.1',0),Node);threading.Thread(target=node.serve_forever,daemon=True).start()
 reachable,connected=nc.collect(f'http://127.0.0.1:{node.server_port}',now)
 assert {str(i) for i in reachable}=={'8.8.8.8','8.8.4.4'} and {str(i) for i in connected}=={'8.8.8.8','81.2.69.5','1.1.1.1'}
 payload=nc.census(reachable,connected,db,now)
 assert payload['totals']=={'observed':4,'reachable':2,'connected':3},payload
 assert payload['countries']=={'GB':{'observed':1,'reachable':0,'connected':1},'US':{'observed':2,'reachable':2,'connected':1},'ZZ':{'observed':1,'reachable':0,'connected':1}}
 assert not any(ip in json.dumps(payload) for ip in ['8.8','81.2','1.1.1.1'])
 node.shutdown()

 # Website ingest and API.
 private=tmp/'private';(private/'node-census').mkdir(parents=True)
 secret=secrets.token_hex(32);(private/'node-census-config.php').write_text(f"<?php return ['secret' => '{secret}'];\n")
 port=free_port();base=f'http://127.0.0.1:{port}'
 env={**os.environ,'MONZERO_NODE_CENSUS_DIR':str(private/'node-census')}
 server=subprocess.Popen(['php','-S',f'127.0.0.1:{port}','-t',str(root/'website')],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 try:
  for _ in range(100):
   try:
    with socket.create_connection(('127.0.0.1',port),timeout=.2):break
   except OSError:time.sleep(.1)
  assert requests.get(base+'/api/v1/network/nodes/').status_code==503
  def raw(body,key=secret,ts=None,nonce=None):
   ts=str(ts or int(time.time()));nonce=nonce or secrets.token_hex(16)
   sig=hmac.new(key.encode(),f'{ts}\n{nonce}\n'.encode()+body,hashlib.sha256).hexdigest()
   return requests.post(base+'/api/node-census/',data=body,headers={'X-Census-Timestamp':ts,'X-Census-Nonce':nonce,'X-Census-Signature':sig})
  body=json.dumps(payload,separators=(',',':')).encode()
  assert requests.get(base+'/api/node-census/').status_code==405
  assert raw(body,key=secrets.token_hex(32)).status_code==401
  assert raw(body,ts=int(time.time())-1000).status_code==401
  code,reply=nc.send(base,secret,payload);assert code==200,(code,reply)
  nonce=secrets.token_hex(16);later=dict(payload,observed_at=payload['observed_at']+1)
  assert raw(json.dumps(later,separators=(',',':')).encode(),nonce=nonce).status_code==200
  assert raw(json.dumps(dict(later,observed_at=later['observed_at']+1),separators=(',',':')).encode(),nonce=nonce).status_code==409  # replayed nonce
  assert raw(body).status_code==409  # older than stored
  bad=json.loads(json.dumps(later));bad['observed_at']+=5;bad['countries']['US']['observed']=9
  assert raw(json.dumps(bad).encode()).status_code==400
  bad=json.loads(json.dumps(later));bad['observed_at']+=5;bad['countries']['us']=bad['countries'].pop('US')
  assert raw(json.dumps(bad).encode()).status_code==400
  bad=json.loads(json.dumps(later));bad['observed_at']+=5;bad['ip']='8.8.8.8'
  assert raw(json.dumps(bad).encode()).status_code==400  # extra keys are refused
  r=requests.get(base+'/api/v1/network/nodes/?history=daily');api=r.json()
  assert r.status_code==200 and api['observed_at']==later['observed_at'] and api['data']['totals']==payload['totals'] and api['data']['stale'] is False
  assert api['data']['countries']['US']['reachable']==2 and len(api['data']['history'])==1 and 'DB-IP' in api['data']['geo_attribution']
  assert requests.get(base+'/api/v1/network/nodes/?history=all').status_code==400
  assert requests.get(base+'/lib/node-census.php').status_code==404
  stored=''.join(p.read_text() for p in (private/'node-census').glob('*.json'))
  assert not any(ip in stored for ip in ['8.8.8.8','8.8.4.4','81.2.69','1.1.1.1'])
  assert all(oct(p.stat().st_mode&0o777)=='0o600' for p in (private/'node-census').glob('*.json'))

  # Two vantage points: one-way daily tags, a node seen by both counted once, old or other-day reports left out.
  salt=secrets.token_hex(32);ips=lambda *a:{nc.public_ip(x) for x in a}
  eu=nc.tagged_census(ips('8.8.8.8','8.8.4.4'),ips('8.8.8.8','81.2.69.5'),db,int(time.time())+20,'eu',salt)
  us=nc.tagged_census(ips('8.8.8.8'),ips('81.2.69.5','81.2.69.9','1.1.1.1'),db,int(time.time())+21,'us',salt)
  assert '8.8.8.8' not in json.dumps(eu) and eu['tag_day']==time.strftime('%Y-%m-%d',time.gmtime(eu['observed_at']))
  assert set(eu['countries']['US']['reachable']) & set(us['countries']['US']['reachable'])  # same address, same tag
  other=nc.tagged_census(ips('8.8.8.8'),set(),db,int(time.time()),'us','different salt');assert other['countries']['US']['reachable'][0] not in eu['countries']['US']['reachable']
  code,reply=nc.send(base,secret,eu);assert code==200,(code,reply)
  code,reply=nc.send(base,secret,us);assert code==200,(code,reply)
  merged=requests.get(base+'/api/v1/network/nodes/').json()['data']
  assert merged['vantages']==['eu','us'] and 'node.monzero.org and node2.monzero.org' in merged['vantage']
  # Union: US {8.8.8.8, 8.8.4.4}, GB {81.2.69.5, 81.2.69.9}, unknown {1.1.1.1}.
  assert merged['totals']=={'observed':5,'reachable':2,'connected':4},merged['totals']
  assert merged['countries']['US']=={'observed':2,'reachable':2,'connected':1} and merged['countries']['GB']=={'observed':2,'reachable':0,'connected':2},merged['countries']
  assert nc.send(base,secret,dict(us,observed_at=us['observed_at']-1))[0]==409  # older than this vantage's last report
  bad=json.loads(json.dumps(us));bad['observed_at']+=5;bad['countries']['US']['reachable']=['8.8.8.8'];assert nc.send(base,secret,bad)[0]==400
  bad=json.loads(json.dumps(us));bad['observed_at']+=5;bad['vantage']='mars';assert nc.send(base,secret,bad)[0]==400
  bad=json.loads(json.dumps(us));bad['observed_at']+=5;bad['tag_day']='2000-01-01';assert nc.send(base,secret,bad)[0]==400
  stored=''.join(p.read_text() for p in (private/'node-census').glob('*.json'));assert not any(ip in stored for ip in ['8.8.8.8','81.2.69','1.1.1.1'])
  assert all(len(t)==16 for c in json.loads((private/'node-census/vantage-eu.json').read_text())['countries'].values() for t in c['reachable']+c['connected'])
  # Browser: map under the production CSP, table, legend, no layout overflow.
  from playwright.sync_api import sync_playwright
  csp="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'"
  with sync_playwright() as p:
   browser=p.chromium.launch(headless=True,executable_path=shutil.which('chromium'))
   for width in (390,1440):
    page=browser.new_page(viewport={'width':width,'height':900});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('response',lambda r: errors.append(f'{r.status} {r.url}') if r.status >= 400 and not r.url.endswith('/news/data/latest.json') else None)
    page.on('console',lambda m:errors.append(m.text) if m.type=='error' and 'Failed to load resource' not in m.text else None)
    def with_csp(route):
     resp=route.fetch();route.fulfill(response=resp,headers={**resp.headers,'content-security-policy':csp})
    page.route('**/network/nodes/',with_csp)
    page.goto(base+'/network/nodes/');page.wait_for_selector('#map svg path[class^="lvl-"]')
    assert page.locator('#map svg path[data-cc=US]').get_attribute('class')=='lvl-2'
    assert page.locator('#map svg path[data-cc=GB]').get_attribute('class')=='lvl-2'
    assert page.locator('#map svg path[class]').count()==2
    rows=page.locator('#rows tr');assert rows.count()==3
    assert 'United Kingdom' in rows.nth(0).inner_text() and 'United States' in rows.nth(1).inner_text() and 'Unknown' in rows.nth(2).inner_text()
    assert '5 observed nodes in 2 countries' in page.locator('#status').inner_text() and 'node2.monzero.org' in page.locator('#summary').inner_text()
    assert page.locator('#history-rows tr').count()==1
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),width
    assert not errors,errors;page.close()
   page=browser.new_page();page.route('**/api/v1/network/nodes/**',lambda r:r.fulfill(status=503,content_type='application/json',body='{"schema":"monzero-api-v1","error":{"code":"unavailable","message":"x"}}'))
   page.goto(base+'/network/nodes/');page.wait_for_function("document.getElementById('status').textContent.includes('No node census')")
   assert page.locator('#map-figure').is_hidden();page.close()
   browser.close()
 finally:server.terminate();server.wait(timeout=5)
print('Node census: IP filtering, country aggregation, signed ingest (signature/replay/sums/order), API, no stored IPs, country-only map under CSP passed')
