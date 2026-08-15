#!/usr/bin/env bash
set -euo pipefail

RPC_PORT="${MONZERO_RPC_PORT:-16175}"
MINER_ADDRESS="${MONZERO_MINER_ADDRESS:-FR3j29tPrro5vdgMvFMyQr4W7VX41VzRHKjvhhNm5EB32MUFTiKFW21PCDrvUM5hvSQLYBom4jmY1AehUJKKtZbXH1uQ5u6}"
THREADS="${1:-${MONZERO_MINER_THREADS:-1}}"
RPC_URL="http://127.0.0.1:$RPC_PORT"

if ! [[ "$THREADS" =~ ^[1-9][0-9]*$ ]]; then
  printf 'Error: thread count must be a positive integer.\n' >&2
  printf 'Usage: %s [threads]\n' "$0" >&2
  exit 1
fi

if ! curl --silent --fail --max-time 2 \
  --header 'Content-Type: application/json' \
  --data '{}' "$RPC_URL/get_info" >/dev/null; then
  printf 'Error: the Monzero daemon is not running at 127.0.0.1:%s.\n' "$RPC_PORT" >&2
  printf 'Start it separately with ./start-monzerod.sh\n' >&2
  exit 1
fi

response="$(curl --silent --show-error --fail --max-time 10 \
  --header 'Content-Type: application/json' \
  --data "{\"miner_address\":\"$MINER_ADDRESS\",\"threads_count\":$THREADS,\"do_background_mining\":false,\"ignore_battery\":true}" \
  "$RPC_URL/start_mining")"

python3 - "$response" "$THREADS" "$MINER_ADDRESS" <<'PY'
import json
import sys

data = json.loads(sys.argv[1])
status = data.get("status", "")
if status != "OK":
    raise SystemExit(f"Mining failed: {data.get('error_details') or status or data}")
print(f"Mining started with {sys.argv[2]} thread(s).")
print(f"Rewards address: {sys.argv[3]}")
PY
