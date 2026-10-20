"""Admin content editing: catalog record edit/add/remove with validation, stale-edit refusal, backups and
audit; announcements and roadmap updates; faucet panel with pause/resume; permission limits; escaping;
public pages rendering posts. Isolated content root, databases and mail log."""
import json,os,re,shutil,socket,sqlite3,subprocess,tempfile,time
from pathlib import Path
import requests
root=Path(__file__).resolve().parents[2];site=root/'website'
PASSWORD='correct horse battery staple';TODAY=time.strftime('%Y-%m-%d',time.gmtime())

with tempfile.TemporaryDirectory() as tmp:
 tmp=Path(tmp);content=tmp/'content';private=tmp/'private';private.mkdir()
 for rel in ['exchanges/catalog.json','ecosystem/catalog.json','community/bounties/catalog.json','mining/benchmarks/catalog.json']:
  (content/rel).parent.mkdir(parents=True,exist_ok=True);shutil.copy(site/rel,content/rel)
 (content/'roadmap').mkdir()
 (tmp/'faucet-config.php').write_text("<?php return ['enabled' => true, 'amount_atomic' => '10000000000', 'daily_cap_atomic' => '500000000000', 'turnstile_site_key' => 'k', 'turnstile_secret' => 's', 'worker_secret' => '"+'a'*64+"', 'base_url' => 'http://127.0.0.1'];\n")
 with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
 base=f'http://127.0.0.1:{port}';mail=tmp/'mail.jsonl'
 env={**os.environ,'MONZERO_ADMIN_DB':str(private/'admin.sqlite'),'MONZERO_ADMIN_MAIL_LOG':str(mail),'MONZERO_ADMIN_BASE_URL':base,'MONZERO_CONTENT_ROOT':str(content),
      'MONZERO_FAUCET_CONFIG':str(tmp/'faucet-config.php'),'MONZERO_FAUCET_DB':str(private/'faucet.sqlite'),'MONZERO_FAUCET_HEARTBEAT':str(private/'faucet-heartbeat.json')}
 def mails():return [json.loads(l) for l in mail.read_text().splitlines()] if mail.exists() else []
 assert subprocess.run(['php',str(site/'admin/bootstrap.php'),'security@monzero.org'],env=env,capture_output=True).returncode==0
 server=subprocess.Popen(['php','-S',f'127.0.0.1:{port}','-t',str(site)],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 try:
  for _ in range(100):
   try:
    with socket.create_connection(('127.0.0.1',port),timeout=.2):break
   except OSError:time.sleep(.1)
  def setup(email):
   s=requests.Session();token=re.search(r'\?setup=([A-Za-z0-9_-]{43})',[m for m in mails() if m['to']==email][-1]['body']).group(1)
   r=s.post(base+'/admin/?do=setup',data={'token':token,'password':PASSWORD,'confirm':PASSWORD},allow_redirects=False);assert r.status_code==303,r.text;return s
  def page(s,query):r=s.get(base+'/admin/'+query);return r
  def form(s,query,pattern):
   html=page(s,query).text;return {k:re.search(rf'name="{k}" value="([^"]*)"',html).group(1) for k in pattern}
  def post(s,do,data):return s.post(base+f'/admin/?do={do}',data=data,allow_redirects=False)
  owner=setup('security@monzero.org')
  home=page(owner,'').text
  for label in ['Announcements','Roadmap updates','Exchange listings','Ecosystem directory','Bounty board','CPU benchmarks','Faucet']:assert label in home,label
  # Edit a catalog record.
  listing=page(owner,'?view=content&kind=exchanges').text;assert 'Biconomy' in listing
  view=page(owner,'?view=content&kind=exchanges&record=biconomy').text
  record=json.loads(re.search(r'<textarea name="record"[^>]*>(.*?)</textarea>',view,re.S).group(1).replace('&quot;','"').replace('&amp;','&').replace('&lt;','<').replace('&gt;','>'))
  f=form(owner,'?view=content&kind=exchanges&record=biconomy',['csrf','version'])
  record['note']='Edited from the admin area <b>test</b>.';record['updated_at']=TODAY
  r=post(owner,'content-save',{**f,'kind':'exchanges','id':'biconomy','record':json.dumps(record)});assert r.status_code==303,r.text[:500]
  saved=json.loads((content/'exchanges/catalog.json').read_text());assert saved['records'][0]['note']==record['note'] and saved['updated_at']==TODAY
  assert len(list((private/'content-history/exchanges').glob('*.json')))==1
  assert '&lt;b&gt;test&lt;/b&gt;' in page(owner,'?view=content&kind=exchanges&record=biconomy').text  # escaped in the editor
  # Invalid save: refused with a specific message; file unchanged. Stale version: refused.
  before=(content/'exchanges/catalog.json').read_text()
  f=form(owner,'?view=content&kind=exchanges&record=biconomy',['csrf','version'])
  bad=dict(record,status='listed');r=post(owner,'content-save',{**f,'kind':'exchanges','id':'biconomy','record':json.dumps(bad)})
  assert r.status_code==400 and 'status must be one of' in r.text and (content/'exchanges/catalog.json').read_text()==before
  r=post(owner,'content-save',{**f,'kind':'exchanges','id':'biconomy','record':'{not json'});assert r.status_code==400 and 'JSON object' in r.text
  r=post(owner,'content-save',{**f,'version':'0'*64,'kind':'exchanges','id':'biconomy','record':json.dumps(record)});assert r.status_code==400 and 'Someone else changed' in r.text
  # Add then remove an ecosystem entry from the template.
  view=page(owner,'?view=content&kind=ecosystem&record=').text;assert 'new-entry' in view and TODAY in view
  f=form(owner,'?view=content&kind=ecosystem&record=',['csrf','version'])
  entry={'id':'test-wallet','name':'Test wallet','category':'Wallet applications','operator':'third-party','description':'A wallet.','url':'https://example.org/','verified_at':TODAY}
  assert post(owner,'content-save',{**f,'kind':'ecosystem','id':'','record':json.dumps(entry)}).status_code==303
  assert any(r['id']=='test-wallet' for r in json.loads((content/'ecosystem/catalog.json').read_text())['records'])
  f=form(owner,'?view=content&kind=ecosystem',['csrf','version'])
  assert post(owner,'content-delete',{**f,'kind':'ecosystem','id':'test-wallet'}).status_code==303
  assert not any(r['id']=='test-wallet' for r in json.loads((content/'ecosystem/catalog.json').read_text())['records'])
  # Announcements and roadmap updates.
  f=form(owner,'?view=content&kind=announcements',['csrf','version'])
  assert post(owner,'post-add',{**f,'kind':'announcements','title':'Faucet is open','body':'Claim 0.1 XMZ.\nOnce a day.','url':'/faucet/'}).status_code==303
  ann=json.loads((content/'community/announcements.json').read_text());assert ann['records'][0]['title']=='Faucet is open' and ann['records'][0]['id']==f'{TODAY}-faucet-is-open'
  f=form(owner,'?view=content&kind=announcements',['csrf','version'])
  r=post(owner,'post-add',{**f,'kind':'announcements','title':'Bad link','body':'x','url':'javascript:alert(1)'});assert r.status_code==400 and 'link' in r.text
  f=form(owner,'?view=content&kind=roadmap-updates',['csrf','version'])
  assert post(owner,'post-add',{**f,'kind':'roadmap-updates','title':'Node map live','body':'Country counts from two nodes.','url':''}).status_code==303
  assert json.loads((content/'roadmap/updates.json').read_text())['records'][0]['url'] is None
  # Faucet panel and pause/resume.
  panel=page(owner,'?view=faucet').text;assert 'Claims are <strong>open</strong>' in panel and 'No heartbeat' in panel
  f=form(owner,'?view=faucet',['csrf'])
  assert post(owner,'faucet-disable',f).status_code==303 and "'enabled' => false" in (tmp/'faucet-config.php').read_text()
  assert 'Claims are <strong>paused</strong>' in page(owner,'?view=faucet').text
  assert post(owner,'faucet-enable',f).status_code==303 and "'enabled' => true" in (tmp/'faucet-config.php').read_text()
  # Audit trail.
  actions=[a for (a,) in sqlite3.connect(private/'admin.sqlite').execute('SELECT action FROM audit')]
  for a in ['content.edited','content.added','content.deleted','content.post_added','faucet.paused','faucet.resumed']:assert a in actions,a
  # A limited admin: ecosystem only.
  f=form(owner,'?view=admins',['csrf'])
  assert post(owner,'invite',{**f,'email':'eco@example.org','permissions[]':['ecosystem']}).status_code==303
  eco=setup('eco@example.org')
  assert page(eco,'?view=content&kind=ecosystem').status_code==200
  for q in ['?view=content&kind=exchanges','?view=faucet','?view=content&kind=announcements']:assert page(eco,q).status_code==403,q
  f=form(eco,'?view=content&kind=ecosystem',['csrf','version'])
  assert post(eco,'faucet-disable',f).status_code==403 and post(eco,'content-delete',{**f,'kind':'exchanges','id':'biconomy'}).status_code==403
  # Unauthenticated requests go to sign-in, and internals are not served.
  assert 'Sign in' in requests.get(base+'/admin/?view=content&kind=exchanges').text
  assert requests.get(base+'/admin/content.php').status_code==404 and requests.get(base+'/lib/catalogs.php').status_code==404

  # Public pages render the posts (served from the isolated content root).
  from playwright.sync_api import sync_playwright
  with sync_playwright() as p:
   browser=p.chromium.launch(headless=True,executable_path=shutil.which('chromium'))
   for path,section,file in [('/community/','#announcements','community/announcements.json'),('/roadmap/','#roadmap-updates','roadmap/updates.json')]:
    pg=browser.new_page();errors=[];pg.on('pageerror',lambda e:errors.append(str(e)))
    serve=lambda name:(lambda r:r.fulfill(status=200,content_type='application/json',body=(content/name).read_text()))
    pg.route('**/'+file+'*',serve(file))
    pg.goto(base+path);pg.wait_for_selector(section+' li')
    assert pg.locator(section).is_visible() and not errors,errors
    pg.close()
   pg=browser.new_page();pg.route('**/community/announcements.json*',lambda r:r.fulfill(status=404,body=''));pg.goto(base+'/community/');pg.wait_for_timeout(500)
   assert pg.locator('#announcements').is_hidden();pg.close()
   browser.close()
 finally:server.terminate();server.wait(timeout=5)
print('Admin content: catalog edit/add/remove with validation, stale edits refused, backups, audit, posts, faucet pause/resume, permissions, escaping, public posts passed')
