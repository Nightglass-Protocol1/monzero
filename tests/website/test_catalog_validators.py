"""PHP catalog validators (lib/catalogs.php) against the browser validators: thousands of mutated
catalogs; PHP may be stricter but must never accept a catalog the page would reject."""
import copy,json,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[2];site=root/'website';TODAY='2026-10-20'

def load(p):return json.loads((site/p).read_text())
exchanges=load('exchanges/catalog.json');ecosystem=load('ecosystem/catalog.json');bounties=load('community/bounties/catalog.json');benchmarks=load('mining/benchmarks/catalog.json')
for c in (exchanges,ecosystem,bounties):c['updated_at']=min(c['updated_at'],TODAY)
live={'id':'example-live','exchange':'Example','status':'live','note':'Verified live listing.','updated_at':'2026-10-19','application_date':'2026-10-01',
 'listing_fee':{'amount':'1500.50','currency':'USDT','evidence_url':'https://example.org/fee'},'funding':{'target':'15000','currency':'USD','progress_url':'/fund/'},
 'announcements':[{'label':'Listing live','url':'https://example.org/news'}],'pair':'XMZ/USDT','trading_url':'https://example.org/trade/XMZ_USDT',
 'deposits':'enabled','withdrawals':'disabled','trading':'active','last_verified':'2026-10-19','verification_url':'https://example.org/proof'}
paid={'id':'paid-bounty','title':'Fix a bug','description':'Line one.\nLine two.','category':'Bug fixes','difficulty':'beginner','acceptance_criteria':['Works'],
 'submission_instructions':'Open a pull request.','discussion_url':'https://github.com/x/y/issues/1','status':'completed','review_status':'accepted','updated_at':'2026-10-19',
 'maintainer':'Maintainers','reviewed_by':'Reviewer','reward_currency':'XMZ','reward_atomic':'100000000000','funding_status':'paid','funding_evidence_url':'https://example.org/f',
 'funding_checked_at':'2026-10-10','completion_evidence_url':'https://example.org/c','completion_checked_at':'2026-10-15','payment_evidence_url':'https://example.org/p','payment_checked_at':'2026-10-18'}
bench={'id':'amd-ryzen-test','manufacturer':'AMD','model':'Ryzen 7 7700','os':'Linux','miner':'XMRig','miner_version':'6.22.0','methodology':'Benchmark 1M',
 'cores':8,'threads':16,'hashrate_hps':12000.5,'power_watts':120,'power_basis':'wall','date':'2026-10-01','status':'verified','source_url':'https://example.org/run',
 'verification_url':'https://example.org/verify','verified_by':'Maintainer'}
post={'id':'2026-10-20-hello','date':'2026-10-20','title':'Hello','body':'First line.\nSecond line.','url':'/roadmap/'}
bases=[('exchanges',exchanges),('exchanges',{**exchanges,'records':exchanges['records']+[live]}),('ecosystem',ecosystem),('bounties',bounties),
 ('bounties',{**bounties,'records':bounties['records']+[paid]}),('benchmarks',{**benchmarks,'records':benchmarks['records']+[bench]}),
 ('announcements',{'schema':'monzero-announcements-v1','updated_at':TODAY,'records':[post]}),('roadmap-updates',{'schema':'monzero-roadmap-updates-v1','updated_at':TODAY,'records':[post]})]

pool=[None,'',' x','x ','x','x'*2100,'x y','x​y','a\tb','a\nb',0,1,-1,1.5,4.0,True,[],{},[1],'2026-10-20','2026-10-21','2026-02-30','2026-1-01','2025-01-01',
 'https://example.org/','http://example.org/','https://user@example.org/','https://','/fund/','//evil.example','/a\\b','https://ex ample.org','javascript:alert(1)',
 'https://example.org/path#frag','https://EXAMPLE.org/run','https://example.org:443/run','planned','live','suspended','approved','open','in-review','completed','cancelled',
 'awaiting-submission','accepted','funded','paid','none','proposed','community','verified','wall','cpu-package','unknown','XMZ','XMZ/USDT','xmz/usdt','enabled','disabled',
 'active','halted','Mining pools','Exchanges','Merchants','third-party','project','0','100000000000','18446744073709551615','18446744073709551616','01','USD','usd',
 '\U0001F600'*70,'x ',' x','beginner','advanced','Bug fixes',8,16,4096,4097,0.0001,1e400]

cases=[]
for kind,base in bases:
 cases.append((kind,base))
 for field in ('schema','updated_at','records'):
  for v in pool[:20]:m=copy.deepcopy(base);m[field]=v;cases.append((kind,m))
 for i,rec in enumerate(base['records']):
  for field in list(rec):
   for v in pool:
    m=copy.deepcopy(base);m['records'][i][field]=v;cases.append((kind,m))
   m=copy.deepcopy(base);del m['records'][i][field];cases.append((kind,m))
   for sub in (rec[field] if isinstance(rec[field],dict) else {}):
    for v in pool[:40]:m=copy.deepcopy(base);m['records'][i][field][sub]=v;cases.append((kind,m))
  m=copy.deepcopy(base);m['records'][i]['extra']=1;cases.append((kind,m))
  m=copy.deepcopy(base);m['records'].append(copy.deepcopy(rec));cases.append((kind,m))  # duplicate id
batch=[{'kind':k,'json':json.dumps(d,ensure_ascii=False).replace('Infinity','1e400')} for k,d in cases]  # 1e400 parses as Infinity in both
js=json.loads(subprocess.run(['node',str(root/'tests/website/catalog_js_check.mjs'),TODAY],input=json.dumps(batch),capture_output=True,text=True,check=True).stdout)
php=json.loads(subprocess.run(['php',str(root/'tests/website/catalog_php_check.php'),TODAY],input=json.dumps(batch),capture_output=True,text=True,check=True).stdout)
assert len(js)==len(php)==len(batch)
for i,(kind,_) in enumerate(bases):
 first=[j for j,(k,d) in enumerate(cases) if d is bases[i][1]][0]
 assert js[first] and php[first],(kind,'valid base rejected',js[first],php[first])
looser=[(batch[i]['kind'],batch[i]['json'][:300]) for i in range(len(batch)) if php[i] and not js[i]]
assert not looser,('PHP accepted catalogs the browser rejects',looser[:5])
stricter=sum(1 for i in range(len(batch)) if js[i] and not php[i]);accepted=sum(js)
print(f'Catalog validators: {len(batch)} cases, browser accepts {accepted}, PHP never looser, PHP stricter on {stricter}')
