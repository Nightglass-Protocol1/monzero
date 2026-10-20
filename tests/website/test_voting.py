"""Community voting: admin creates/closes/withdraws polls; eligibility (full sign-in, account older than
the poll), one final vote per member, per-network cap, CSRF and origin checks, results visibility."""
import hashlib,json,os,re,secrets,socket,sqlite3,subprocess,sys,tempfile,time
from pathlib import Path
import requests
root=Path(__file__).resolve().parents[2];site=root/'website';PASSWORD='correct horse battery staple'
sys.path.insert(0,str(Path(__file__).resolve().parent));from admin_mfa import enroll

with tempfile.TemporaryDirectory() as tmp:
 tmp=Path(tmp);private=tmp/'private';private.mkdir();mail=tmp/'mail.jsonl'
 (tmp/'faucet-config.php').write_text("<?php return ['enabled' => true, 'amount_atomic' => '10000000000', 'daily_cap_atomic' => '500000000000', 'turnstile_site_key' => 'k', 'turnstile_secret' => 's', 'worker_secret' => '"+'a'*64+"', 'base_url' => 'http://127.0.0.1'];\n")
 with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
 base=f'http://127.0.0.1:{port}'
 env={**os.environ,'MONZERO_ADMIN_DB':str(private/'admin.sqlite'),'MONZERO_ADMIN_MAIL_LOG':str(mail),'MONZERO_ADMIN_BASE_URL':base,'MONZERO_FAUCET_CONFIG':str(tmp/'faucet-config.php'),
      'MONZERO_FAUCET_DB':str(private/'faucet.sqlite'),'MONZERO_VOTING_DB':str(private/'voting.sqlite'),'MONZERO_CONTENT_ROOT':str(tmp)}
 assert subprocess.run(['php',str(site/'admin/bootstrap.php'),'security@monzero.org'],env=env,capture_output=True).returncode==0
 server=subprocess.Popen(['php','-S',f'127.0.0.1:{port}','-t',str(site)],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 try:
  for _ in range(100):
   try:
    with socket.create_connection(('127.0.0.1',port),timeout=.2):break
   except OSError:time.sleep(.1)
  assert 'No proposals yet' in requests.get(base+'/community/voting/').text
  # Owner opens a poll.
  token=re.search(r'\?setup=([A-Za-z0-9_-]{43})',json.loads(mail.read_text().splitlines()[-1])['body']).group(1)
  owner=requests.Session();assert owner.post(base+'/admin/?do=setup',data={'token':token,'password':PASSWORD,'confirm':PASSWORD},allow_redirects=False).status_code==303;enroll(owner,base)
  csrf=lambda s,q:re.search(r'name="csrf" value="([^"]+)"',s.get(base+'/admin/'+q).text).group(1)
  r=owner.post(base+'/admin/?do=proposal-create',data={'csrf':csrf(owner,'?view=proposals'),'title':'x','description':'too short','options':'Yes','days':'7'});assert r.status_code==400 and 'title' in r.text
  r=owner.post(base+'/admin/?do=proposal-create',data={'csrf':csrf(owner,'?view=proposals'),'title':'Should the faucet amount rise to 0.2 XMZ?','description':'The faucet pays 0.1 XMZ a day.\nShould it pay 0.2?',
    'options':'Yes\nNo\nNo opinion','days':'7'},allow_redirects=False);assert r.status_code==303,r.text
  slug=sqlite3.connect(private/'voting.sqlite').execute('SELECT slug FROM proposals').fetchone()[0];assert slug.endswith('should-the-faucet-amount-rise-to-0-2-xmz')
  # Members (faucet accounts) and their sessions, inserted directly; sign-up itself is covered by test_faucet.py.
  requests.get(base+'/faucet/')  # creates the faucet database
  db=sqlite3.connect(private/'faucet.sqlite');now=int(time.time())
  def member(email,created,level='full',verified=True,totp=True):
   cur=db.execute("INSERT INTO members (email,password_hash,email_verified_at,totp_secret,created_at) VALUES (?,?,?,?,?)",(email,'x',now if verified else None,'A'*32 if totp else None,created))
   token=secrets.token_urlsafe(32)[:43].ljust(43,'A');c=secrets.token_hex(16)
   db.execute("INSERT INTO sessions (hash,member_id,level,csrf,created_at,seen_at) VALUES (?,?,?,?,?,?)",(hashlib.sha256(token.encode()).hexdigest(),cur.lastrowid,level,c,now,now));db.commit()
   s=requests.Session();s.cookies.set('mzfaucet',token);return s,c
  page=lambda s:s.get(base+f'/community/voting/?p={slug}').text
  vote=lambda s,c,o,**kw:s.post(base+f'/community/voting/?p={slug}',data={'csrf':c,'option':o},allow_redirects=False,**kw)
  alice,ac=member('alice@example.org',now-86400)
  assert 'Cast vote' in page(alice) and 'Results are shown after you vote' in page(alice)
  assert vote(alice,'0'*32,0).status_code==403
  assert vote(alice,ac,0,headers={'Origin':'https://evil.example'}).status_code==403
  assert vote(alice,ac,9).status_code==400
  r=vote(alice,ac,0);assert r.status_code==303 and 'voted=1' in r.headers['Location']
  text=alice.get(base+r.headers['Location']).text;assert 'Your vote was recorded' in text and 'Yes (your vote)' in text and '1 vote.' in text
  r=vote(alice,ac,1);assert r.status_code==400 and 'You have voted' in r.text
  late,lc=member('late@example.org',now+5);assert 'Only accounts created before' in page(late) and vote(late,lc,1).status_code==400
  half,hc=member('half@example.org',now-86400,level='setup');assert 'Finish signing in' in page(half) and vote(half,hc,1).status_code==400
  assert 'Sign in with your faucet account' in requests.get(base+f'/community/voting/?p={slug}').text
  # Per-network cap: two more votes from this network, then refused.
  for i in range(2):s,c=member(f'm{i}@example.org',now-86400);assert vote(s,c,1).status_code==303
  s,c=member('m9@example.org',now-86400);r=vote(s,c,1);assert r.status_code==400 and 'maximum number of votes' in r.text
  # Votes are final in storage.
  con=sqlite3.connect(private/'voting.sqlite')
  try:con.execute('UPDATE votes SET option_index=2');raise AssertionError('vote changed')
  except sqlite3.DatabaseError as e:assert 'final' in str(e)
  finally:con.rollback();con.close()
  # Close early: final results for everyone, no more votes.
  r=owner.post(base+'/admin/?do=proposal-close',data={'csrf':csrf(owner,'?view=proposals'),'slug':slug},allow_redirects=False);assert r.status_code==303,(r.status_code,re.sub(r'<[^>]+>',' ',r.text)[-400:])
  anon=requests.get(base+f'/community/voting/?p={slug}').text;assert 'Final results' in anon and '3 votes.' in anon and 'Yes' in anon
  s,c=member('m10@example.org',now-86400);assert vote(s,c,0).status_code==400
  listing=requests.get(base+'/community/voting/').text;assert 'Closed' in listing and '3 votes' in listing
  # Withdraw: hidden from the public.
  assert owner.post(base+'/admin/?do=proposal-withdraw',data={'csrf':csrf(owner,'?view=proposals'),'slug':slug},allow_redirects=False).status_code==303
  assert requests.get(base+f'/community/voting/?p={slug}').status_code==404 and 'No proposals yet' in requests.get(base+'/community/voting/').text
  actions=[a for (a,) in sqlite3.connect(private/'admin.sqlite').execute('SELECT action FROM audit')]
  assert {'proposal.created','proposal.closed','proposal.withdrawn'}<=set(actions)
  assert requests.get(base+'/lib/voting.php').status_code==404
 finally:server.terminate();server.wait(timeout=5)
print('Voting: admin create/close/withdraw, eligibility, one final vote, network cap, CSRF/origin, results visibility passed')
