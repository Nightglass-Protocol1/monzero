"""Exercise the production PHP adapter with a loopback-only synthetic RPC server."""
import json, socket, subprocess, tempfile, threading, time, unittest, urllib.request, urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

class ObservationTest(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  class Rpc(BaseHTTPRequestHandler):
   def log_message(self,*args): pass
   def do_POST(self):
    self.rfile.read(int(self.headers.get('Content-Length',0)))
    data=cls.info if self.path=='/get_info' else {'result':{'block_header':cls.header}}
    body=json.dumps(data).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(body)
  cls.rpc=ThreadingHTTPServer(('127.0.0.1',0),Rpc)
  cls.thread=threading.Thread(target=cls.rpc.serve_forever,daemon=True);cls.thread.start()
  cls.temp=tempfile.TemporaryDirectory()
  source=(Path(__file__).resolve().parents[2]/'website/api/node-info/index.php').read_text()
  source=source.replace("http://node.monzero.org:6175",f'http://127.0.0.1:{cls.rpc.server_port}')
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
 def setUp(self):
  type(self).info={'status':'OK','nettype':'mainnet','height':100,'top_block_hash':'a'*64,'difficulty':12345,'difficulty_top64':0,'synchronized':True}
  type(self).header={'height':99,'hash':'a'*64,'reward':200000000000,'timestamp':int(time.time())}
 def get(self):
  request=urllib.request.Request(f'http://127.0.0.1:{self.port}/index.php',data=b'{}',headers={'Content-Type':'application/json'})
  with urllib.request.urlopen(request,timeout=5) as response:return json.load(response)
 def test_matching_tip(self):
  value=self.get();self.assertTrue(value['tip_fresh']);self.assertEqual(value['tip_height'],99);self.assertEqual(value['tip_reward_atomic'],200000000000)
 def test_changed_tip_is_not_bound(self):
  for field,value in [('height',100),('hash','b'*64)]:
   self.setUp();self.header[field]=value;result=self.get()
   self.assertFalse(result['tip_fresh']);self.assertIsNone(result['tip_reward_atomic']);self.assertIsNone(result['tip_height'])
 def test_server_freshness_policy(self):
  for age,accepted in [(120,True),(1000,False),(-200,True),(-400,False)]:
   self.header['timestamp']=int(time.time())-age
   self.assertEqual(self.get()['tip_fresh'],accepted)
 def test_post_only(self):
  with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(f'http://127.0.0.1:{self.port}/index.php',timeout=5)
  self.assertEqual(error.exception.code,405);error.exception.close()
if __name__=='__main__':unittest.main()
