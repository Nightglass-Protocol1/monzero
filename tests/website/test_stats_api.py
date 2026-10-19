"""Production PHP stats adapter against a loopback synthetic daemon; no mining."""
import fcntl,json,os,socket,subprocess,tempfile,threading,time,unittest,urllib.request,urllib.error
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
class StatsAPI(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  class Rpc(BaseHTTPRequestHandler):
   def log_message(self,*args):pass
   def do_POST(self):
    cls.calls+=1;payload=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
    if self.path=='/json_rpc':
     assert payload['method']=='get_block_headers_range'
     assert payload['params']['start_height']==1 and payload['params']['end_height']==3
    data=cls.info if self.path=='/get_info' else {'result':cls.range}
    body=json.dumps(data).encode()+ (b' '*2097153 if cls.oversized else b'')
    self.send_response(cls.upstream);self.send_header('Location','/get_info');self.end_headers()
    try:self.wfile.write(body)
    except (BrokenPipeError,ConnectionResetError):pass
  cls.rpc=ThreadingHTTPServer(('127.0.0.1',0),Rpc);threading.Thread(target=cls.rpc.serve_forever,daemon=True).start()
  cls.temp=tempfile.TemporaryDirectory();root=Path(cls.temp.name)
  source=Path(__file__).resolve().parents[2]/'website/stats'
  code=(source/'api.php').read_text().replace('http://node.monzero.org:6175',f'http://127.0.0.1:{cls.rpc.server_port}')
  if os.environ.get('MONZERO_TEST_STREAM_HTTP'):code=code.replace("function_exists('curl_init')",'false')
  (root/'api.php').write_text(code);(root/'contract.php').write_text((source/'contract.php').read_text())
  with socket.socket() as s:s.bind(('127.0.0.1',0));cls.port=s.getsockname()[1]
  cls.php=subprocess.Popen(['php','-d',f'sys_temp_dir={root}','-S',f'127.0.0.1:{cls.port}','-t',str(root)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  for _ in range(50):
   try:
    with socket.create_connection(('127.0.0.1',cls.port),timeout=.2):break
   except OSError:time.sleep(.1)
  else:raise RuntimeError('PHP did not start')
 @classmethod
 def tearDownClass(cls):cls.php.terminate();cls.php.wait(timeout=5);cls.rpc.shutdown();cls.rpc.server_close();cls.temp.cleanup()
 def setUp(self):
  type(self).calls=0;type(self).oversized=False;type(self).upstream=200
  for f in Path(self.temp.name).glob('monzero-chain-charts-*/observation.json'):f.unlink()
  h=lambda n:f'{n:064x}'
  type(self).info={'status':'OK','nettype':'mainnet','height':4,'target':120,'synchronized':True,'top_block_hash':h(3)}
  type(self).range={'status':'OK','headers':[{'height':n,'hash':h(n),'prev_hash':h(n-1),'orphan_status':False,'timestamp':int(time.time())-120*(3-n),'difficulty':10000,'difficulty_top64':0,'num_txes':0} for n in range(1,4)]}
 def request(self,method='GET'):
  try:r=urllib.request.urlopen(urllib.request.Request(f'http://127.0.0.1:{self.port}/api.php',method=method),timeout=12)
  except urllib.error.HTTPError as e:r=e
  with r:return r.status,dict(r.headers),json.load(r)
 def cache(self):return next(Path(self.temp.name).glob('monzero-chain-charts-*/observation.json'))
 def expire(self):
  p=self.cache();v=json.loads(p.read_text());v['generated_at']-=61;p.write_text(json.dumps(v))
 def test_cache_and_private_permissions(self):
  status,headers,data=self.request();self.assertEqual(status,200);self.assertEqual(len(data['blocks']),3)
  self.assertEqual(self.calls,2);self.assertEqual(self.request()[2],data);self.assertEqual(self.calls,2)
  self.assertEqual(self.cache().stat().st_mode&0o777,0o600);self.assertEqual(self.cache().parent.stat().st_mode&0o777,0o700)
  self.expire();self.assertEqual(self.request()[0],200);self.assertEqual(self.calls,4)
 def test_invalid_history_and_negative_cache(self):
  self.range['headers'][1]['prev_hash']='f'*64
  for _ in range(2):
   status,headers,data=self.request();self.assertEqual(status,502);self.assertEqual(headers['Cache-Control'],'no-store');self.assertNotIn('blocks',data)
  self.assertEqual(self.calls,2)
 def test_busy_cache_does_not_wait_or_fetch(self):
  self.request()
  with self.cache().open('r+') as f:
   fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);start=time.monotonic()
   self.assertEqual(self.request()[0],503);self.assertLess(time.monotonic()-start,1)
  self.assertEqual(self.calls,2)
 def test_shared_cache_readers_can_coexist(self):
  self.request()
  with self.cache().open('r') as f:
   fcntl.flock(f,fcntl.LOCK_SH|fcntl.LOCK_NB);self.assertEqual(self.request()[0],200)
  self.assertEqual(self.calls,2)
 def test_corrupt_or_future_cache_is_not_served(self):
  self.request();p=self.cache();v=json.loads(p.read_text());v['blocks']=[];p.write_text(json.dumps(v));self.assertEqual(len(self.request()[2]['blocks']),3)
  v=json.loads(p.read_text());v['generated_at']+=10000;p.write_text(json.dumps(v));self.assertEqual(self.request()[0],200);self.assertEqual(self.calls,6)
 def test_no_stale_success_on_upstream_failure(self):
  self.request();self.expire();type(self).upstream=503
  self.assertEqual(self.request()[0],502);self.assertEqual(self.request()[0],502);self.assertEqual(self.calls,3)
 def test_redirect_and_oversized_rejected(self):
  type(self).upstream=302;self.assertEqual(self.request()[0],502);self.assertEqual(self.calls,1)
  self.setUp();type(self).oversized=True;self.assertEqual(self.request()[0],502);self.assertEqual(self.calls,1)
 def test_wrong_method_does_no_rpc(self):
  status,headers,_=self.request('POST');self.assertEqual(status,405);self.assertEqual(headers['Allow'],'GET');self.assertEqual(headers['Cache-Control'],'no-store');self.assertEqual(self.calls,0)
if __name__=='__main__':unittest.main()
