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
python3 -I utils/website/nav_submenus.py --check
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
node --check website/exchanges/exchanges.mjs
node --test tests/website/exchanges.test.mjs
python3 tests/website/check_exchanges.py
node --check website/ecosystem/ecosystem.mjs
node --test tests/website/ecosystem.test.mjs
python3 tests/website/check_ecosystem.py
python3 tests/website/test_node_census.py
python3 tests/website/test_history_upload.py
python3 tests/website/test_deploy.py
for f in $(find website/api/v1 -name "*.php"); do php -l "$f"; done
python3 tests/website/test_api_v1.py
node --check website/mining/leaderboard/leaderboard.mjs
node --test tests/website/leaderboard.test.mjs
python3 tests/website/check_leaderboard.py
php -l website/admin/lib.php; php -l website/admin/index.php; php -l website/admin/bootstrap.php
# Admin storage needs pdo_sqlite (present on the production host); say so loudly when missing.
if php -m | grep -qx pdo_sqlite; then python3 tests/website/test_admin.py; else echo "SKIPPED test_admin.py: this PHP lacks pdo_sqlite (run with PHP 8.3 + pdo_sqlite)"; fi
for f in website/lib/auth.php website/lib/xmz-address.php website/faucet/lib.php website/faucet/index.php website/api/faucet/index.php website/api/faucet/worker/index.php; do php -l "$f"; done
python3 -m py_compile utils/faucet/faucet_worker.py
# The faucet needs pdo_sqlite and gmp (both on the production host).
if php -m | grep -qx pdo_sqlite && php -m | grep -qx gmp; then python3 tests/website/test_faucet.py; else echo "SKIPPED test_faucet.py: this PHP lacks pdo_sqlite or gmp (run with PHP 8.3 + pdo_sqlite + gmp)"; fi
