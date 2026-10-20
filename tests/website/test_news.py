"""Crypto news: feed parsing (RSS/Atom), sponsored/filler/press-release/http/stale/future/entity
filtering, tracking removal, cross-outlet ranking, a failing outlet, signed ingest (signature, replay,
validation, ordering, 30-day archive), the /news/ page with archive days, and the homepage strip."""
import gzip,hashlib,hmac,http.server,json,os,secrets,shutil,socket,subprocess,sys,tempfile,threading,time
from email.utils import formatdate
from pathlib import Path
import requests
root=Path(__file__).resolve().parents[2];site=root/'website'
sys.path.insert(0,str(root/'utils/news'));import news_collector as nc
now=int(time.time());rfc=lambda t:formatdate(t,usegmt=True);iso=lambda t:time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(t))
def rss(items):return ('<?xml version="1.0"?><rss version="2.0"><channel><title>x</title>'+''.join(f'<item><title>{t}</title><link>{l}</link><pubDate>{rfc(at)}</pubDate>'+''.join(f'<category>{c}</category>' for c in cats)+'</item>' for t,l,at,cats in items)+'</channel></rss>').encode()
feeds={
 'a':rss([('BlackRock files for a new Bitcoin ETF with downside protection','https://a.example/etf?utm_source=rss&amp;id=1',now-600,[]),
          ('Sponsored: the best wallet of 2026','https://a.example/s',now-600,[]),
          ('Exchange token surges after listing news','https://a.example/press-release/x',now-700,[]),
          ('XRP price prediction: could rally 5x this month','https://a.example/p',now-800,[]),
          ('Old story about miners from last week','https://a.example/old',now-3*86400,[]),
          ('Story from the future that cannot be right','https://a.example/f',now+7200,[]),
          ('Plain http link story should be dropped','http://a.example/h',now-100,[]),
          ('Partner piece on yields','https://a.example/y',now-100,['Press Release'])]),
 'b':('<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><title>b</title>'
      f'<entry><title>BlackRock Files for Bitcoin ETF Offering Downside Protection</title><link rel="alternate" href="https://b.example/1"/><published>{iso(now-900)}</published></entry>'
      f'<entry><title>Visa and Mesh bring crypto spending to 175 million merchants</title><link href="https://b.example/2"/><updated>{iso(now-1200)}</updated></entry></feed>').encode(),
 'c':rss([('BlackRock files for Bitcoin ETF that trades gains for downside protection','https://c.example/1',now-1000,[]),
          ('BlackRock bitcoin ETF filing again: downside protection explained','https://c.example/2',now-1100,[]),
          ('Visa, Mesh partner to enable crypto spending at 175M merchants','https://c.example/3',now-1300,[])]),
 'evil':b'<?xml version="1.0"?><!DOCTYPE r [<!ENTITY a "aaaa">]><rss><channel><item><title>&a;&a;</title></item></channel></rss>',
}
class Feeds(http.server.BaseHTTPRequestHandler):
 def do_GET(self):
  key=self.path.strip('/')
  if key not in feeds:self.send_response(500);self.end_headers();return
  self.send_response(200);self.end_headers();self.wfile.write(feeds[key])
 def log_message(self,*a):pass
fs=http.server.ThreadingHTTPServer(('127.0.0.1',0),Feeds);threading.Thread(target=fs.serve_forever,daemon=True).start()
F=lambda name,key:{'name':name,'home':f'https://{key}.example/','feed':f'http://127.0.0.1:{fs.server_port}/{key}','region':'Global'}
config=[F('Alpha','a'),F('Beta','b'),F('Gamma','c'),F('Evil','evil'),F('Down','missing')]
items,report=nc.collect(config,now)
assert report['Alpha']==1 and report['Beta']==2 and report['Gamma']==3 and isinstance(report['Evil'],str) and isinstance(report['Down'],str),report
alpha=[i for i in items if i['source']=='Alpha'];assert alpha[0]['url']=='https://a.example/etf?id=1'  # tracking parameter removed
payload=nc.build(config,items,report,now)
top=payload['stories'][0];assert top['outlets']==3 and top['source']=='Alpha' and {a['source'] for a in top['also']}=={'Beta','Gamma'},top  # Gamma's second ETF post does not count twice
assert payload['stories'][1]['outlets']==2 and 'Visa' in payload['stories'][1]['title']
assert [s['ok'] for s in payload['sources']]==[True,True,True,False,False]
assert not any(w in json.dumps(payload) for w in ['Sponsored','press-release','prediction','Old story','future','http://a.example','Partner'])

with tempfile.TemporaryDirectory() as tmp:
 tmp=Path(tmp);private=tmp/'private';private.mkdir();data=tmp/'data';secret=secrets.token_hex(32)
 (private/'news-config.php').write_text(f"<?php return ['secret' => '{secret}'];\n")
 with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
 base=f'http://127.0.0.1:{port}'
 env={**os.environ,'MONZERO_PRIVATE_DIR':str(private),'MONZERO_NEWS_DATA_DIR':str(data)}
 server=subprocess.Popen(['php','-S',f'127.0.0.1:{port}','-t',str(site)],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 def raw(body,key=secret,nonce=None,ts=None):
  ts=str(ts or int(time.time()));nonce=nonce or secrets.token_hex(16)
  sig=hmac.new(key.encode(),f'{ts}\n{nonce}\n'.encode()+body,hashlib.sha256).hexdigest()
  return requests.post(base+'/api/news/',data=body,headers={'X-News-Timestamp':ts,'X-News-Nonce':nonce,'X-News-Signature':sig})
 pack=lambda p:gzip.compress(json.dumps(p).encode())
 try:
  for _ in range(100):
   try:
    with socket.create_connection(('127.0.0.1',port),timeout=.2):break
   except OSError:time.sleep(.1)
  assert requests.get(base+'/api/news/').status_code==405
  assert raw(pack(payload),key=secrets.token_hex(32)).status_code==401
  data.mkdir();old=time.strftime('%Y-%m-%d',time.gmtime(now-40*86400));(data/f'{old}.json').write_text('{}');yesterday=time.strftime('%Y-%m-%d',time.gmtime(now-86400))
  (data/f'{yesterday}.json').write_text(json.dumps({**payload,'date':yesterday,'generated_at':now-86400}))
  code,reply=nc.upload(base,secret,payload);assert code==200 and reply['stories']==len(payload['stories']),(code,reply)
  assert json.loads((data/'latest.json').read_text())==payload and (data/f"{payload['date']}.json").exists() and not (data/f'{old}.json').exists()
  assert json.loads((data/'index.json').read_text())['days']==[payload['date'],yesterday]
  n=secrets.token_hex(16);later={**payload,'generated_at':now+1}
  assert raw(pack(later),nonce=n).status_code==200 and raw(pack({**later,'generated_at':now+2}),nonce=n).status_code==409
  assert raw(pack(payload)).status_code==409  # older than published
  for bad in [{**later,'generated_at':now+3,'stories':[{**later['stories'][0],'url':'http://x.example/'}]},
              {**later,'generated_at':now+3,'stories':[{**later['stories'][0],'source':'Unknown'}]},
              {**later,'generated_at':now+3,'stories':[{**later['stories'][0],'title':'<script> x'}]},
              {**later,'generated_at':now+3,'extra':1}]:
   assert raw(pack(bad)).status_code==400,bad
  assert raw(b'not gzip').status_code==400
  # Page and homepage strip.
  from playwright.sync_api import sync_playwright
  with sync_playwright() as p:
   browser=p.chromium.launch(headless=True,executable_path=shutil.which('chromium'))
   for width in (390,1440):
    pg=browser.new_page(viewport={'width':width,'height':900});errors=[];pg.on('pageerror',lambda e:errors.append(str(e)))
    pg.route('**/news/data/*',lambda r:r.fulfill(status=200,content_type='application/json',body=(data/r.request.url.split('/news/data/')[1].split('?')[0]).read_text()))
    pg.goto(base+'/news/');pg.wait_for_selector('#stories li')
    first=pg.locator('#stories li').first;assert 'BlackRock' in first.inner_text() and '3 outlets' in first.inner_text() and 'Also covered by Beta, Gamma' in first.inner_text()
    assert first.locator('a.headline').get_attribute('rel')=='noopener noreferrer nofollow' and first.locator('a.headline').get_attribute('href')=='https://a.example/etf?id=1'
    assert 'not reachable' in pg.locator('#sources').inner_text() and pg.locator('#day option').count()==2
    pg.select_option('#day',yesterday);pg.wait_for_selector(f'#news-title:has-text("{yesterday}")')
    assert pg.evaluate('document.documentElement.scrollWidth <= innerWidth') and not errors,errors;pg.close()
   pg=browser.new_page();pg.route('**/news/data/latest.json*',lambda r:r.fulfill(status=200,content_type='application/json',body=(data/'latest.json').read_text()))
   pg.route('**/*.php*',lambda r:r.fulfill(status=503,body='{}'));pg.goto(base+'/');pg.wait_for_selector('#news-strip:not([hidden])')
   assert pg.locator('#news-strip-list li').count()==min(5,len(payload['stories'])) and 'BlackRock' in pg.locator('#news-strip-list').inner_text();pg.close()
   browser.close()
 finally:server.terminate();server.wait(timeout=5);fs.shutdown()
print('News: RSS/Atom parsing, sponsored/filler/press/http/stale/future/entity filtering, ranking, failing outlets, signed ingest, archive, page, homepage strip passed')
