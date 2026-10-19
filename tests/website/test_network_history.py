import subprocess,sys
import importlib.util,json,os,sqlite3,tempfile,unittest,concurrent.futures,threading,time
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
spec=importlib.util.spec_from_file_location('history',Path(__file__).resolve().parents[2]/'utils/website/network_history.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
def sample(at,height=4,difficulty=10000):
 return {'schema':'monzero-chain-charts-v2','network':'mainnet','target_seconds':120,'height':height,'generated_at':at,'synchronized':True,
         'blocks':[{'height':n,'timestamp':at-120*(height-1-n),'difficulty':difficulty,'transactions':0} for n in range(max(1,height-720),height)]}
class History(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'private'/'history.sqlite';self.db=h.connect(self.path)
 def tearDown(self):self.db.close();self.tmp.cleanup()
 def test_schema_permissions_and_reopen(self):
  self.assertEqual(self.path.stat().st_mode&0o777,0o600);self.assertEqual(self.path.parent.stat().st_mode&0o777,0o700)
  self.assertEqual(self.db.execute('PRAGMA user_version').fetchone()[0],1)
  self.db.close();self.db=h.connect(self.path);self.assertEqual(self.db.execute('SELECT count(*) FROM observations').fetchone()[0],0)
 def test_idempotence_conflicts_and_clock(self):
  self.assertTrue(h.record(self.db,sample(1000),'preview',1000));self.assertFalse(h.record(self.db,sample(1000),'preview',1000))
  with self.assertRaises(ValueError):h.record(self.db,sample(1000,difficulty=20000),'preview',1000)
  with self.assertRaises(ValueError):h.record(self.db,sample(999),'preview',1000)
  self.assertFalse(h.record(self.db,sample(1030),'preview',1030));self.assertEqual(h.export(self.db,'all',1030)['archive_samples'],1)
 def test_bad_metadata_and_samples(self):
  for field,value in [('network','testnet'),('target_seconds',0),('height',4.0),('synchronized','true'),('generated_at',2000)]:
   data=sample(1000);data[field]=value
   with self.assertRaises(ValueError):h.record(self.db,data,'preview',1000)
  for field,value in [('difficulty',2**53),('difficulty',True),('timestamp',0),('transactions',-1)]:
   data=sample(1000);data['blocks'][0][field]=value
   with self.assertRaises(ValueError):h.record(self.db,data,'preview',1000)
  with self.assertRaises(ValueError):h.record(self.db,sample(500),'preview',1000)
 def test_gaps_empty_ranges_and_reorganization_observations(self):
  self.assertEqual(h.export(self.db,'all',1000)['points'],[])
  h.record(self.db,sample(1000,5),'preview',1000);h.record(self.db,sample(10000,4),'preview',10000)
  out=h.export(self.db,'all',10000);self.assertEqual(len(out['points']),2)
  self.assertEqual(out['points'][1]['minimum_height'],4)
  self.assertEqual(h.export(self.db,'24h',100000)['points'],[])
 def test_bounded_aggregation_and_exact_extrema(self):
  for i in range(1500):h.record(self.db,sample(1000+i*60,difficulty=9007199254740991),'preview',1000+i*60)
  out=h.export(self.db,'all',1000+1500*60);self.assertLessEqual(len(out['points']),721)
  self.assertEqual(sum(p['samples'] for p in out['points']),1500)
  self.assertEqual(out['points'][0]['maximum_difficulty'],'9007199254740991')
  json.dumps(out,allow_nan=False)
 def test_unrelated_database_is_not_migrated(self):
  other=self.path.parent/'unrelated.sqlite'
  db=sqlite3.connect(other);db.execute('CREATE TABLE private_records (value TEXT)');db.commit();db.close()
  with self.assertRaises(ValueError):h.connect(other)
  db=sqlite3.connect(other);self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],0)
  self.assertEqual(db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall(),[('private_records',)]);db.close()
 def test_all_requested_ranges_and_minute_cadence(self):
  h.record(self.db,sample(100000),'preview',100000)
  for name in h.RANGES:
   out=h.export(self.db,name,100060);self.assertEqual(len(out['points']),1);self.assertEqual(out['sources'],['preview'])
  with self.assertRaises(ValueError):h.export(self.db,'unknown',100060)
 def test_concurrent_initialization_and_ingest(self):
  path=self.path.parent/'concurrent.sqlite';barrier=threading.Barrier(2)
  def worker():
   barrier.wait();db=h.connect(path)
   try:return h.record(db,sample(1000),'preview',1000)
   finally:db.close()
  with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
   results=list(pool.map(lambda _:worker(),range(2)))
  self.assertEqual(sorted(results),[False,True])
  db=h.connect(path);self.assertEqual(h.export(db,'all',1000)['archive_samples'],1);db.close()
 def test_sources_cannot_mix(self):
  h.record(self.db,sample(1000),'preview',1000)
  with self.assertRaises(ValueError):h.record(self.db,sample(1060),'live',1060)
  self.assertEqual(h.export(self.db,'all',1060)['sources'],['preview'])
 def test_sync_tip_age_and_boundary_metadata(self):
  d=sample(100000);d['synchronized']=False
  self.assertTrue(h.record(self.db,d,'preview',100000))
  self.assertTrue(h.record(self.db,sample(100060),'preview',100060))
  out=h.export(self.db,'24h',186400)
  self.assertEqual(sum(p['samples'] for p in out['points']),2)
  self.assertEqual(out['points'][0]['synchronized_samples'],1)
  self.assertFalse(out['points'][0]['all_samples_synchronized'])
  self.assertEqual(out['points'][0]['maximum_tip_age_seconds'],0)
 def test_symlinks_rejected(self):
  linked=self.path.parent/'link.sqlite';linked.symlink_to(self.path)
  with self.assertRaises(ValueError):h.connect(linked)
  directory=Path(self.tmp.name)/'linked';directory.symlink_to(self.path.parent,target_is_directory=True)
  with self.assertRaises(ValueError):h.connect(directory/'history.sqlite')
 def test_backup_roundtrip(self):
  h.record(self.db,sample(1000),'preview',1000)
  path=self.path.parent/'backup.sqlite';target=h.connect(path)
  self.db.backup(target);target.close()
  restored=h.connect(path)
  try:self.assertEqual(h.export(restored,'all',1000),h.export(self.db,'all',1000))
  finally:restored.close()
 def test_public_exports_replace_files_without_exposing_database(self):
  h.record(self.db,sample(1000),'preview',1000);out=Path(self.tmp.name)/'public'
  self.assertEqual(h.publish(self.db,out,1060),6)
  self.assertEqual({p.name for p in out.iterdir()},{name+'.json' for name in h.RANGES})
  for file in out.iterdir():
   data=json.loads(file.read_text());self.assertEqual(data['archive_samples'],1)
   self.assertEqual(file.stat().st_mode&0o777,0o644);self.assertNotIn('digest',data)
  h.publish(self.db,out,1120)
  self.assertEqual(json.loads((out/'all.json').read_text())['generated_at'],1120)
 def test_source_window_and_staleness_boundaries(self):
  self.assertTrue(h.record(self.db,sample(1000),'preview',1300))
  with self.assertRaises(ValueError):h.normalize(sample(1000),1301)
  with self.assertRaisesRegex(ValueError,'clock is ahead'):h.normalize(sample(1301),1300)
  with self.assertRaises(ValueError):h.record(self.db,sample(1400),'unknown',1400)
  for change in ({'schema':'wrong'},{'blocks':{}},{'blocks':[]},{'target_seconds':120.0}):
   data=sample(1400);data.update(change)
   with self.assertRaises(ValueError):h.normalize(data,1400)
  data=sample(1400);data['blocks'][1]['height']=99
  with self.assertRaises(ValueError):h.normalize(data,1400)
 def test_export_only_does_not_create_database_or_replace_files_on_wrong_path(self):
  out=Path(self.tmp.name)/'public';out.mkdir();(out/'all.json').write_text('keep-existing')
  missing=Path(self.tmp.name)/'wrong'/'missing.sqlite'
  result=subprocess.run([sys.executable,str(Path(h.__file__)),'--export-only','--database',str(missing),'--output-directory',str(out)],capture_output=True)
  self.assertNotEqual(result.returncode,0);self.assertFalse(missing.parent.exists());self.assertEqual((out/'all.json').read_text(),'keep-existing')
 def test_readonly_export(self):
  h.record(self.db,sample(1000),'preview',1000);db=h.connect(self.path,readonly=True)
  try:
   self.assertEqual(h.export(db,'all',1000)['archive_samples'],1)
   with self.assertRaises(sqlite3.OperationalError):db.execute('DELETE FROM observations')
  finally:db.close()
 def test_refuse_public_directory_and_future_schema(self):
  self.path.parent.chmod(0o755)
  with self.assertRaises(ValueError):h.connect(self.path)
  self.path.parent.chmod(0o700);self.db.execute('PRAGMA user_version=2');self.db.commit()
  with self.assertRaises(ValueError):h.connect(self.path)
class Transport(unittest.TestCase):
 def test_bounded_fixed_source_fetch(self):
  state={'status':200,'body':b'{"ok":true}','delay':0}
  class Handler(BaseHTTPRequestHandler):
   def log_message(self,*args):pass
   def do_GET(self):
    time.sleep(state['delay']);self.send_response(state['status']);self.send_header('Location','/other');self.end_headers()
    try:self.wfile.write(state['body'])
    except (BrokenPipeError,ConnectionResetError):pass
  server=ThreadingHTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
  original=h.SOURCES['preview'];h.SOURCES['preview']=f'http://127.0.0.1:{server.server_port}/'
  try:
   self.assertEqual(h.fetch('preview'),{'ok':True})
   for status in (302,500):
    state['status']=status
    with self.assertRaises(ValueError):h.fetch('preview')
   state.update(status=200,body=b' '*2097153)
   with self.assertRaises(ValueError):h.fetch('preview')
   state.update(body=b'{}',delay=1)
   with self.assertRaisesRegex(ValueError,'timed out'):h.fetch('preview',timeout=.1)
  finally:h.SOURCES['preview']=original;server.shutdown();server.server_close()
if __name__=='__main__':unittest.main()
