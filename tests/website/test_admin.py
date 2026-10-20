"""Admin accounts: owner bootstrap, invites with owner approval, delegated permissions, CSRF,
throttling, TOTP, disabling and the append-only audit log. Isolated database and mail log."""
import base64,hashlib,hmac,json,os,re,socket,sqlite3,struct,subprocess,tempfile,time
from pathlib import Path
import requests
root=Path(__file__).resolve().parents[2]
PASSWORD='correct horse battery staple'

def totp(secret,offset=0):
 key=base64.b32decode(secret);counter=int(time.time())//30+offset
 h=hmac.new(key,struct.pack('>Q',counter),hashlib.sha1).digest();o=h[19]&15
 return f"{(struct.unpack('>I',h[o:o+4])[0]&0x7fffffff)%1000000:06d}"

with tempfile.TemporaryDirectory() as tmp:
 tmp=Path(tmp);db=tmp/'private/admin.sqlite';mail=tmp/'mail.jsonl'
 with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
 base=f'http://127.0.0.1:{port}'
 env={**os.environ,'MONZERO_ADMIN_DB':str(db),'MONZERO_ADMIN_MAIL_LOG':str(mail),'MONZERO_ADMIN_BASE_URL':base}
 def mails():return [json.loads(l) for l in mail.read_text().splitlines()] if mail.exists() else []
 def link_for(email):
  token=re.search(r'\?setup=([A-Za-z0-9_-]{43})',[m for m in mails() if m['to']==email][-1]['body']).group(1);return token
 boot=subprocess.run(['php',str(root/'website/admin/bootstrap.php'),'security@monzero.org'],env=env,capture_output=True,text=True)
 assert boot.returncode==0,boot.stderr
 assert oct(db.stat().st_mode&0o777)=='0o600' and oct((db.parent/'admin-secret').stat().st_mode&0o777)=='0o600'
 assert subprocess.run(['php',str(root/'website/admin/bootstrap.php'),'other@example.org'],env=env,capture_output=True).returncode==1
 server=subprocess.Popen(['php','-S',f'127.0.0.1:{port}','-t',str(root/'website')],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 try:
  for _ in range(50):
   try:
    with socket.create_connection(('127.0.0.1',port),timeout=.2):break
   except OSError:time.sleep(.1)
  def csrf(session,view=''):
   r=session.get(base+'/admin/'+(f'?view={view}' if view else ''));return re.search(r'name="csrf" value="([^"]+)"',r.text).group(1)
  def post(session,do,data,**kw):return session.post(base+f'/admin/?do={do}',data=data,allow_redirects=False,**kw)
  secrets_by={}
  def enroll(s,email):
   # Authenticator codes are mandatory: every new admin turns them on before anything else.
   account=s.get(base+'/admin/?view=account').text;m=re.search(r'name="secret" value="([A-Z2-7]{32})"',account)
   if not m:return
   secret=m.group(1);assert post(s,'totp-enable',{'csrf':csrf(s,'account'),'secret':secret,'code':totp(secret)}).status_code==303;secrets_by[email]=secret
  def setup(email,password=PASSWORD,mfa=True):
   s=requests.Session();token=link_for(email)
   page=s.get(base+f'/admin/?setup={token}');assert page.status_code==200 and email in page.text and page.headers['Cache-Control']=='no-store' and page.headers['Referrer-Policy']=='no-referrer'
   assert post(s,'setup',{'token':token,'password':'short','confirm':'short'}).status_code==400
   r=post(s,'setup',{'token':token,'password':password,'confirm':password});assert r.status_code==303 and 'mzadmin' in r.cookies,r.text
   assert post(requests.Session(),'setup',{'token':token,'password':password,'confirm':password}).status_code in (400,403)
   if mfa:enroll(s,email)
   return s
  # Owner activation; setup link is single-use. Without authenticator codes nothing else is allowed.
  owner=setup('security@monzero.org',mfa=False)
  r=owner.get(base+'/admin/',allow_redirects=False);assert r.status_code==303 and 'view=account' in r.headers['Location'] and 'totp-required' in r.headers['Location']
  assert 'required for every admin' in owner.get(base+'/admin/?view=account&msg=totp-required').text
  r=post(owner,'invite',{'csrf':csrf(owner,'account'),'email':'early@example.org'});assert r.status_code==403 and 'Turn on authenticator codes' in r.text
  account=owner.get(base+'/admin/?view=account').text;secret=re.search(r'name="secret" value="([A-Z2-7]{32})"',account).group(1)
  assert post(owner,'totp-enable',{'csrf':csrf(owner,'account'),'secret':secret,'code':'000000' if totp(secret)!='000000' else '111111'}).status_code==400
  assert post(owner,'totp-enable',{'csrf':csrf(owner,'account'),'secret':secret,'code':totp(secret)}).status_code==303
  page=owner.get(base+'/admin/');assert 'Signed in as <strong>security@monzero.org</strong> (owner)' in page.text
  assert owner.get(base+'/admin/?setup=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA').status_code==400
  # Owner invite is emailed at once with the chosen permissions.
  r=post(owner,'invite',{'csrf':csrf(owner,'admins'),'email':'Alice@Example.org','permissions[]':['admins.invite','exchanges']});assert r.status_code==303 and 'msg=invited' in r.headers['Location']
  alice=setup('alice@example.org')
  assert 'Invite admins' in alice.get(base+'/admin/').text and 'Audit log' not in alice.get(base+'/admin/').text
  # Delegated invite: subset only, waits for owner approval, no email until approved.
  before=len(mails())
  assert post(alice,'invite',{'csrf':csrf(alice,'admins'),'email':'bob@example.org','permissions[]':['exchanges','audit.view']}).status_code==400
  r=post(alice,'invite',{'csrf':csrf(alice,'admins'),'email':'bob@example.org','permissions[]':['exchanges']});assert 'msg=awaiting' in r.headers['Location']
  assert len(mails())==before
  assert 'Waiting for owner approval' in owner.get(base+'/admin/?view=admins').text
  bob_id=sqlite3.connect(db).execute("SELECT id FROM users WHERE email='bob@example.org'").fetchone()[0]
  assert post(alice,'approve',{'csrf':csrf(alice,'admins'),'user_id':bob_id}).status_code==403
  assert 'msg=approved' in post(owner,'approve',{'csrf':csrf(owner,'admins'),'user_id':bob_id}).headers['Location']
  bob=setup('bob@example.org')
  assert post(bob,'invite',{'csrf':csrf(bob),'email':'eve@example.org'}).status_code==403
  # CSRF and origin checks.
  assert post(owner,'invite',{'email':'x@example.org'}).status_code==403
  assert post(owner,'invite',{'csrf':csrf(owner,'admins'),'email':'x@example.org'},headers={'Origin':'https://evil.example'}).status_code==403
  # Owner edits permissions; cannot grant unknown ones; owner row is untouchable.
  alice_id=sqlite3.connect(db).execute("SELECT id FROM users WHERE email='alice@example.org'").fetchone()[0]
  assert post(owner,'permissions',{'csrf':csrf(owner,'admins'),'user_id':alice_id,'permissions[]':['made.up']}).status_code==400
  assert post(owner,'permissions',{'csrf':csrf(owner,'admins'),'user_id':alice_id,'permissions[]':['exchanges']}).status_code==303
  owner_id=sqlite3.connect(db).execute("SELECT id FROM users WHERE is_owner=1").fetchone()[0]
  assert post(owner,'disable',{'csrf':csrf(owner,'admins'),'user_id':owner_id}).status_code==403
  # Disabling ends the session immediately.
  assert post(owner,'disable',{'csrf':csrf(owner,'admins'),'user_id':alice_id}).status_code==303
  assert 'Sign in' in alice.get(base+'/admin/').text
  # Login: wrong passwords are throttled per account.
  for _ in range(5):assert post(requests.Session(),'login',{'email':'bob@example.org','password':'wrong password!!'}).status_code==401
  assert post(requests.Session(),'login',{'email':'bob@example.org','password':PASSWORD}).status_code==429
  assert post(requests.Session(),'login',{'email':'nobody@example.org','password':PASSWORD}).status_code==401
  # TOTP: sign-in needs the code, and codes cannot be turned off.
  assert post(owner,'totp-disable',{'csrf':csrf(owner,'account'),'current':PASSWORD}).status_code==400
  assert 'Turn off authenticator codes' not in owner.get(base+'/admin/?view=account').text
  assert post(requests.Session(),'login',{'email':'security@monzero.org','password':PASSWORD}).status_code==401
  fresh=requests.Session();r=post(fresh,'login',{'email':'security@monzero.org','password':PASSWORD,'code':totp(secret)});assert r.status_code==303
  assert '(owner)' in fresh.get(base+'/admin/').text
  # Sign out invalidates the server session.
  cookie=fresh.cookies.get('mzadmin');assert post(fresh,'logout',{'csrf':csrf(fresh)}).status_code==303
  assert 'Sign in' in requests.get(base+'/admin/',cookies={'mzadmin':cookie}).text
  # Forgotten owner password: CLI reset clears it, ends sessions, keeps TOTP, emails a new link.
  boot=lambda *a:subprocess.run(['php',str(root/'website/admin/bootstrap.php'),*a],env=env,capture_output=True,text=True)
  assert boot('--reset','other@example.org').returncode==1 and boot('--clear-totp','security@monzero.org').returncode==2
  assert boot('--reset','security@monzero.org').returncode==0
  assert 'Sign in' in owner.get(base+'/admin/').text
  assert post(requests.Session(),'login',{'email':'security@monzero.org','password':PASSWORD,'code':totp(secret)}).status_code==401
  NEW='a brand new long passphrase';owner=setup('security@monzero.org',NEW)
  assert post(requests.Session(),'login',{'email':'security@monzero.org','password':NEW}).status_code==401
  r=post(requests.Session(),'login',{'email':'security@monzero.org','password':NEW,'code':totp(secret,1)});assert r.status_code==303
  assert boot('--reset','--clear-totp','security@monzero.org').returncode==0;owner=setup('security@monzero.org',PASSWORD,mfa=False)
  assert sqlite3.connect(db).execute('SELECT totp_secret FROM users WHERE is_owner=1').fetchone()[0] is None
  assert owner.get(base+'/admin/?view=audit',allow_redirects=False).status_code==303  # must set up a new device first
  enroll(owner,'security@monzero.org')
  # Audit log: visible to owner, append-only in storage.
  audit=owner.get(base+'/admin/?view=audit').text
  for action in ['account.activated','invite.sent','invite.requested','invite.approved','permissions.changed','account.disabled','login.failed','login.throttled','totp.enabled','owner.password_reset']:assert action in audit,action
  assert 'Audit log' not in bob.get(base+'/admin/?view=audit').text.split('</h1>')[0]
  con=sqlite3.connect(db)
  for sql in ['UPDATE audit SET action="x"','DELETE FROM audit']:
   try:con.execute(sql);raise AssertionError('audit modified')
   except sqlite3.DatabaseError as e:assert 'append-only' in str(e)
  stored=con.execute('SELECT password_hash FROM users').fetchall();assert all(h is None or h.startswith('$argon2id$') for (h,) in stored)
  assert not any(PASSWORD in json.dumps(m) for m in mails())
  # Internals are not reachable over HTTP.
  assert requests.get(base+'/admin/lib.php').status_code==404 and requests.get(base+'/admin/bootstrap.php').status_code==404
 finally:server.terminate();server.wait(timeout=5)
print('Admin: mandatory authenticator codes, owner bootstrap, single-use links, delegated invites with approval, subset grants, CSRF/origin, throttling, TOTP, disable, logout, append-only audit passed')
