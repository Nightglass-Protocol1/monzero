"""Exercise the example Nginx routing/headers with isolated loopback PHP CGI.
Set NGINX_BINARY and NGINX_FASTCGI_PARAMS when nginx is not installed normally.
No mining, builds, production configuration changes or upstream RPC requests.
"""
import os, shutil, socket, subprocess, tempfile, time, urllib.request, urllib.error
from pathlib import Path
root=Path(__file__).resolve().parents[2]
nginx=os.environ.get('NGINX_BINARY') or shutil.which('nginx')
params=Path(os.environ.get('NGINX_FASTCGI_PARAMS','/etc/nginx/fastcgi_params'))
if not nginx or not params.is_file():raise SystemExit('Provide NGINX_BINARY and NGINX_FASTCGI_PARAMS to run this hosting check')
def free_port():
 with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]
def request(port,path,method='GET'):
 try:r=urllib.request.urlopen(urllib.request.Request(f'http://127.0.0.1:{port}'+path,method=method),timeout=5)
 except urllib.error.HTTPError as e:r=e
 with r:return r.status,r.headers,r.read()
with tempfile.TemporaryDirectory(prefix='monzero-nginx-') as directory:
 tmp=Path(directory);site=tmp/'site';site.mkdir();webport=free_port();cgiport=free_port()
 while cgiport==webport:cgiport=free_port()
 for name in ['index.html','styles.css','site-nav.js','assets/logo.webp','checksum.sha256','module.mjs','.hidden.php']:
  p=site/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('fixture')
 endpoint=site/'api/node-info/index.php';endpoint.parent.mkdir(parents=True)
 # Real adapter handles method rejection before any network request.
 endpoint.write_bytes((root/'website/api/node-info/index.php').read_bytes())
 config=(root/'website/nginx-monzero.conf').read_text().replace('listen 80;',f'listen 127.0.0.1:{webport};').replace('    listen [::]:80;','').replace('/var/www/monzero',str(site)).replace('include fastcgi_params;',f'include {params};').replace('unix:/run/php/php-fpm.sock',f'127.0.0.1:{cgiport}')
 config='daemon off; master_process off;\npid '+str(tmp/'nginx.pid')+';\nerror_log stderr;\nevents {}\nhttp { access_log off; client_body_temp_path '+str(tmp/'body')+'; fastcgi_temp_path '+str(tmp/'fastcgi')+'; proxy_temp_path '+str(tmp/'proxy')+'; uwsgi_temp_path '+str(tmp/'uwsgi')+'; scgi_temp_path '+str(tmp/'scgi')+';\n'+config+'\n}'
 mime=params.parent/'mime.types'
 if mime.is_file():config=config.replace('http {', 'http { include '+str(mime)+';',1)
 conf=tmp/'nginx.conf';conf.write_text(config)
 subprocess.run([nginx,'-t','-p',str(tmp)+'/', '-c',str(conf)],check=True,capture_output=True)
 processes=[]
 try:
  processes.append(subprocess.Popen(['php-cgi','-d','opcache.enable=0','-b',f'127.0.0.1:{cgiport}'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
  processes.append(subprocess.Popen([nginx,'-p',str(tmp)+'/', '-c',str(conf)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
  for _ in range(50):
   try:
    with socket.create_connection(('127.0.0.1',webport),timeout=.2):pass
    with socket.create_connection(('127.0.0.1',cgiport),timeout=.2):pass
    break
   except OSError:time.sleep(.1)
  else:raise RuntimeError('Preview servers did not start')
  for path,expected in [('/',200),('/styles.css',200),('/site-nav.js',200),('/checksum.sha256',200),('/module.mjs',200),('/assets/logo.webp',200),('/missing',404),('/.hidden.php',403),('/api/node-info/',405),('/api/node-info/index.php',405)]:
   status,headers,body=request(webport,path);assert status==expected,(path,status,body)
   for key in ['Content-Security-Policy','X-Content-Type-Options','X-Frame-Options','Referrer-Policy','Permissions-Policy','Strict-Transport-Security']:
    assert headers.get(key),(path,key)
   if 'node-info' in path:
    assert b'METHOD_NOT_ALLOWED' in body and b'<?php' not in body
    assert headers.get('Allow')=='POST' and headers.get('Cache-Control')=='no-store'
   if path=='/styles.css' and mime.is_file():assert headers['Content-Type'].startswith('text/css')
   if path=='/module.mjs':assert 'javascript' in headers['Content-Type']
   if path=='/checksum.sha256':assert headers['Content-Type'].startswith('text/plain')
   if path in ['/styles.css','/site-nav.js','/checksum.sha256']:assert 'max-age=604800' in headers['Cache-Control']
  class NoRedirect(urllib.request.HTTPRedirectHandler):
   def redirect_request(self,*args,**kwargs):return None
  opener=urllib.request.build_opener(NoRedirect)
  for path,method,expected,target in [('/assets','GET',301,'/assets/'),('/api/node-info','POST',308,'/api/node-info/')]:
   try:opener.open(urllib.request.Request(f'http://127.0.0.1:{webport}'+path,method=method))
   except urllib.error.HTTPError as response:
    with response:assert response.code==expected and response.headers['Location']==target,(path,response.code,response.headers)
   else:raise AssertionError('Expected redirect')
  # Instrument the script only to check that directory routing preserves POST.
  endpoint.write_text('<?php header("Content-Type: application/json"); echo json_encode(["method"=>$_SERVER["REQUEST_METHOD"]]);')
  status,headers,body=request(webport,'/api/node-info/','POST')
  assert status==200 and b'"method":"POST"' in body,(status,body)
  print('Nginx: PHP directory routing, POST preservation, error/static security headers, MIME, cache and dotfile protection passed')
 finally:
  for process in processes:process.terminate()
  for process in processes:
   try:process.wait(timeout=5)
   except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
