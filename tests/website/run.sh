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
