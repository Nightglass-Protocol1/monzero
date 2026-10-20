"""Homepage headline banner: links, hidden duplicate copy, scrolling, pause on hover/focus/button,
reduced motion, phone width, and hidden when there is no news."""
import json,shutil,socket,subprocess,time
from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[2]
news={'schema':'monzero-news-v1','generated_at':int(time.time()),'date':'2026-10-20','window_hours':24,'sources':[{'name':'Alpha','home':'https://a.example/','region':'US','ok':True}],
 'stories':[{'title':f'Headline number {i} about bitcoin','url':f'https://a.example/{i}','source':'Alpha','published_at':int(time.time())-60,'outlets':2,'also':[]} for i in range(15)]+
          [{'title':'<img src=x onerror=alert(1)>','url':'javascript:alert(1)','source':'Alpha','published_at':1,'outlets':1,'also':[]}]}
with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
server=subprocess.Popen(['php','-S',f'127.0.0.1:{port}','-t',str(root/'website')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
try:
 for _ in range(50):
  try:
   with socket.create_connection(('127.0.0.1',port),timeout=.2):break
  except OSError:time.sleep(.1)
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True,executable_path=shutil.which('chromium'))
  def home(body,width=1440,motion='no-preference'):
   ctx=browser.new_context(viewport={'width':width,'height':900},reduced_motion=motion);page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
   def route(r):
    u=r.request.url
    if '/news/data/latest.json' in u:return r.fulfill(status=200 if body else 404,content_type='application/json',body=json.dumps(body or {}))
    if '.php' in u or '/api/' in u or not u.startswith(f'http://127.0.0.1:{port}/'):return r.fulfill(status=503,body='{}')
    r.continue_()
   page.route('**/*',route);page.goto(f'http://127.0.0.1:{port}/');page.wait_for_timeout(700);return ctx,page,errors
  ctx,page,errors=home(news)
  t=page.locator('#news-ticker');assert t.is_visible()
  assert page.evaluate("document.getElementById('news-ticker').getBoundingClientRect().bottom <= document.querySelector('.site-header').getBoundingClientRect().top+1")  # above the menu
  items=page.locator('#ticker-track li');assert items.count()==30,items.count()  # 15 safe stories twice; the unsafe one is dropped
  assert page.locator('#ticker-track li[aria-hidden="true"]').count()==15 and page.locator('#ticker-track li[aria-hidden="true"] a[tabindex="-1"]').count()==15
  first=page.locator('#ticker-track a').first;assert first.get_attribute('href')=='https://a.example/0' and first.get_attribute('rel')=='noopener noreferrer nofollow'
  assert 'javascript' not in page.content().split('id="ticker-track"')[1].split('</ul>')[0]
  anim=lambda:page.evaluate("getComputedStyle(document.getElementById('ticker-track')).animationPlayState")
  assert page.evaluate("getComputedStyle(document.getElementById('ticker-track')).animationName")=='ticker-scroll' and anim()=='running'
  x1=page.evaluate("new DOMMatrix(getComputedStyle(document.getElementById('ticker-track')).transform).m41");page.mouse.move(5,890);page.wait_for_timeout(600)
  x2=page.evaluate("new DOMMatrix(getComputedStyle(document.getElementById('ticker-track')).transform).m41");assert x2<x1,(x1,x2)  # it moves left
  box=page.locator('.ticker-viewport').bounding_box();page.mouse.move(box['x']+box['width']/2,box['y']+box['height']/2);assert anim()=='paused';page.mouse.move(5,890);assert anim()=='running'
  page.locator('#ticker-pause').click();assert anim()=='paused' and page.locator('#ticker-pause').get_attribute('aria-pressed')=='true'
  page.mouse.move(5,890);assert anim()=='paused';page.locator('#ticker-pause').click();page.mouse.move(5,890);page.locator('body').click(position={'x':5,'y':890});assert anim()=='running'
  first.focus();assert anim()=='paused'  # keyboard focus pauses too
  assert not errors,errors;ctx.close()
  ctx,page,errors=home(news,width=390)
  assert page.locator('#news-ticker').is_visible() and page.evaluate('document.documentElement.scrollWidth <= innerWidth') and not errors;ctx.close()
  ctx,page,errors=home(news,motion='reduce')
  assert page.evaluate("getComputedStyle(document.getElementById('ticker-track')).animationName")=='none' and page.locator('#ticker-pause').is_hidden()
  assert page.locator('#ticker-track li:visible').count()==15;ctx.close()
  ctx,page,errors=home(None);assert page.locator('#news-ticker').is_hidden() and not errors;ctx.close()
  browser.close()
finally:server.terminate();server.wait(timeout=5)
print('News ticker: links, hidden duplicate, unsafe links dropped, scrolling, pause on hover/focus/button, phone width, reduced motion, hidden without news passed')
