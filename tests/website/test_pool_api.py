"""PHP HTTP boundary checks using an explicitly replaced synthetic transport."""
import json, shutil, socket, subprocess, tempfile, time, unittest, urllib.request, urllib.error
from pathlib import Path
class PoolApi(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory();cls.root=Path(cls.temp.name)
  source=Path(__file__).resolve().parents[2]/'website/mining/dashboard'
  shutil.copy(source/'contract.php',cls.root/'contract.php')
  code=(source/'api.php').read_text()
  code=code.replace("sys_get_temp_dir().'/monzero-pool-dashboard-v1'", "__DIR__.'/private-state'")
  # Only the external transport is replaced. Request guards/cache/limits/normalizer
  # are the actual production code; this does not prove production TLS behavior.
  code=code[:code.index('function dashboardFetch(string $path): array {')]+'''function dashboardFetch(string $path): array {
    file_put_contents(__DIR__.'/calls',"call\\n",FILE_APPEND);
    if($path==='/api/stats')return ['config'=>['coin'=>'monzero','coinUnits'=>100000000000],'pool'=>['hashrate'=>2000]];
    parse_str(parse_url($path,PHP_URL_QUERY),$args);
    return ['address'=>$args['address'],'hashrate'=>1000,'pending'=>'9007199254740993','paid'=>0,'workers'=>[],'payments'=>[]];
}
'''
  (cls.root/'api.php').write_text(code)
  with socket.socket() as s:s.bind(('127.0.0.1',0));cls.port=s.getsockname()[1]
  cls.server=subprocess.Popen(['php','-S',f'127.0.0.1:{cls.port}','-t',cls.temp.name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  for _ in range(50):
   try:
    with socket.create_connection(('127.0.0.1',cls.port),timeout=.2):break
   except OSError:time.sleep(.1)
  else:raise RuntimeError('Preview server did not start')
 @classmethod
 def tearDownClass(cls):cls.server.terminate();cls.server.wait(timeout=5);cls.temp.cleanup()
 def setUp(self):
  shutil.rmtree(self.root/'private-state',ignore_errors=True)
  (self.root/'calls').unlink(missing_ok=True)
 def request(self,data=None,query='',headers=None):
  r=urllib.request.Request(f'http://127.0.0.1:{self.port}/api.php'+query,data=data,headers={'Content-Type':'application/json',**(headers or {})})
  try:response=urllib.request.urlopen(r,timeout=5)
  except urllib.error.HTTPError as error:response=error
  with response:return response.status,json.load(response),response.headers
 def body(self,char='1'):return json.dumps({'address':'F'+char*94}).encode()
 def test_read_boundary(self):
  for data,query,headers,expected in [(None,'',{},405),(b'{}','',{},400),(b'x'*2049,'',{},413),(self.body(),'?address=leak',{},400),(self.body(),'',{},200)][:4]:
   self.assertEqual(self.request(data,query,headers)[0],expected)
  self.assertEqual(self.request(self.body(),headers={'Sec-Fetch-Site':'cross-site'})[0],403)
  self.assertFalse((self.root/'calls').exists())
 def test_cache_precision_and_limit(self):
  status,data,headers=self.request(self.body());self.assertEqual(status,200)
  self.assertEqual(data['pending_atomic'],'9007199254740993');self.assertNotIn('address',data)
  self.assertEqual(headers['Cache-Control'],'no-store')
  self.request(self.body());self.assertEqual((self.root/'calls').read_text().count('call'),3)
  self.request(self.body('2'));self.assertEqual((self.root/'calls').read_text().count('call'),4)
  for _ in range(7):self.assertEqual(self.request(self.body())[0],200)
  self.assertEqual(self.request(self.body())[0],429)
  state=(self.root/'private-state/state.json').read_text()
  self.assertNotIn('F'+'1'*94,state);self.assertNotIn('127.0.0.1',state);self.assertNotIn('9007199254740993',state)
if __name__=='__main__':unittest.main()
