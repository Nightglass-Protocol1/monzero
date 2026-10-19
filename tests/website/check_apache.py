"""Isolated .htaccess MIME/cache/header checks; no production changes or PHP.
Requires httpd with dynamic modules; paths may be set through HTTPD_BINARY,
HTTPD_MODULES and HTTPD_MIME_TYPES. Tests static policy without rewrite first,
then separately tests the HTTPS redirect. This is not a TLS/PHP-FPM test.
"""
import os,shutil,socket,subprocess,tempfile,time,urllib.request,urllib.error
from pathlib import Path
root=Path(__file__).resolve().parents[2]
binary=os.environ.get('HTTPD_BINARY') or shutil.which('httpd')
modules=Path(os.environ.get('HTTPD_MODULES','/usr/lib/httpd/modules'))
mime=Path(os.environ.get('HTTPD_MIME_TYPES','/etc/httpd/conf/mime.types'))
if not binary or not mime.is_file():raise SystemExit('Provide Apache executable, modules and mime.types paths')
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None
opener=urllib.request.build_opener(NoRedirect)
with tempfile.TemporaryDirectory(prefix='monzero-apache-') as directory:
 tmp=Path(directory);site=tmp/'site';site.mkdir()
 (site/'.htaccess').write_bytes((root/'website/.htaccess').read_bytes())
 for name in ['index.html','main.mjs','catalog.json','styles.css','main.js','release.zip.sha256']:(site/name).write_text('fixture')
 data=site/'network/data';data.mkdir(parents=True)
 (data/'.htaccess').write_bytes((root/'website/network/data/.htaccess').read_bytes())
 (data/'24h.json').write_text('{}')
 for rewrite in [False,True]:
  with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
  names=['mpm_event','authz_core','unixd','dir','mime','headers','expires']+(['rewrite'] if rewrite else [])
  config=f'ServerRoot "{tmp}"\nPidFile "{tmp}/httpd.pid"\nListen 127.0.0.1:{port}\nServerName localhost\nErrorLog "{tmp}/error.log"\n'
  config+=''.join(f'LoadModule {name}_module "{modules}/mod_{name}.so"\n' for name in names)
  config+='ExpiresActive On\nExpiresDefault "access plus 7 days"\n'
  config+=f'TypesConfig "{mime}"\nDocumentRoot "{site}"\nDirectoryIndex index.html\n<Directory "{site}">\nAllowOverride All\nRequire all granted\n</Directory>\n'
  conf=tmp/'httpd.conf';conf.write_text(config)
  subprocess.run([binary,'-t','-f',str(conf)],check=True,capture_output=True)
  server=subprocess.Popen([binary,'-f',str(conf),'-DFOREGROUND'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  try:
   for _ in range(50):
    try:
     with socket.create_connection(('127.0.0.1',port),timeout=.2):break
    except OSError:time.sleep(.1)
   else:raise RuntimeError((tmp/'error.log').read_text())
   for path in ['/','/main.mjs','/catalog.json','/main.js','/styles.css','/release.zip.sha256','/network/data/24h.json','/missing']:
    try:response=opener.open(f'http://127.0.0.1:{port}'+path,timeout=5)
    except urllib.error.HTTPError as error:response=error
    with response:
     if rewrite:
      assert response.status==301,(path,response.status)
      assert response.headers['Location']=='https://monzero.org'+path
      continue
     assert response.status==(404 if path=='/missing' else 200),(path,response.status,(tmp/'error.log').read_text())
     for header in ['Content-Security-Policy','X-Frame-Options','X-Content-Type-Options','Referrer-Policy','Permissions-Policy','Strict-Transport-Security']:assert response.headers.get(header),(path,header)
     if path in ['/main.mjs','/catalog.json','/network/data/24h.json']:
      assert response.headers.get_all('Cache-Control')==['no-cache']
      assert response.headers.get('Expires') is None
     if path=='/main.mjs':
      assert response.headers['Content-Type'].startswith('text/javascript') and response.headers['Cache-Control']=='no-cache'
      conditional=urllib.request.Request(f'http://127.0.0.1:{port}'+path,headers={'If-None-Match':response.headers['ETag']})
      try:opener.open(conditional,timeout=5)
      except urllib.error.HTTPError as cached:
       with cached:
        assert cached.code==304 and cached.headers.get_all('Cache-Control')==['no-cache']
        assert cached.headers.get('Content-Security-Policy')
      else:raise AssertionError('Expected module revalidation response')
     if path=='/release.zip.sha256':assert response.headers['Content-Type'].startswith('text/plain')
     if path in ['/styles.css','/main.js']:assert 'max-age=604800' in response.headers['Cache-Control']
   print('Apache HTTPS redirect passed' if rewrite else 'Apache module MIME/revalidation, checksum MIME, static cache and security/error headers passed')
  finally:
   server.terminate()
   try:server.wait(timeout=5)
   except subprocess.TimeoutExpired:server.kill();server.wait(timeout=5)
