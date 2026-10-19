"""The faucet status endpoint can only report paused, and no claim route exists."""
import json,socket,subprocess,time,urllib.request,urllib.error
from pathlib import Path
root=Path(__file__).resolve().parents[2]
with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
server=subprocess.Popen(['php','-S',f'127.0.0.1:{port}','-t',str(root/'website')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
def req(path,method='GET',data=None):
 try:r=urllib.request.urlopen(urllib.request.Request(f'http://127.0.0.1:{port}{path}',method=method,data=data),timeout=5)
 except urllib.error.HTTPError as e:r=e
 with r:return r.status,r.headers,r.read()
try:
 for _ in range(50):
  try:
   with socket.create_connection(('127.0.0.1',port),timeout=.2):break
  except OSError:time.sleep(.1)
 status,h,body=req('/api/faucet/');data=json.loads(body)
 assert status==200 and data['status']=='paused' and data['schema']=='monzero-faucet-v1' and h['X-Content-Type-Options']=='nosniff'
 status,h,body=req('/api/faucet/','POST',b'{"address":"F"}');assert status==405 and json.loads(body)['status']=='paused' and 'POST' not in h['Allow']
 # No claim route exists; the dev server falls back to the status script, which still refuses.
 assert req('/api/faucet/claim/','POST',b'{}')[0]==405
 src=(root/'website/api/faucet/index.php').read_text()
 for forbidden in ['wallet','transfer','json_rpc','getenv','require','include','curl']:assert forbidden not in src.lower().replace('payouts are not implemented',''),forbidden
 page=(root/'website/faucet/index.html').read_text();assert 'Status: paused' in page and '<form' not in page and '<input' not in page
finally:server.terminate();server.wait(timeout=5)
print('Faucet: status endpoint paused-only, claims refused, no wallet/config access, page has no claim form')
