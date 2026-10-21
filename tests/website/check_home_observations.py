"""Browser fixtures for malformed/stale public observations; no network services started."""
import copy, shutil, socket, subprocess, time
from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[2]
with socket.socket() as sock:
    sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
base=f'http://127.0.0.1:{port}'
server=subprocess.Popen(['php','-S',f'127.0.0.1:{port}','-t',str(root/'website')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
now=int(time.time())
valid={
 '/api/v1/supply/':{'schema':'monzero-api-v1','observed_at':now,'data':{'circulating_supply':'1234.567'}},
 '/api/v1/network/nodes/':{'data':{'stale':False,'totals':{'observed':2},'countries':{'GB':{'observed':2}}}},
 '/api/status/':{'overall':'ok','checks':[{'id':'faucet','state':'ok','days_left':5}]},
 '/api/faucet/':{'status':'open'}
}
try:
    time.sleep(.4)
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,executable_path=shutil.which('chromium'))
        def open_fixture(fixtures):
            page=browser.new_page();errors=[];page.on('pageerror',lambda err:errors.append(str(err)))
            def handle(route):
                url=route.request.url
                for path,body in fixtures.items():
                    if url.endswith(path):return route.fulfill(json=body)
                if '/api/' in url or not url.startswith(base):return route.fulfill(status=503,json={})
                route.continue_()
            page.route('**/*',handle);page.goto(base)
            page.wait_for_function("!document.querySelector('#supply-note').textContent.startsWith('Loading') && document.querySelector('#tile-status').textContent !== '—'") if fixtures is valid else page.wait_for_timeout(400)
            return page,errors
        page,errors=open_fixture(valid)
        assert page.locator('#metric-supply').inner_text()=='1,234 XMZ'
        assert page.locator('#tile-status').inner_text()=='All working'
        assert page.locator('#tile-faucet').inner_text()=='Open'
        assert not errors;page.close()
        for value in ['', ' ', 'NaN', 'Infinity','1e3','-1',1234,None]:
            fixture=copy.deepcopy(valid);fixture['/api/v1/supply/']['data']['circulating_supply']=value
            page,errors=open_fixture(fixture)
            assert page.locator('#metric-supply').inner_text()=='Unavailable',value
            assert not errors;page.close()
        fixture=copy.deepcopy(valid);fixture['/api/v1/supply/']['observed_at']=now-3600
        page,errors=open_fixture(fixture);assert '(stale)' in page.locator('#supply-note').inner_text();page.close()
        fixture=copy.deepcopy(valid);fixture['/api/v1/supply/']['observed_at']=now+3600
        fixture['/api/v1/network/nodes/']['data']['totals']['observed']=-1
        fixture['/api/status/']={};fixture['/api/faucet/']={}
        page,errors=open_fixture(fixture)
        for key in ['metric-supply','tile-nodes','tile-faucet','tile-status']:
            assert page.locator('#'+key).inner_text() in ['Unavailable','—'],key
        assert 'unavailable' in page.locator('#tile-faucet-detail').inner_text()
        assert not errors;page.close()
        browser.close()
    print('Homepage data: valid supply, malformed/empty amounts, stale/future timestamps, invalid census/faucet/service states passed')
finally:
    server.terminate();server.wait(timeout=5)
