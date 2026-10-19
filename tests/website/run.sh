#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
node --check website/app.js
node --check website/mining/calculator/calculator.mjs
node --test tests/website/mining-calculator.test.mjs
php -l website/api/node-info/index.php
python3 tests/website/test_node_observation.py
MONZERO_TEST_STREAM_HTTP=1 python3 tests/website/test_node_observation.py
python3 tests/website/check_calculator_browser.py
python3 tests/website/check_home_network.py

php -l website/mining/dashboard/api.php
php tests/website/pool-contract.php
python3 tests/website/test_pool_api.py
node --check website/mining/dashboard/dashboard.mjs
node --test tests/website/pool-history.test.mjs tests/website/worker-labels.test.mjs tests/website/pool-alerts.test.mjs
python3 tests/website/check_pool_dashboard.py
python3 tests/website/check_pool_alerts.py

node --check website/mining/benchmarks/benchmarks.mjs
node utils/website/validate_benchmarks.mjs
node --test tests/website/benchmarks.test.mjs
python3 tests/website/check_benchmarks.py

node --check website/site-nav.js
python3 tests/website/check_navigation.py

php -l website/stats/api.php
php tests/website/stats-contract.php
python3 tests/website/test_stats_api.py
MONZERO_TEST_STREAM_HTTP=1 python3 tests/website/test_stats_api.py
python3 tests/website/test_network_history.py
node --test tests/website/network-history.test.mjs
node --check website/network/network.mjs
python3 tests/website/check_network_history.py
node --test tests/website/network-blocks.test.mjs
node --test tests/website/difficulty-alerts.test.mjs
node --test tests/website/bounties.test.mjs
node --check website/community/bounties/board.mjs
python3 tests/website/check_bounties.py
php -l website/explorer/api.php
node --check website/explorer/app.js
python3 tests/website/test_explorer_assets.py
python3 tests/website/check_explorer_assets.py
node --check website/payments/request/request.mjs
node --test tests/website/payment-request.test.mjs
python3 tests/website/check_payment_request.py
