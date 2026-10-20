"""Faucet end to end: accounts (email, password, mandatory TOTP), Turnstile, address rules,
24-hour/address/network/budget limits, the signed worker interface and the real payout worker
against a fake wallet RPC. Needs PHP with pdo_sqlite and gmp (production has both)."""
import urllib.parse,base64,hashlib,hmac,http.server,json,os,re,secrets,socket,sqlite3,struct,subprocess,sys,tempfile,threading,time
from pathlib import Path
import requests
root=Path(__file__).resolve().parents[2]
PW='correct horse battery staple'
ADDR=['FWPbFrwvRqpWTMDJAAeT3wAGsCUvERHyEAZJySDBDTKJJxr4q9gNStxSZghEAmtgvd49oySaDP9WGV1KVDeDXFBfM748KwK',
 'Fj4gs1bC1Wf82NWMYCm7gaifFntWiVDz83ZYNEVtwyUmSWxPAAM8Bjy4XwbK2k91Jq5VG3ndJLHrDhs2SoYPryYEBwWxL9J',
 'FQLhxULkbyx4886T7196doS9GPMzexD9gXpsZJDwVjeRVdFCSoHnv7KPbBeGpzJBzHRCAs9UxqeoyFQMYbqSWYTfJJCEnHf',
 'FS1LtxYqTVPRDV5aAhLJzQCjDz2ViLRduE3ijDZu3osWKBjMGkV1XPk4pfDUMqt1Aiezvephdqm6YD19GKFD9ZcXVUEgtLB',
 'FraTu7LjjcZeKvcs4Q4FYGRR14WHcisMnQaApGDwUpiHKq7go5Bpxt7T1qpDkmbb5o85N3anx7eyj6fPvd3VegvJUKiAEGq']  # last: wallet-cli subaddress
AMOUNT='10000000000'

def totp(secret,offset=0):
 key=base64.b32decode(secret);counter=int(time.time())//30+offset
 h=hmac.new(key,struct.pack('>Q',counter),hashlib.sha1).digest();o=h[19]&15
 return f"{(struct.unpack('>I',h[o:o+4])[0]&0x7fffffff)%1000000:06d}"

def serve(handler):
 s=http.server.ThreadingHTTPServer(('127.0.0.1',0),handler);threading.Thread(target=s.serve_forever,daemon=True).start();return s

seen=set()
class Turnstile(http.server.BaseHTTPRequestHandler):
 def do_POST(self):
  form=dict(x.split('=',1) for x in self.rfile.read(int(self.headers['Content-Length'])).decode().split('&'))
  token=urllib.parse.unquote(form.get('response',''));ok=token.startswith('good') and form.get('secret')=='test-secret'
  action=token.split(':',1)[1] if ':' in token else ''
  host='evil.test' if token.startswith('goodhost') else 'faucet.test'
  if token in seen:ok=False
  seen.add(token)
  body=json.dumps({'success':ok,'action':action,'hostname':host}).encode()
  self.send_response(200);self.end_headers();self.wfile.write(body)
 def log_message(self,*a):pass

wallet={'mode':'ok','sent':[],'balance':10**12,'locked':0}
class Wallet(http.server.BaseHTTPRequestHandler):
 def do_POST(self):
  req=json.loads(self.rfile.read(int(self.headers['Content-Length'])));m,p=req['method'],req.get('params',{})
  if m=='transfer' and wallet['mode']=='drop':self.connection.close();return
  if m=='validate_address':r={'valid':p['address'] in ADDR,'nettype':'mainnet'}
  elif m=='get_balance':r={'balance':wallet['balance'],'unlocked_balance':wallet['balance']-wallet['locked']}
  elif m=='transfer':
   txid=secrets.token_hex(32);wallet['sent'].append((p['destinations'][0]['address'],p['destinations'][0]['amount'],txid));wallet['balance']-=p['destinations'][0]['amount'];r={'tx_hash':txid}
  else:r=None
  body=json.dumps({'jsonrpc':'2.0','id':'0','result':r}).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(body)
 def log_message(self,*a):pass

turnstile=serve(Turnstile);wallet_server=serve(Wallet)
with tempfile.TemporaryDirectory() as tmp:
 tmp=Path(tmp);(tmp/'private').mkdir();db=tmp/'private/faucet.sqlite';mail=tmp/'mail.jsonl';cfg=tmp/'faucet-config.php'
 with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
 base=f'http://127.0.0.1:{port}';secret_hex=secrets.token_hex(32)
 def config(**over):
  c=dict(enabled=True,amount_atomic=AMOUNT,daily_cap_atomic=str(3*int(AMOUNT)),cooldown_seconds=86400,per_client_daily=5,signups_per_client_daily=10,
   turnstile_site_key='test-site',turnstile_secret='test-secret',turnstile_verify_url=f'http://127.0.0.1:{turnstile.server_port}/',turnstile_hostnames=['faucet.test'],worker_secret=secret_hex,base_url=base);c.update(over)
  def php(v):
   if isinstance(v,list):return '['+','.join(php(x) for x in v)+']'
   if isinstance(v,bool):return 'true' if v else 'false'
   if isinstance(v,int):return str(v)
   return "'"+str(v).replace("\\","\\\\").replace("'","\\'")+"'"
  cfg.write_text('<?php return ['+','.join(f"'{k}'=>{php(v)}" for k,v in c.items())+'];')
 config()
 env={**os.environ,'MONZERO_FAUCET_DB':str(db),'MONZERO_FAUCET_CONFIG':str(cfg),'MONZERO_FAUCET_MAIL_LOG':str(mail),'MONZERO_FAUCET_HEARTBEAT':str(tmp/'private/faucet-heartbeat.json')}
 server=subprocess.Popen(['php','-S',f'127.0.0.1:{port}','-t',str(root/'website')],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 def mails(to):return [json.loads(l) for l in mail.read_text().splitlines() if json.loads(l)['to']==to] if mail.exists() else []
 def post(s,do,data,**kw):
  # 'good' means: a fresh single-use token issued for this form's action on our hostname.
  if data.get('cf-turnstile-response')=='good':data={**data,'cf-turnstile-response':f'good{secrets.token_hex(6)}:{do}'}
  return s.post(base+f'/faucet/?do={do}',data=data,allow_redirects=False,**kw)
 def csrf(s):return re.search(r'name="csrf" value="([^"]+)"',s.get(base+'/faucet/').text).group(1)
 def member(email,address,offset=0):
  s=requests.Session()
  assert post(s,'signup',{'email':email,'password':PW,'confirm':PW,'cf-turnstile-response':'good'}).status_code==303
  link=re.search(r'\?verify=([A-Za-z0-9_-]{43})',mails(email)[-1]['body']).group(1)
  assert s.get(base+f'/faucet/?verify={link}',allow_redirects=False).status_code==303
  assert post(s,'login',{'email':email,'password':PW,'cf-turnstile-response':'good'}).status_code==303
  page=s.get(base+'/faucet/').text;sec=re.search(r'name="secret" value="([A-Z2-7]{32})"',page).group(1)
  assert post(s,'totp',{'csrf':csrf(s),'secret':sec,'code':totp(sec,-1)}).status_code==303
  if address:assert post(s,'address',{'csrf':csrf(s),'address':address,'code':totp(sec)}).status_code==303,email
  return s,sec
 try:
  for _ in range(100):
   try:
    with socket.create_connection(('127.0.0.1',port),timeout=.2):break
   except OSError:time.sleep(.1)
  # Landing page, status endpoint, internals hidden.
  page=requests.get(base+'/faucet/');assert page.status_code==200 and 'Sign in' in page.text and 'cf-turnstile' in page.text and '0.1 XMZ once every 24 hours' in page.text
  st=requests.get(base+'/api/faucet/').json();assert st['status']=='open' and st['amount_atomic']==AMOUNT and 'worker_secret' not in json.dumps(st)
  for path in ['/faucet/lib.php','/lib/auth.php','/lib/xmz-address.php']:assert requests.get(base+path).status_code==404,path
  # Sign-up: bot check, password rules, confirmation email, no account enumeration.
  a=requests.Session()
  assert post(a,'signup',{'email':'alice@example.org','password':PW,'confirm':PW,'cf-turnstile-response':'bad'}).status_code==400
  assert post(a,'signup',{'email':'alice@example.org','password':'short','confirm':'short','cf-turnstile-response':'good'}).status_code==400
  assert post(a,'signup',{'email':'alice@example.org','password':PW,'confirm':PW,'cf-turnstile-response':'good'}).status_code==303
  assert post(a,'signup',{'email':'alice@example.org','password':PW,'confirm':PW,'cf-turnstile-response':'good'}).status_code==303
  assert len(mails('alice@example.org'))==1
  assert post(a,'login',{'email':'alice@example.org','password':PW,'cf-turnstile-response':'good'}).status_code==403
  link=re.search(r'\?verify=([A-Za-z0-9_-]{43})',mails('alice@example.org')[0]['body']).group(1)
  assert a.get(base+f'/faucet/?verify={link}',allow_redirects=False).status_code==303
  assert a.get(base+f'/faucet/?verify={link}',allow_redirects=False).status_code==400
  # Sign-in leads to mandatory 2FA setup; nothing else works until it is on.
  assert post(a,'login',{'email':'alice@example.org','password':PW,'cf-turnstile-response':'bad'}).status_code==400
  assert post(a,'login',{'email':'alice@example.org','password':PW,'cf-turnstile-response':'good'}).status_code==303
  page=a.get(base+'/faucet/').text;assert 'Set up two-factor authentication' in page
  assert post(a,'claim',{'csrf':csrf(a),'cf-turnstile-response':'good'}).status_code==429
  sec=re.search(r'name="secret" value="([A-Z2-7]{32})"',page).group(1)
  assert post(a,'totp',{'csrf':csrf(a),'secret':sec,'code':'000000' if totp(sec)!='000000' else '111111'}).status_code==400
  assert post(a,'totp',{'csrf':csrf(a),'secret':sec,'code':totp(sec,-1)}).status_code==303
  assert 'Your faucet' in a.get(base+'/faucet/').text
  # Claims need an address; address changes need a fresh TOTP code (no replay) and a valid mainnet address.
  assert 'Add a payout address' in a.get(base+'/faucet/').text
  assert post(a,'address',{'csrf':csrf(a),'address':ADDR[0][:-1]+'L','code':totp(sec)}).status_code==400
  assert post(a,'address',{'csrf':csrf(a),'address':ADDR[0],'code':totp(sec,-1)}).status_code==400  # step already used
  assert post(a,'address',{'csrf':csrf(a),'address':ADDR[0],'code':totp(sec)}).status_code==303
  assert post(a,'address',{'csrf':csrf(a),'address':ADDR[1],'code':totp(sec)}).status_code==400  # same code again
  # CSRF and origin protection.
  assert post(a,'claim',{'cf-turnstile-response':'good'}).status_code==403
  assert post(a,'claim',{'csrf':csrf(a),'cf-turnstile-response':'good'},headers={'Origin':'https://evil.example'}).status_code==403
  # Turnstile tokens must match the form, our hostname, and be fresh.
  assert post(a,'claim',{'csrf':csrf(a),'cf-turnstile-response':f'good{secrets.token_hex(6)}:login'}).status_code==400
  assert post(a,'claim',{'csrf':csrf(a),'cf-turnstile-response':f'goodhost{secrets.token_hex(6)}:claim'}).status_code==400
  used=f'good{secrets.token_hex(6)}:login';assert post(requests.Session(),'login',{'email':'alice@example.org','password':PW,'code':totp(sec,1),'cf-turnstile-response':used}).status_code==303
  assert post(requests.Session(),'login',{'email':'alice@example.org','password':PW,'cf-turnstile-response':used}).status_code==400
  # Claim: bot check, then once per 24 hours.
  assert post(a,'claim',{'csrf':csrf(a),'cf-turnstile-response':'bad'}).status_code==400
  assert post(a,'claim',{'csrf':csrf(a),'cf-turnstile-response':'good'}).status_code==303
  r=post(a,'claim',{'csrf':csrf(a),'cf-turnstile-response':'good'});assert r.status_code==429 and 'claim again after' in r.text
  # Address belongs to one account; budget caps the day.
  b,bsec=member('bob@example.org',None)
  assert post(b,'address',{'csrf':csrf(b),'address':ADDR[0],'code':totp(bsec)}).status_code==409
  assert post(b,'address',{'csrf':csrf(b),'address':ADDR[1],'code':totp(bsec,1)}).status_code==303  # the previous code was spent
  assert post(b,'claim',{'csrf':csrf(b),'cf-turnstile-response':'good'}).status_code==303
  c,_=member('carol@example.org',ADDR[2],1)
  assert post(c,'claim',{'csrf':csrf(c),'cf-turnstile-response':'good'}).status_code==303
  d,_=member('dave@example.org',ADDR[3],2)
  r=post(d,'claim',{'csrf':csrf(d),'cf-turnstile-response':'good'});assert r.status_code==429 and 'budget' in r.text
  # Per-network limit (budget raised so it is the limit that triggers).
  config(daily_cap_atomic=str(100*int(AMOUNT)),per_client_daily=3)
  r=post(d,'claim',{'csrf':csrf(d),'cf-turnstile-response':'good'});assert r.status_code==429 and 'network' in r.text
  config(daily_cap_atomic=str(100*int(AMOUNT)))
  # Worker interface: signatures, replay protection.
  def signed(payload,ts=None,nonce=None,secret=secret_hex):
   body=json.dumps(payload).encode();ts=ts or str(int(time.time()));nonce=nonce or secrets.token_hex(16)
   sig=hmac.new(secret.encode(),f'{ts}\n{nonce}\n'.encode()+body,hashlib.sha256).hexdigest()
   return requests.post(base+'/api/faucet/worker/',data=body,headers={'X-Faucet-Timestamp':ts,'X-Faucet-Nonce':nonce,'X-Faucet-Signature':sig})
  assert requests.post(base+'/api/faucet/worker/',json={'action':'lease'}).status_code==401
  assert signed({'action':'lease'},secret='0'*64).status_code==401
  assert signed({'action':'lease'},ts=str(int(time.time())-1000)).status_code==401
  n=secrets.token_hex(16);config(enabled=False)
  assert signed({'action':'lease'},nonce=n).json()=={'paused':True,'claims':[]}
  assert signed({'action':'lease'},nonce=n).status_code==409
  assert requests.get(base+'/api/faucet/').json()['status']=='paused'
  config(daily_cap_atomic=str(100*int(AMOUNT)))
  # The real worker pays the queue through the fake wallet and reports txids.
  wcfg=tmp/'worker.json';journal=tmp/'journal.jsonl'
  wcfg.write_text(json.dumps({'site_url':base,'worker_secret':secret_hex,'wallet_rpc':f'http://127.0.0.1:{wallet_server.server_port}/json_rpc','journal':str(journal),
   'amount_atomic':AMOUNT,'max_per_day_atomic':str(100*int(AMOUNT)),'reserve_atomic':'0','enable_payouts':True,'batch':10}))
  run=lambda *extra:subprocess.run([sys.executable,str(root/'utils/faucet/faucet_worker.py'),'--config',str(wcfg),'--once',*extra],capture_output=True,text=True,timeout=120)
  out=run();assert out.returncode==0 and 'dry run' in out.stdout and not wallet['sent'],out.stdout+out.stderr
  out=run('--enable-payouts');assert out.returncode==0,out.stdout+out.stderr
  assert sorted(x[0] for x in wallet['sent'])==sorted(ADDR[:3]) and all(x[1]==int(AMOUNT) for x in wallet['sent'])
  con=sqlite3.connect(db);rows=con.execute('SELECT status,txid FROM claims').fetchall()
  assert len(rows)==3 and all(s=='paid' and len(t)==64 for s,t in rows),rows
  assert wallet['sent'][0][2][:16] in a.get(base+'/faucet/').text or any(x[2][:16] in a.get(base+'/faucet/').text for x in wallet['sent'])
  # Nothing pending: a second run pays nothing more.
  run('--enable-payouts');assert len(wallet['sent'])==3
  # Locked change: claims stay queued (no lease, no halt) until the balance unlocks; one claim per cycle by default.
  assert post(d,'claim',{'csrf':csrf(d),'cf-turnstile-response':'good'}).status_code==303
  wallet['locked']=wallet['balance']-int(AMOUNT)//2
  out=run('--enable-payouts');assert out.returncode==0 and 'stay queued' in out.stdout,out.stdout+out.stderr
  assert len(wallet['sent'])==3 and con.execute("SELECT status FROM claims WHERE address=?",(ADDR[3],)).fetchone()[0]=='pending'
  wallet['locked']=0;cfg1=json.loads(wcfg.read_text());cfg1.pop('batch');wcfg.write_text(json.dumps(cfg1))
  out=run('--enable-payouts');assert out.returncode==0 and len(wallet['sent'])==4,out.stdout+out.stderr
  assert con.execute("SELECT status FROM claims WHERE address=?",(ADDR[3],)).fetchone()[0]=='paid'
  # Balance really too low: halt before leasing anything.
  saved=wallet['balance'];wallet['balance']=int(AMOUNT)//2;out=run('--enable-payouts');assert out.returncode==2 and 'refill' in out.stdout,out.stdout
  wallet['balance']=saved
  # Uncertain send: the worker halts, keeps the journal entry and refuses to continue.
  e,_=member('erin@example.org',ADDR[4],3)
  assert post(e,'claim',{'csrf':csrf(e),'cf-turnstile-response':'good'}).status_code==303
  wallet['mode']='drop';out=run('--enable-payouts');assert out.returncode==2 and 'HALT' in out.stdout,out.stdout
  wallet['mode']='ok';out=run('--enable-payouts');assert out.returncode==2 and 'no recorded result' in out.stdout
  assert len(wallet['sent'])==4 and con.execute("SELECT status FROM claims WHERE address=?",(ADDR[4],)).fetchone()[0]=='processing'
  # Login throttling, password reset with TOTP.
  for _ in range(5):assert post(requests.Session(),'login',{'email':'bob@example.org','password':'wrong password!!','cf-turnstile-response':'good'}).status_code==401
  assert post(requests.Session(),'login',{'email':'bob@example.org','password':PW,'cf-turnstile-response':'good'}).status_code==429
  assert post(requests.Session(),'forgot',{'email':'carol@example.org','cf-turnstile-response':'good'}).status_code==303
  token=re.search(r'\?reset=([A-Za-z0-9_-]{43})',mails('carol@example.org')[-1]['body']).group(1)
  carol_secret=con.execute("SELECT totp_secret FROM members WHERE email='carol@example.org'").fetchone()[0]
  NEW='another long passphrase here'
  assert post(requests.Session(),'reset',{'token':token,'password':NEW,'confirm':NEW,'code':'000000'}).status_code==400
  assert post(requests.Session(),'reset',{'token':token,'password':NEW,'confirm':NEW,'code':totp(carol_secret,1)}).status_code==303
  assert post(requests.Session(),'reset',{'token':token,'password':NEW,'confirm':NEW,'code':totp(carol_secret)}).status_code==400
  # Stored data: argon2id hashes, append-only events, no passwords in mail.
  assert all(h.startswith('$argon2id$') for (h,) in con.execute('SELECT password_hash FROM members'))
  for sql in ['UPDATE events SET action="x"','DELETE FROM events']:
   try:con.execute(sql);raise AssertionError('events modified')
   except sqlite3.DatabaseError as err:assert 'append-only' in str(err)
  assert not any(PW in l for l in mail.read_text().splitlines())
 finally:server.terminate();server.wait(timeout=10);turnstile.shutdown();wallet_server.shutdown()
print('Faucet: sign-up/verify/mandatory TOTP, Turnstile, address rules, 24h/address/network/budget limits, CSRF, signed worker API, real worker payouts, halt on uncertainty, throttling, reset passed')
