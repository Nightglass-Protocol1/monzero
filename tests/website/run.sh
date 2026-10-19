#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
node --check website/app.js
node --check website/mining/calculator/calculator.mjs
node --test tests/website/mining-calculator.test.mjs
php -l website/api/node-info/index.php
python3 tests/website/test_node_observation.py
python3 tests/website/check_calculator_browser.py
python3 tests/website/check_home_network.py

php -l website/mining/dashboard/api.php
php tests/website/pool-contract.php
python3 tests/website/test_pool_api.py
node --check website/mining/dashboard/dashboard.mjs
python3 tests/website/check_pool_dashboard.py

node --check website/mining/benchmarks/benchmarks.mjs
node --test tests/website/benchmarks.test.mjs
python3 tests/website/check_benchmarks.py

python3 utils/website/sync_navigation.py --check
node --check website/site-nav.js
python3 tests/website/check_navigation.py
