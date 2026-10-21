"""Exercise the production PHP adapter with a loopback-only synthetic RPC server."""
import fcntl, json, os, socket, subprocess, tempfile, threading, time, unittest, urllib.request, urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

class ObservationTest(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  class Rpc(BaseHTTPRequestHandler):
   def log_message(self,*args): pass
   def do_POST(self):
    self.rfile.read(int(self.headers.get('Content-Length',0)))
    cls.calls+=1
    data=cls.info if self.path=='/get_info' else {'result':{'block_header':cls.header}}
    body=json.dumps(data).encode();self.send_response(cls.header_status if self.path=='/json_rpc' else cls.upstream_status);self.send_header('Location','/get_info');self.send_header('Content-Type','application/json');self.end_headers()
    if cls.slow:
     try:
      for byte in body:
       self.wfile.write(bytes([byte]));self.wfile.flush();time.sleep(.25)
     except (BrokenPipeError,ConnectionResetError):pass
    else:self.wfile.write(body)
  cls.rpc=ThreadingHTTPServer(('127.0.0.1',0),Rpc)
  cls.thread=threading.Thread(target=cls.rpc.serve_forever,daemon=True);cls.thread.start()
  cls.temp=tempfile.TemporaryDirectory()
  source=(Path(__file__).resolve().parents[2]/'website/api/node-info/index.php').read_text()
  source=source.replace("http://node.monzero.org:6175",f'http://127.0.0.1:{cls.rpc.server_port}')
  source=source.replace('sys_get_temp_dir()',repr(cls.temp.name))
  if os.environ.get('MONZERO_TEST_STREAM_HTTP')=='1':source=source.replace("function_exists('curl_init')",'false')
  Path(cls.temp.name,'index.php').write_text(source)
  with socket.socket() as s:s.bind(('127.0.0.1',0));cls.port=s.getsockname()[1]
  cls.php=subprocess.Popen(['php','-S',f'127.0.0.1:{cls.port}','-t',cls.temp.name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  for _ in range(50):
   try:
    with socket.create_connection(('127.0.0.1',cls.port),timeout=.2):break
   except OSError:time.sleep(.1)
  else:raise RuntimeError('PHP server did not start')
 @classmethod
 def tearDownClass(cls):
  cls.php.terminate();cls.php.wait(timeout=5);cls.rpc.shutdown();cls.rpc.server_close();cls.temp.cleanup()
 def clear_cache(self):
  for p in Path(self.temp.name).glob('monzero-node-status-*/observation.json'):p.unlink()
 def setUp(self):
  self.clear_cache();type(self).calls=0;type(self).upstream_status=200;type(self).header_status=200;type(self).slow=False
  type(self).info={'status':'OK','nettype':'mainnet','height':100,'top_block_hash':'a'*64,'difficulty':12345,'difficulty_top64':0,'synchronized':True}
  type(self).header={'height':99,'hash':'a'*64,'reward':200000000000,'timestamp':int(time.time())}
 def get(self):
  request=urllib.request.Request(f'http://127.0.0.1:{self.port}/index.php',data=b'{}',headers={'Content-Type':'application/json'})
  with urllib.request.urlopen(request,timeout=12) as response:return json.load(response)
 def test_matching_tip(self):
  value=self.get();self.assertTrue(value['tip_fresh']);self.assertEqual(value['tip_height'],99);self.assertEqual(value['tip_reward_atomic'],200000000000)
 def test_changed_tip_is_not_bound(self):
  for field,value in [('height',100),('hash','b'*64)]:
   self.setUp();self.header[field]=value;result=self.get()
   self.assertFalse(result['tip_fresh']);self.assertIsNone(result['tip_reward_atomic']);self.assertIsNone(result['tip_height'])
 def test_server_freshness_policy(self):
  for age,accepted in [(120,True),(2000,False),(-200,True),(-400,False)]:
   self.clear_cache()
   self.header['timestamp']=int(time.time())-age
   self.assertEqual(self.get()['tip_fresh'],accepted)
 def test_cache_reuse_expiry_and_no_stale_on_error(self):
  first=self.get();self.assertEqual(self.calls,2)
  self.header['reward']=300000000000
  self.assertEqual(self.get()['tip_reward_atomic'],first['tip_reward_atomic']);self.assertEqual(self.calls,2)
  path=next(Path(self.temp.name).glob('monzero-node-status-*/observation.json'))
  state=json.loads(path.read_text());state['observed_at']-=16;path.write_text(json.dumps(state))
  self.assertEqual(self.get()['tip_reward_atomic'],300000000000);self.assertEqual(self.calls,4)
  state=json.loads(path.read_text());state['observed_at']-=16;path.write_text(json.dumps(state));type(self).upstream_status=503
  for _ in range(2):
   with self.assertRaises(urllib.error.HTTPError) as error:self.get()
   self.assertEqual(error.exception.code,502);error.exception.close()
  self.assertEqual(self.calls,5) # failed observations also cool down
 def test_cached_tip_freshness_recomputed(self):
  self.get();path=next(Path(self.temp.name).glob('monzero-node-status-*/observation.json'))
  state=json.loads(path.read_text());state['header']['timestamp']=int(time.time())-1801;path.write_text(json.dumps(state))
  self.assertFalse(self.get()['tip_fresh']);self.assertEqual(self.calls,2)
 def test_busy_cache_does_not_fetch(self):
  self.get();path=next(Path(self.temp.name).glob('monzero-node-status-*/observation.json'))
  with path.open('r+') as file:
   fcntl.flock(file,fcntl.LOCK_EX|fcntl.LOCK_NB)
   with self.assertRaises(urllib.error.HTTPError) as error:self.get()
   self.assertEqual(error.exception.code,503);error.exception.close()
  self.assertEqual(self.calls,2)
 def test_testnet_is_not_ready(self):
  self.info.update(nettype='testnet',incoming_connections_count=3)
  self.assertFalse(self.get()['network_ready'])
 def test_oversized_response_rejected(self):
  self.info['oversized']='x'*262144
  with self.assertRaises(urllib.error.HTTPError) as error:self.get()
  self.assertEqual(error.exception.code,502);error.exception.close()
 def test_redirect_is_not_followed(self):
  type(self).upstream_status=302
  with self.assertRaises(urllib.error.HTTPError) as error:self.get()
  self.assertEqual(error.exception.code,502);error.exception.close();self.assertEqual(self.calls,1)
 def test_private_cache_and_corruption_recovery(self):
  self.get();path=next(Path(self.temp.name).glob('monzero-node-status-*/observation.json'))
  self.assertEqual(path.stat().st_mode&0o777,0o600);self.assertEqual(path.parent.stat().st_mode&0o777,0o700)
  path.write_text('{broken')
  self.assertTrue(self.get()['tip_fresh']);self.assertEqual(self.calls,4)
 def test_fresh_readers_share_lock(self):
  self.get();path=next(Path(self.temp.name).glob('monzero-node-status-*/observation.json'))
  with path.open('r') as file:
   fcntl.flock(file,fcntl.LOCK_SH|fcntl.LOCK_NB)
   self.assertTrue(self.get()['tip_fresh'])
  self.assertEqual(self.calls,2)
 def test_partial_failure_cools_down_for_five_seconds(self):
  type(self).header_status=503
  with self.assertRaises(urllib.error.HTTPError) as error:self.get()
  self.assertEqual(error.exception.code,502);self.assertEqual(error.exception.headers['Retry-After'],'5');error.exception.close()
  path=next(Path(self.temp.name).glob('monzero-node-status-*/observation.json'))
  state=json.loads(path.read_text());self.assertFalse(state['available']);state['observed_at']-=6;path.write_text(json.dumps(state))
  type(self).header_status=200;type(self).slow=False
  self.assertTrue(self.get()['tip_fresh']);self.assertEqual(self.calls,4)
 def test_future_timestamp_forces_new_observation(self):
  self.get();path=next(Path(self.temp.name).glob('monzero-node-status-*/observation.json'))
  state=json.loads(path.read_text());state['observed_at']+=1000;path.write_text(json.dumps(state))
  self.get();self.assertEqual(self.calls,4)
 def test_slow_response_has_total_deadline(self):
  type(self).slow=True;started=time.monotonic()
  with self.assertRaises(urllib.error.HTTPError) as error:self.get()
  self.assertEqual(error.exception.code,502);error.exception.close()
  self.assertLess(time.monotonic()-started,7)
 def test_post_only(self):
  with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(f'http://127.0.0.1:{self.port}/index.php',timeout=5)
  self.assertEqual(error.exception.code,405);error.exception.close()
if __name__=='__main__':unittest.main()
