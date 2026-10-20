"""Deploy script against a fake webspace home: plan, upload with backup and verification, live-owned
paths never touched, server-side edits refused unless forced, nothing deleted, rollback."""
import json,os,shutil,subprocess,sys,tempfile
from pathlib import Path
root=Path(__file__).resolve().parents[2];site=root/'website';script=[sys.executable,str(root/'utils/website/deploy.py')]

with tempfile.TemporaryDirectory() as tmp:
 home=Path(tmp);live=home/'Monzero'
 shutil.copytree(site,live,ignore=shutil.ignore_patterns('downloads','__pycache__'))
 for f in (live/'network/data').glob('*.json'):f.unlink()
 env={**os.environ,'DEPLOY_REMOTE':f'local:{home}'}
 run=lambda *a:subprocess.run(script+list(a),env=env,capture_output=True,text=True,timeout=600)
 # Live differs: one stale page, one missing page, a live-only file, live-owned files that differ.
 (live/'security/index.html').write_text('old page')
 (live/'markets/index.html').unlink()
 (live/'live-only.txt').write_text('keep me')
 (live/'releases/v1.0.0.json').write_text('{"live":"authoritative"}')
 (live/'exchanges/catalog.json').write_text('{"edited":"in admin"}')
 out=run();assert out.returncode==0,out.stderr
 assert '2 to upload (1 new, 1 changed)' in out.stdout and 'security/index.html' in out.stdout and 'markets/index.html' in out.stdout,out.stdout
 assert 'releases/' not in out.stdout and 'exchanges/catalog.json' not in out.stdout
 assert (live/'security/index.html').read_text()=='old page'  # plan only
 out=run('--apply');assert out.returncode==0,out.stderr+out.stdout
 assert (live/'security/index.html').read_bytes()==(site/'security/index.html').read_bytes() and (live/'markets/index.html').exists()
 assert (live/'live-only.txt').read_text()=='keep me' and json.loads((live/'releases/v1.0.0.json').read_text())=={'live':'authoritative'}
 assert json.loads((live/'exchanges/catalog.json').read_text())=={'edited':'in admin'}
 manifest=json.loads((home/'monzero-private/deploy-manifest.json').read_text());assert manifest['files']['security/index.html']
 assert oct((home/'monzero-private/deploy-manifest.json').stat().st_mode&0o777)=='0o600'
 backups=list((home/'Monzero-backups').glob('deploy-*'));assert len(backups)==1
 assert (backups[0]/'replaced.txt').read_text().split()==['security/index.html']
 out=run();assert 'live site is up to date' in out.stdout,out.stdout
 # Someone edits a page on the server: the next deploy refuses it unless forced.
 (live/'fund/index.html').write_text('hand edit on the server')
 out=run('--apply');assert out.returncode!=0 and 'fund/index.html' in out.stdout and 'refusing' in out.stderr,out.stdout+out.stderr
 assert (live/'fund/index.html').read_text()=='hand edit on the server'
 out=run('--apply','--force','fund/index.html');assert out.returncode==0,out.stderr
 assert (live/'fund/index.html').read_bytes()==(site/'fund/index.html').read_bytes()
 # Rollback restores what the last deploy replaced.
 out=run('--rollback');assert out.returncode==0,out.stderr
 assert (live/'fund/index.html').read_text()=='hand edit on the server'
 assert not (home/'monzero-private/deploy-manifest.json').exists()
print('Deploy: plan, upload with backup and verification, live-owned and live-only files untouched, server edits refused unless forced, rollback passed')
