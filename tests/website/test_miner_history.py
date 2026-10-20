"""Leaderboard history: opt-in daily totals in the miner-stats ingest (uptime slots, positive block
increments, withdrawal deletes history, 30-day pruning), 7/30-day boards, and the page boards."""
import json,os,secrets,shutil,socket,subprocess,tempfile,time
from pathlib import Path
import requests
root=Path(__file__).resolve().parents[2]
with tempfile.TemporaryDirectory() as tmp:
 tmp=Path(tmp);stats=tmp/'stats.json';token=secrets.token_hex(16)
 env={**os.environ,'MONZERO_STATS_SECRET':secrets.token_hex(32),'MONZERO_STATS_INGEST_TOKEN':token,'MONZERO_STATS_FILE':str(stats)}
 with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
 base=f'http://127.0.0.1:{port}/api/miner-stats/'
 server=subprocess.Popen(['php','-S',f'127.0.0.1:{port}','-t',str(root/'website')],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 def report(iid,hashrate,blocks,history=None):
  body={'installation_id':iid,'hashrate':hashrate,'blocks_found':blocks}
  if history is not None:body['history']=history
  return requests.post(base,json=body,headers={'Authorization':f'Bearer {token}'})
 board=lambda w:requests.get(base+f'?board={w}').json()
 try:
  for _ in range(100):
   try:
    with socket.create_connection(('127.0.0.1',port),timeout=.2):break
   except OSError:time.sleep(.1)
  a,b='a'*32,'b'*32
  assert report(a,1000,0,history='yes').status_code==400
  for hr,blocks in [(1000,0),(1200,2),(800,1),(1000,3)]:assert report(a,hr,blocks,history=True).status_code==200  # reset 2->1 adds nothing
  assert report(b,5000,9).status_code==200  # no history flag: never on the boards
  week=board('7d');assert week['status']=='OK' and week['window_days']==7 and len(week['miners'])==1,week
  m=week['miners'][0];assert m['average_hashrate']==1000.0 and m['blocks_found']==4 and m['active_days']==1,m
  assert m['uptime_percent']==round(100/1008,1),m  # one 10-minute slot of 1008 in a week
  assert requests.get(base+'?board=1y').status_code==400
  # Withdrawal: a report without the flag deletes that miner's history immediately.
  assert report(b,5000,9,history=True).status_code==200 and len(board('7d')['miners'])==2
  assert report(b,5000,9,history=False).status_code==200 and len(board('7d')['miners'])==1
  # Pruning and windows: a day 10 days ago counts for 30 days only; 40 days ago is deleted.
  hist=Path(str(stats)+'.history.json');data=json.loads(hist.read_text());aid=next(iter(next(iter(data['days'].values()))))
  day=lambda n:time.strftime('%Y-%m-%d',time.gmtime(time.time()-n*86400))
  data['days'][day(10)]={aid:{'r':2,'h':4000.0,'b':5,'s':'f'+'0'*35}};data['days'][day(40)]={aid:{'r':1,'h':1.0,'b':1,'s':'1'+'0'*35}};hist.write_text(json.dumps(data))
  assert report(a,1000,3,history=True).status_code==200
  data=json.loads(hist.read_text());assert day(40) not in data['days'] and day(10) in data['days']
  assert board('7d')['miners'][0]['blocks_found']==4
  month=board('30d')['miners'][0];assert month['blocks_found']==9 and month['active_days']==2 and month['average_hashrate']==round((1000*5+4000)/7,2),month
  assert oct(hist.stat().st_mode&0o777)=='0o600' and str(a) not in hist.read_text()  # keyed by HMAC, not the installation ID
  # Page boards.
  from playwright.sync_api import sync_playwright
  fixture={'status':'OK','generated_at':int(time.time()),'window_days':7,'miners':[{'name':f'Miner {i:08X}','average_hashrate':1000.0+i,'uptime_percent':50.0-i,'blocks_found':i%3,'active_days':7} for i in range(5)]}
  with sync_playwright() as p:
   browser=p.chromium.launch(headless=True,executable_path=shutil.which('chromium'))
   page=browser.new_page(viewport={'width':390,'height':900});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
   page.route('**/api/miner-stats/?board=*',lambda r:r.fulfill(content_type='application/json',body=json.dumps(fixture)))
   page.route('**/api/miner-stats/',lambda r:r.fulfill(content_type='application/json',body=json.dumps({'status':'OK','generated_at':int(time.time()),'active_miners':0,'total_hashrate':0,'total_blocks':0,'miners':[]})))
   page.goto(f'http://127.0.0.1:{port}/mining/leaderboard/');page.wait_for_function("document.querySelectorAll('#by-uptime tr').length===5")
   assert 'Miner 00000000' in page.locator('#by-uptime tr').first.inner_text() and '50.0%' in page.locator('#by-uptime tr').first.inner_text()
   assert 'Miner 00000004' in page.locator('#by-average tr').first.inner_text() and page.locator('#by-period-blocks tr').count()==3
   fixture['miners'][0]['name']='<b>wallet</b>';page.select_option('#window','30d');page.wait_for_function("document.getElementById('history-status').textContent.includes('unavailable')")
   assert page.locator('#by-uptime tr').count()==0 and page.evaluate('document.documentElement.scrollWidth <= innerWidth') and not errors,errors
   browser.close()
 finally:server.terminate();server.wait(timeout=5)
print('Miner history: opt-in totals, uptime slots, block increments, withdrawal, pruning, 7/30-day boards, page boards passed')
