"""Maintain static shared navigation. --check is read-only; --write edits sources.
No build process or runtime dependency is introduced.
"""
import argparse, html, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]/'website'
LINKS=[('/', 'Home'),('/#download','Download'),('/explorer/','Explorer'),('/explorer/#/assets','Assets & NFTs'),('/stats/','Network stats'),('/wallets/','Public wallets'),
('/app/','Studio'),('/roadmap/','Roadmap'),('/WHITEPAPER.md?rev=1.5-20261017','Whitepaper'),
('/#mine','Mining guide'),('/mining/calculator/','Mining calculator'),('/mining/dashboard/','Mining dashboard'),
('/mining/benchmarks/','CPU benchmarks'),('https://pool.monzero.org/','Mining pool'),('/founder/','Founder'),
('/fund/','Donate'),('/security/','Security'),('https://t.me/MonzeroOfficial','Community')]
def updated(path):
 text=path.read_text();header=re.search(r'<header\b[^>]*class="[^"]*site-header[^"]*"[^>]*>.*?</header>',text,re.S)
 if not header:return text
 current='/'+str(path.parent.relative_to(ROOT)).strip('.')+'/'
 current=current.replace('//','/')
 links=''.join('<a href="'+html.escape(url,quote=True)+'"'+(' aria-current="page"' if url==current else '')+'>'+html.escape(label)+'</a>' for url,label in LINKS)
 nav='<nav id="site-nav" aria-label="Primary navigation">'+links+'</nav>'
 part=header.group();part=re.sub(r'<nav\b.*?</nav>',nav,part,count=1,flags=re.S)
 if 'menu-toggle' not in part:part=part.replace(nav,'<button class="menu-toggle" type="button" aria-expanded="false" aria-controls="site-nav">Menu</button>'+nav)
 text=text[:header.start()]+part+text[header.end():]
 # Load shared styles after page styles, so responsive behavior is consistent.
 text=re.sub(r'<link\b[^>]*href="[^"]*site-nav\.css[^\"]*"[^>]*>\s*','',text)
 text=text.replace('</head>','<link rel="stylesheet" href="/site-nav.css?v=20261019-navigation"></head>')
 text=re.sub(r'<script\b[^>]*src="[^"]*site-nav\.js[^\"]*"[^>]*></script>\s*','',text)
 text=text.replace('</body>','<script src="/site-nav.js?v=20261019-navigation" defer></script></body>')
 return text
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--write',action='store_true');parser.add_argument('--check',action='store_true');args=parser.parse_args()
 changed=[]
 for path in ROOT.rglob('index.html'):
  result=updated(path)
  if result!=path.read_text():
   changed.append(str(path.relative_to(ROOT)))
   if args.write:path.write_text(result)
 if changed:print(('Updated: ' if args.write else 'Navigation differs: ')+', '.join(changed))
 else:print('Shared navigation is consistent')
 if changed and not args.write:raise SystemExit(1)
