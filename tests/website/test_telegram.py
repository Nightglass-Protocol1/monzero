"""Telegram miner alerts against fake Telegram and pool APIs: webhook secret, commands and limits,
private chats only, drop/recovery/offline/online/payout alerts, silence when the pool is down,
rate limit, blocked chats forgotten, /stop all, check-ins driving checks, dashboard card."""
import hashlib,hmac,http.server,json,os,secrets,shutil,socket,sqlite3,subprocess,sys,tempfile,threading,time,urllib.parse
from pathlib import Path
import requests
root=Path(__file__).resolve().parents[2];site=root/'website'
ADDR=['FWPbFrwvRqpWTMDJAAeT3wAGsCUvERHyEAZJySDBDTKJJxr4q9gNStxSZghEAmtgvd49oySaDP9WGV1KVDeDXFBfM748KwK']
sent=[];blocked=set();calls=[];feed_fail=[False];feed_drop=[False]
class Telegram(http.server.BaseHTTPRequestHandler):
 def do_POST(self):
  body=json.loads(self.rfile.read(int(self.headers['Content-Length'])) or b'{}')
  calls.append((self.path.rsplit('/',1)[1],body))
  if self.path.endswith('/sendMessage') and body['chat_id']=='@MonzeroOfficial' and feed_drop[0]:
   sent.append((body['chat_id'],body['text']));self.connection.close();return  # delivered, but the reply is lost
  if self.path.endswith('/sendMessage'):
   if body['chat_id'] in blocked:r={'ok':False,'error_code':403,'description':'Forbidden: bot was blocked by the user'}
   elif body['chat_id']=='@MonzeroOfficial' and feed_fail[0]:r={'ok':False,'error_code':400,'description':'Bad Request: not enough rights to send text messages to the chat'}
   else:sent.append((body['chat_id'],body['text']));r={'ok':True,'result':{'message_id':len(sent)}}
  else:r={'ok':True}
  b=json.dumps(r).encode();self.send_response(200);self.end_headers();self.wfile.write(b)
 def log_message(self,*a):pass
pool={'up':True,'hashrate':1000,'payments':[{'timestamp':1,'txid':'a'*64,'amount':50000000000}],'total':2264,'height':13084}
class Pool(http.server.BaseHTTPRequestHandler):
 def do_GET(self):
  if not pool['up']:self.send_response(503);self.end_headers();return
  if self.path.startswith('/api/stats'):
   b=json.dumps({'pool':{'hashrate':374578.0,'miners':10,'totalBlocks':pool['total'],'blocks':[{'height':pool['height'],'finder':'FRZiwpLV…XRwR','reward':1}]}}).encode()
   self.send_response(200);self.end_headers();self.wfile.write(b);return
  address=urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)['address'][0]
  b=json.dumps({'address':address,'hashrate':pool['hashrate'],'pending':0,'paid':0,'workers':[],'payments':pool['payments']}).encode()
  self.send_response(200);self.end_headers();self.wfile.write(b)
 def log_message(self,*a):pass
def serve(h):s=http.server.ThreadingHTTPServer(('127.0.0.1',0),h);threading.Thread(target=s.serve_forever,daemon=True).start();return s
tg,pl=serve(Telegram),serve(Pool)

with tempfile.TemporaryDirectory() as tmp:
 tmp=Path(tmp);private=tmp/'private';private.mkdir()
 hook=secrets.token_hex(32);status_secret=secrets.token_hex(32)
 env={**os.environ,'MONZERO_PRIVATE_DIR':str(private)}
 with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
 base=f'http://127.0.0.1:{port}'
 server=subprocess.Popen(['php','-d','opcache.enable=0','-S',f'127.0.0.1:{port}','-t',str(site)],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 def say(chat,text,kind='private',secret=None):
  update={'update_id':1,'message':{'message_id':1,'chat':{'id':chat,'type':kind},'text':text}}
  return requests.post(base+'/api/telegram/',json=update,headers={'X-Telegram-Bot-Api-Secret-Token':secret or hook})
 def last(chat):return [t for c,t in sent if c==chat][-1]
 def check(force=True):
  out=subprocess.run(['php','-r',f'require "{site}/lib/telegram.php"; echo tgCheckAll(time(), {"true" if force else "false"});'],env=env,capture_output=True,text=True,timeout=60)
  assert out.returncode==0,out.stderr;return int(out.stdout or 0)
 try:
  for _ in range(100):
   try:
    with socket.create_connection(('127.0.0.1',port),timeout=.2):break
   except OSError:time.sleep(.1)
  assert requests.get(base+'/api/telegram/').json()=={'enabled':False,'username':None}
  assert say(1,'/start').status_code==503
  (private/'telegram-config.php').write_text(f"<?php return ['bot_token' => '123456:{'A'*35}', 'webhook_secret' => '{hook}', 'bot_username' => 'MonzeroAlertsBot', 'api' => 'http://127.0.0.1:{tg.server_port}', 'pool_api' => 'http://127.0.0.1:{pl.server_port}/api/miner'];\n")
  assert requests.get(base+'/api/telegram/').json()=={'enabled':True,'username':'MonzeroAlertsBot'}
  assert say(1,'/start',secret='wrong').status_code==401 and not sent
  assert say(1,'/start').status_code==200 and '/watch ADDRESS' in last(1)
  say(2,'/watch '+ADDR[0],kind='group');assert not any(c==2 for c,_ in sent)  # group chats are ignored
  say(1,'/watch notanaddress');assert 'Monzero' in last(1) or 'characters' in last(1)
  say(1,'/watch '+ADDR[0]+' rig one');assert 'Watching rig one' in last(1)
  say(1,'/list');assert 'rig one' in last(1)
  say(1,'/drop 5');assert 'from 10 to 90' in last(1)
  say(1,'/drop 60');assert '60%' in last(1)
  db=sqlite3.connect(private/'telegram.sqlite')
  for i in range(4):db.execute("INSERT INTO watches (chat_id,address,name,created_at) VALUES (1,?,?,0)",(f'X{i}',f'x{i}'))
  db.commit();say(1,'/watch '+ADDR[0]);assert 'Watching' in last(1)  # re-watching the same address is allowed at the limit
  db.execute("DELETE FROM watches WHERE address LIKE 'X%'");db.commit()
  # Alerts: first check only records; three samples build the usual rate; then drop, recovery, payout.
  n=len(sent);assert check()==0 and len(sent)==n
  check();check()
  pool['hashrate']=300;assert check()==1 and 'dropped to 300' in last(1)
  assert check()==0  # alerted once
  pool['hashrate']=1000;assert check()==1 and 'recovered' in last(1)
  pool['payments']=[{'timestamp':2,'txid':'b'*64,'amount':125000000000}]+pool['payments'];k=check();assert k==1 and 'Payout to rig one: 1.25 XMZ' in last(1),(k,sent[-3:])
  # Offline after the chosen minutes, then online again.
  pool['hashrate']=0;assert check()==0
  state=json.loads(db.execute('SELECT state FROM watches').fetchone()[0]);state['online_at']=int(time.time())-1800
  db.execute('UPDATE watches SET state=?',(json.dumps(state),));db.commit()
  assert check()==1 and 'no hashrate on the pool for 30 minutes' in last(1)
  pool['hashrate']=900;assert check()==1 and 'mining again' in last(1)
  # Pool unreachable: silence. Rate limit without force.
  pool['up']=False;assert check()==0;pool['up']=True
  assert check(force=False)==0
  # Check-ins from the nodes drive the checks.
  (private/'status-config.php').write_text(f"<?php return ['secret' => '{status_secret}', 'node_rpc' => 'http://127.0.0.1:9', 'pool_url' => 'http://127.0.0.1:9/'];\n")
  db.execute("UPDATE meta SET value='0' WHERE key='checked_at'");db.commit()
  body=json.dumps({'node':'eu'}).encode();ts=str(int(time.time()));nonce=secrets.token_hex(16)
  sig=hmac.new(status_secret.encode(),f'{ts}\n{nonce}\n'.encode()+body,hashlib.sha256).hexdigest()
  r=requests.post(base+'/api/status/',data=body,headers={'X-Status-Timestamp':ts,'X-Status-Nonce':nonce,'X-Status-Signature':sig},timeout=60);assert r.status_code==200,r.text
  assert int(db.execute("SELECT value FROM meta WHERE key='checked_at'").fetchone()[0])>=int(ts)
  # Group feed: pool update every N hours (first run records), announcements from admin with pinning.
  cfg=(private/'telegram-config.php').read_text().replace("];\n",f", 'feed_chat' => '@MonzeroOfficial', 'feed_pool_hours' => 24, 'pool_stats' => 'http://127.0.0.1:{pl.server_port}/api/stats'];\n")
  (private/'telegram-config.php').write_text(cfg)
  feed=lambda:[t for c,t in sent if c=='@MonzeroOfficial']
  db.execute("DELETE FROM meta WHERE key='feed_pool'");db.commit();check();assert not feed()  # baseline only
  db.execute("UPDATE meta SET value=? WHERE key='feed_pool'",(json.dumps({'at':int(time.time())-25*3600,'total':2200,'height':13000}),));db.commit()
  check();post=feed()[-1];assert 'Blocks found in the last 25 hours: 64 (heights 13,001–13,084)' in post and '374.6 kH/s from 10 miners' in post,post
  assert 'FRZiwpLV' not in post and 't.me/MonzeroAlertsBot' in post
  check();assert len(feed())==1  # next update only after 24 hours
  mail=tmp/'mail.jsonl';env2={**env,'MONZERO_ADMIN_DB':str(private/'admin.sqlite'),'MONZERO_ADMIN_MAIL_LOG':str(mail),'MONZERO_ADMIN_BASE_URL':base,'MONZERO_CONTENT_ROOT':str(tmp/'content')}
  (tmp/'content/community').mkdir(parents=True)
  assert subprocess.run(['php',str(site/'admin/bootstrap.php'),'security@monzero.org'],env=env2,capture_output=True).returncode==0
  server.terminate();server.wait(timeout=5)
  server=subprocess.Popen(['php','-d','opcache.enable=0','-S',f'127.0.0.1:{port}','-t',str(site)],env=env2,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  for _ in range(100):
   try:
    with socket.create_connection(('127.0.0.1',port),timeout=.2):break
   except OSError:time.sleep(.1)
  import re
  token=re.search(r'\?setup=([A-Za-z0-9_-]{43})',json.loads(mail.read_text().splitlines()[-1])['body']).group(1)
  owner=requests.Session();assert owner.post(base+'/admin/?do=setup',data={'token':token,'password':'correct horse battery staple','confirm':'correct horse battery staple'},allow_redirects=False).status_code==303
  sys.path.insert(0,str(Path(__file__).resolve().parent));from admin_mfa import enroll;enroll(owner,base)
  page=owner.get(base+'/admin/?view=content&kind=announcements').text;assert 'Also post to the Telegram group' in page and '@MonzeroOfficial' in page
  fields=lambda:{k:re.search(rf'name="{k}" value="([^"]*)"',owner.get(base+'/admin/?view=content&kind=announcements').text).group(1) for k in ['csrf','version']}
  r=owner.post(base+'/admin/?do=post-add',data={**fields(),'kind':'announcements','title':'Hello group','body':'First line.\nSecond line.','url':'/faucet/','telegram':'1'},allow_redirects=False)
  assert r.status_code==303 and 'content-saved-telegram' in r.headers['Location'],r.headers
  msg=feed()[-1];assert msg.startswith('📢 Hello group') and 'Second line.' in msg and 'https://monzero.org/faucet/' in msg,msg
  assert calls[-1][0]=='pinChatMessage' and calls[-1][1]['chat_id']=='@MonzeroOfficial'
  r=owner.post(base+'/admin/?do=post-add',data={**fields(),'kind':'announcements','title':'Website only','body':'Not for Telegram.','url':''},allow_redirects=False)
  assert 'content-saved' in r.headers['Location'] and not any('Website only' in t for t in feed())
  pid=json.loads((tmp/'content/community/announcements.json').read_text())['records'][0]['id']
  r=owner.post(base+'/admin/?do=post-telegram',data={**fields(),'kind':'announcements','id':pid},allow_redirects=False);assert 'telegram-sent' in r.headers['Location'] and 'Website only' in feed()[-1]
  n=len(feed());r=owner.post(base+'/admin/?do=post-telegram',data={**fields(),'kind':'announcements','id':pid},allow_redirects=False)
  assert 'telegram-already' in r.headers['Location'] and len(feed())==n  # never twice
  assert owner.post(base+'/admin/?do=post-add',data={**fields(),'kind':'announcements','title':'Second post','body':'Later.','url':''},allow_redirects=False).status_code==303
  pid2=json.loads((tmp/'content/community/announcements.json').read_text())['records'][0]['id']
  feed_fail[0]=True
  r=owner.post(base+'/admin/?do=post-telegram',data={**fields(),'kind':'announcements','id':pid2},allow_redirects=False);assert 'telegram-failed' in r.headers['Location']
  assert 'not enough rights' in owner.get(base+'/admin/?view=content&kind=announcements').text
  feed_fail[0]=False
  r=owner.post(base+'/admin/?do=post-telegram',data={**fields(),'kind':'announcements','id':pid2},allow_redirects=False);assert 'telegram-sent' in r.headers['Location']  # a clear refusal may be retried
  # Major news to the group, never twice.
  def story(title,url,outlets,also=()):return {'title':title,'url':url,'source':'Alpha','published_at':int(time.time())-60,'outlets':outlets,'also':[{'source':'Beta','url':u} for u in also]}
  def news(*stories):
   out=subprocess.run(['php','-r',f'require "{site}/lib/telegram.php"; echo tgFeedNews(tgConfig(), json_decode(stream_get_contents(STDIN), true), time());'],input=json.dumps({'stories':list(stories)}),env=env,capture_output=True,text=True,timeout=60)
   assert out.returncode==0,out.stderr;return int(out.stdout)
  old=story('Old major story already on the page','https://a.example/old',6)
  k=news(old);assert k==0,('first run sent',k,feed()[-2:])  # first run only records
  assert news(old)==0
  etf=story('BlackRock files for a third Bitcoin ETF with downside protection','https://a.example/etf',5,['https://b.example/etf'])
  assert news(etf,story('Small story covered by few outlets','https://a.example/small',3))==1
  post=feed()[-1];assert post.startswith('📰 BlackRock files') and 'covered by 5 outlets' in post and 'https://a.example/etf' in post
  assert calls[-1][1]['disable_web_page_preview'] is False
  assert news(etf)==0 and news(story('Another headline about it','https://c.example/x',7,['https://b.example/etf']))==0  # same links
  assert news(story('BlackRock files for third Bitcoin ETF offering downside protection','https://d.example/new',8))==0  # same story, all-new links
  titles=['Visa launches stablecoin payouts for merchants','Kazakhstan court restricts six exchanges','Ethereum developers schedule Glamsterdam upgrade',
          'Hackers drain lending protocol on Arbitrum','Japan regulator approves yen stablecoin issuer']
  many=[story(t,f'https://a.example/m{i}',6) for i,t in enumerate(titles)]
  assert news(*many)==3 and news(*many)==2  # at most 3 per upload; the rest next time, none twice
  db.execute("UPDATE meta SET value=json_set(value,'$.count',12) WHERE key='feed_news'");db.commit()
  assert news(story('Fresh story over the daily limit','https://a.example/limit',9))==0
  db.execute("UPDATE meta SET value=json_set(value,'$.count',0) WHERE key='feed_news'");db.commit()
  feed_drop[0]=True;n=len(feed());assert news(story('Story whose reply is lost in transit','https://a.example/lost',6))==0;feed_drop[0]=False
  assert len(feed())==n+1 and news(story('Story whose reply is lost in transit','https://a.example/lost',6))==0 and len(feed())==n+1  # delivered once, not retried
  feed_fail[0]=True;assert news(story('Story Telegram refuses at first','https://a.example/refused',6))==0;feed_fail[0]=False
  assert news(story('Story Telegram refuses at first','https://a.example/refused',6))==1  # a clear refusal is retried
  # A chat that blocked the bot is forgotten; /stop all deletes everything.
  say(3,'/watch '+ADDR[0]);blocked.add(3);check()  # first check for chat 3 only records payments
  pool['payments']=[{'timestamp':3,'txid':'c'*64,'amount':1}]+pool['payments'];check()
  assert db.execute('SELECT COUNT(*) FROM chats WHERE chat_id=3').fetchone()[0]==0
  say(1,'/stop all');assert 'deleted' in last(1) and db.execute('SELECT COUNT(*) FROM watches').fetchone()[0]==0
  assert oct((private/'telegram.sqlite').stat().st_mode&0o777)=='0o600'
  assert requests.get(base+'/lib/telegram.php').status_code==404
  # Dashboard card appears only when the bot is configured.
  from playwright.sync_api import sync_playwright
  with sync_playwright() as p:
   browser=p.chromium.launch(headless=True,executable_path=shutil.which('chromium'))
   pg=browser.new_page();pg.route('**/*.php*',lambda r:r.fulfill(status=503,body='{}'));pg.goto(base+'/mining/dashboard/')
   pg.wait_for_selector('#telegram-alerts:not([hidden])');assert pg.locator('#telegram-link').get_attribute('href')=='https://t.me/MonzeroAlertsBot'
   pg.close();(private/'telegram-config.php').unlink()
   pg=browser.new_page();pg.goto(base+'/mining/dashboard/');pg.wait_for_timeout(800);assert pg.locator('#telegram-alerts').is_hidden();browser.close()
 finally:server.terminate();server.wait(timeout=5);tg.shutdown();pl.shutdown()
print('Telegram: webhook secret, commands, limits, private chats only, drop/recovery/offline/online/payout alerts, pool outage silence, rate limit, blocked chats, /stop all, check-in trigger, group feed (pool update, announcements once, major news once: links, similar headlines, lost replies, refusals, caps), dashboard card passed')
