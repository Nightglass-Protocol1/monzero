"""Exercise actual PHP asset routing with isolated upstream replies."""
import http.server,json,socket,subprocess,tempfile,threading,time,urllib.request,urllib.error
from pathlib import Path
root=Path(__file__).resolve().parents[2]
reply={}
class Upstream(http.server.BaseHTTPRequestHandler):
 def do_POST(self):
  self.rfile.read(int(self.headers.get('Content-Length',0)))
  body=json.dumps(reply).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(body)
 def log_message(self,*args):pass
upstream=http.server.ThreadingHTTPServer(('127.0.0.1',0),Upstream);threading.Thread(target=upstream.serve_forever,daemon=True).start()
try:
 with tempfile.TemporaryDirectory(prefix='monzero-explorer-') as directory:
  source=(root/'website/explorer/api.php').read_text().replace('http://node.monzero.org:6175',f'http://127.0.0.1:{upstream.server_port}')
  assert 'http://node.monzero.org:6175' not in source and f'http://127.0.0.1:{upstream.server_port}' in source
  (Path(directory)/'api.php').write_text(source)
  with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
  server=subprocess.Popen(['php','-S',f'127.0.0.1:{port}','-t',directory],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  try:
   for _ in range(50):
    try:
     with socket.create_connection(('127.0.0.1',port),timeout=.2):break
    except OSError:time.sleep(.1)
   for payload,expected in [({'error':{'code':-32601,'message':'Method not found'}},502),({'error':{'message':'Temporary backend failure'}},502),({'result':{}},502),({'result':{'status':'OK','active':False,'total':0,'assets':[]}},200),({'result':{'status':'OK','active':'false','total':0,'assets':[]}},502)]:
    reply=payload
    req=urllib.request.Request(f'http://127.0.0.1:{port}/api.php',data=b'{"action":"assets"}',headers={'Content-Type':'application/json'})
    try:response=urllib.request.urlopen(req,timeout=5)
    except urllib.error.HTTPError as e:response=e
    with response:
     data=json.load(response);assert response.status==expected,(response.status,data)
     if expected==502:assert 'supported' not in data and 'assets' not in data and 'active' not in data and 'total' not in data
     else:assert data['supported'] is True and data['assets']==[] and data['active'] is False
  finally:server.terminate();server.wait(timeout=5)
finally:upstream.shutdown();upstream.server_close()
print('Explorer assets: RPC failures and malformed observations are unavailable, valid empty registry preserved')
