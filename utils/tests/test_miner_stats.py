"""Exercise telemetry with a temporary PHP server; no blockchain nodes needed."""
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('reporter', ROOT / 'utils/monzero-miner-reporter.py')
reporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reporter)


class MinerStats(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.data = Path(cls.temp.name) / 'stats.json'
        cls.token = 'temporary-test-ingest-token-only'
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        cls.url = f'http://127.0.0.1:{port}/api/miner-stats/'
        env = dict(os.environ, MONZERO_STATS_SECRET='test-only-hmac-secret-with-32-characters',
                   MONZERO_STATS_INGEST_TOKEN=cls.token, MONZERO_STATS_FILE=str(cls.data))
        cls.server = subprocess.Popen(['php', '-S', f'127.0.0.1:{port}', '-t', str(ROOT / 'website')],
                                      env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cls.addClassCleanup(cls.cleanup)
        for _ in range(100):
            try:
                reporter.json_request(cls.url)
                break
            except urllib.error.URLError:
                time.sleep(.05)
        else:
            raise RuntimeError('PHP test server did not start')

    @classmethod
    def cleanup(cls):
        cls.server.terminate()
        cls.server.wait(timeout=5)
        cls.temp.cleanup()

    def setUp(self):
        self.data.write_text('{}')

    def post(self, payload, token=None):
        return reporter.json_request(self.url, payload, self.token if token is None else token)

    def test_reporter_to_api_withdrawal_and_privacy(self):
        args = SimpleNamespace(rpc='http://unused.local', endpoint=self.url, token=self.token,
                               id_file=Path(self.temp.name)/'id', log=Path(self.temp.name)/'daemon.log')
        args.log.write_text('[miner 2] INFO global src/cryptonote_basic/miner.cpp:592 Found block <' +
                            'a'*64 + '> at height 42\npeer reports Found block <'+'b'*64+'> at height 43\n')
        actual_request = reporter.json_request
        status = {'status':'OK', 'active':True, 'speed':5875, 'address':'private-wallet-address'}
        def request(url, body=None, token=''):
            if url.endswith('/mining_status'):
                return status
            self.assertEqual(set(body), {'installation_id','active','hashrate','blocks_found'})
            return actual_request(url, body, token)
        with patch.object(reporter, 'json_request', side_effect=request):
            reporter.report(args)
            result = actual_request(self.url)
            self.assertEqual(result['active_miners'],1)
            self.assertEqual(result['total_hashrate'],5875)
            self.assertEqual(result['total_blocks'],1)
            self.assertTrue(result['miners'][0]['last_seen'])
            self.assertNotIn(args.id_file.read_text().strip(), json.dumps(result))
            self.assertNotIn('private-wallet-address', self.data.read_text())
            status['active'] = False
            reporter.report(args)
            self.assertEqual(actual_request(self.url)['active_miners'],0)
            status['status'] = 'BUSY'
            with self.assertRaises(RuntimeError):
                reporter.report(args)

    def test_multiple_miners_legacy_clients_expiry_and_auth(self):
        first = {'installation_id':'1'*32,'hashrate':1000,'blocks_found':2}
        second = dict(first,installation_id='2'*32,hashrate=2000,blocks_found=3,active=True)
        self.post(first)
        self.post(second)
        result = reporter.json_request(self.url)
        self.assertEqual((result['active_miners'],result['total_hashrate'],result['total_blocks']),(2,3000,5))
        self.assertEqual([m['hashrate'] for m in result['miners']],[2000,1000])
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.post(first, 'wrong-token')
        self.assertEqual(error.exception.code,401)
        error.exception.close()
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.post(dict(first,active='yes'))
        self.assertEqual(error.exception.code,400)
        error.exception.close()
        self.post(dict(first,hashrate=0))
        self.assertEqual(reporter.json_request(self.url)['active_miners'],1)
        stored = json.loads(self.data.read_text())
        for record in stored.values():
            record['updated_at'] = int(time.time()) - 181
        self.data.write_text(json.dumps(stored))
        self.assertEqual(reporter.json_request(self.url)['active_miners'],0)


if __name__ == '__main__':
    unittest.main()
