"""Read-only redesign acceptance: responsive documents, navigation and safe data failures."""
import shutil, socket, subprocess, time
from pathlib import Path
from urllib.parse import urlsplit, unquote
from playwright.sync_api import sync_playwright
root = Path(__file__).resolve().parents[2]
with socket.socket() as sock:
    sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
server = subprocess.Popen(['php', '-S', f'127.0.0.1:{port}', '-t', str(root / 'website')], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
base = f'http://127.0.0.1:{port}'
try:
    time.sleep(.4)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=shutil.which('chromium'), headless=True)
        for width in (320, 390, 768, 1440):
            page = browser.new_page(viewport={'width': width, 'height': 1000}, reduced_motion='reduce')
            errors = []; page.on('pageerror', lambda err: errors.append(str(err)))
            def route(r):
                url = r.request.url
                if '/api/' in url or '/explorer/api.php' in url or not url.startswith(base):
                    r.fulfill(status=503, json={'error': 'fixture outage'})
                else: r.continue_()
            page.route('**/*', route)
            for path in ('/', '/download/', '/mining/', '/privacy/', '/terms/'):
                page.goto(base + path)
                assert page.locator('h1').count() == 1
                assert page.locator('.header-cta').is_visible(), (width,path)
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), (width, path)
                for href in page.locator('a[href]').evaluate_all('(links) => links.map(a => a.href)'):
                    url = urlsplit(href)
                    if url.netloc != urlsplit(base).netloc: continue
                    target = root / 'website' / unquote(url.path.lstrip('/'))
                    # Existing deployment-managed release artifacts are intentionally absent locally.
                    if url.path.startswith(('/downloads/', '/releases/')) or url.path == '/WHITEPAPER.md': continue
                    assert target.exists(), href
                    if url.path == path and url.fragment:
                        assert page.locator('[id="' + unquote(url.fragment) + '"]').count(), href
                if path == '/':
                    badge = page.locator('.hero .chainquiry-badge')
                    assert badge.get_attribute('href') == 'https://chainquiry.com/projects/monzero/'
                    assert 'motion=still' in badge.locator('img').evaluate('(img) => img.currentSrc')
                    assert badge.locator('img').get_attribute('width') == '288'
                    assert page.locator('.community-links a[href="https://x.com/MonzeroXMZ"]').count() == 1
                    page.wait_for_function("document.querySelector('#support-status').textContent.includes('unavailable')")
                    assert page.locator('#support-raised').inner_text() == '—'
                    assert page.locator('#news-ticker').count() == 0
                    assert page.locator('.header-cta').is_visible()
                    if width < 1340:
                        page.locator('.menu-toggle').click()
                        page.locator('#nav-sub-mining').locator('..').locator('button').click()
                        assert page.locator('#nav-sub-mining').is_visible()
                        page.keyboard.press('Escape')
                        assert page.locator('.menu-toggle').evaluate('(b) => b === document.activeElement')
                    page.screenshot(path=f'/tmp/monzero-home-{width}.png', full_page=True)
                    page.screenshot(path=f'/tmp/monzero-hero-{width}.png')
            assert not errors, errors
            page.close()
        page = browser.new_page(java_script_enabled=False, viewport={'width':390,'height':900})
        page.goto(base)
        assert page.locator('#site-nav').is_visible()
        assert page.locator('#nav-sub-mining a').first.is_visible()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.keyboard.press('Tab')
        assert page.locator('.skip-link').evaluate('(a) => a === document.activeElement')
        page.keyboard.press('Enter')
        page.wait_for_function("document.activeElement.id === 'main'")
        page.close()
        # A delayed navigation script must not collapse a full-page mobile menu
        # after first paint. No-JS navigation is enabled by its own stylesheet.
        page = browser.new_page(viewport={'width':390,'height':900})
        page.add_init_script("""
          window.layoutShifts = [];
          new PerformanceObserver(list => {
            for (const entry of list.getEntries()) if (!entry.hadRecentInput) layoutShifts.push(entry.value);
          }).observe({type:'layout-shift', buffered:true});
        """)
        def slow_route(r):
            if 'site-nav.js' in r.request.url: time.sleep(.8); r.continue_()
            elif '/api/' in r.request.url or '/api.php' in r.request.url or not r.request.url.startswith(base):
                r.fulfill(status=503, json={'error':'fixture outage'})
            else: r.continue_()
        page.route('**/*', slow_route)
        page.goto(base)
        page.wait_for_timeout(1200)
        assert page.evaluate('layoutShifts.reduce((a,b)=>a+b,0)') < .1
        browser.close()
    print('Redesign: 5 documents, local links, 4 widths, Chainquiry/X, reduced motion, outage placeholders, keyboard, no-JS navigation and delayed-script layout stability passed')
finally:
    server.terminate(); server.wait(timeout=5)
