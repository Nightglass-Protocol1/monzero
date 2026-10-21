"""Fund page goals and spending from fund/goals.json and fund/spending.json: goals replace the built-in
ones and fill in order from the live donation total, closed goals are hidden, spending rows with
receipts, invalid files fall back to the built-in goals, and the homepage summary uses the targets."""
import json,shutil,socket,subprocess,time
from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[2]
goals={'schema':'monzero-fund-goals-v1','updated_at':'2026-10-20','records':[
 {'id':'listing','title':'Listing on Exchange X','description':'First paragraph.\nSecond paragraph.','target_usd':'1000','status':'open'},
 {'id':'old','title':'Closed goal','description':'Hidden.','target_usd':'50','status':'closed'},
 {'id':'bounties','title':'Bug bounties','description':'Rewards.','target_usd':'3000','status':'open'}]}
spending={'schema':'monzero-fund-spending-v1','updated_at':'2026-10-20','records':[
 {'id':'fee','date':'2026-10-19','goal':'listing','description':'Listing fee','paid_to':'Exchange X','amount':'900','currency':'USDT','amount_usd':'900.00','evidence_url':'https://example.org/receipt'},
 {'id':'dns','date':'2026-10-10','goal':'general','description':'Domain','paid_to':'IONOS','amount':'20','currency':'USD','amount_usd':'20.00','evidence_url':None}]}
donations={'updatedAt':int(time.time()),'pricesUsd':{'btc':50000},'coins':[{'id':'btc','name':'Bitcoin','symbol':'BTC','address':'bc1pzsjv3e7mcst6khqr3msq85wlq67hnh48yjrm6eepycvze4htazyqyruvng','decimals':8,'received':'3000000','balance':'3000000','transactions':2,'current':True,'addressUrl':'https://mempool.space/address/x','txUrl':'https://mempool.space/tx/'}],'recent':[]}
# Match the complete endpoint contract; missing currencies must not become a total.
donations['schema']='monzero-donations-v1'
donations['pricedAt']=int(time.time())
donations['coins'][0]['fetchedAt']=int(time.time())
addresses={'ltc':'ltc1qjsmmr8f92pt3k8ztmvg8tc0veu08whc8pklm5x','bch':'qq0je5u6qfkx56e9pl3y6mw26ma4qnwvav9evttxpe','doge':'DQGNxF1SEyh9cXH11mgns749frKwq7Xo1e','eth':'0xD0Eb7C50Db766c897B085A492387135123f0A6b9','usdt-sol':'5LpU8TxNqWvs5ACyhxCXNVFXNMq6mnvvK1YvMGkBWXog'}
for ident,decimals in [('ltc',8),('bch',8),('doge',8),('eth',18),('usdt-sol',6)]:
 donations['pricesUsd'][ident]=1
 donations['coins'].append({'id':ident,'name':ident,'symbol':ident.upper(),'address':addresses[ident],'decimals':decimals,'received':'0','balance':'0','transactions':0,'current':True,'fetchedAt':int(time.time()),'addressUrl':'https://example.org','txUrl':'https://example.org/'})
with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
server=subprocess.Popen(['php','-S',f'127.0.0.1:{port}','-t',str(root/'website')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
try:
 for _ in range(50):
  try:
   with socket.create_connection(('127.0.0.1',port),timeout=.2):break
  except OSError:time.sleep(.1)
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True,executable_path=shutil.which('chromium'))
  def open_page(path,g=goals,sp=spending,width=1280):
   page=browser.new_page(viewport={'width':width,'height':900});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
   def route(r):
    u=r.request.url
    for key,body in [('/fund/goals.json',g),('/fund/spending.json',sp),('/api/donations/',donations)]:
     if key in u:return r.fulfill(status=200 if body is not None else 404,content_type='application/json',body=json.dumps(body) if body is not None else '')
    if '.php' in u or '/api/' in u or not u.startswith(f'http://127.0.0.1:{port}/'):return r.fulfill(status=503,body='{}')
    r.continue_()
   page.route('**/*',route);page.goto(f'http://127.0.0.1:{port}'+path);page.wait_for_timeout(1500);return page,errors
  page,errors=open_page('/fund/')
  items=page.locator('ol.goals > li');assert items.count()==2,items.count()  # closed goal hidden
  assert items.nth(0).locator('h3').inner_text()=='1. Listing on Exchange X' and items.nth(0).locator('p').count()==2 and 'Target: $1,000' in items.nth(0).inner_text()
  # $1,500 received: the first goal is full, $500 goes to the second.
  assert 'goal reached' in items.nth(0).locator('.goal-percent').inner_text() and items.nth(1).locator('.goal-raised').inner_text()=='$500',items.nth(1).inner_text()
  assert page.locator('#overall-target').inner_text()=='$4,000' and page.locator('#goals-heading').inner_text().startswith('Two goals')
  rows=page.locator('#spending-rows tr');assert page.locator('#spending').is_visible() and rows.count()==2
  assert 'Listing on Exchange X' in rows.nth(0).inner_text() and rows.nth(0).locator('a').get_attribute('href')=='https://example.org/receipt' and 'Under $100' in rows.nth(1).inner_text()
  assert not errors,errors;page.close()
  bad=json.loads(json.dumps(goals));bad['records'][0]['target_usd']=1000  # number, not string: invalid file
  page,errors=open_page('/fund/',g=bad,sp=None)
  assert 'Biconomy' in page.locator('ol.goals').inner_text() and page.locator('#spending').is_hidden() and not errors;page.close()
  page,errors=open_page('/',width=390)
  assert page.locator('#support-goal-name').inner_text()=='Listing on Exchange X' and page.locator('#support-goal-target').inner_text()=='US$1,000'
  assert page.locator('#support-remaining').inner_text()=='US$0' and page.locator('#support-raised').inner_text()=='US$1,500' and not errors,errors;page.close()
  browser.close()
finally:server.terminate();server.wait(timeout=5)
print('Fund goals: data-driven goals in order, closed hidden, live fill, spending with receipts, invalid fallback, homepage targets passed')
