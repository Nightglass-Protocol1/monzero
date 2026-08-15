#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
WALLET_BIN="${MONZERO_WALLET_CLI_BIN:-$PROJECT_DIR/build/bin/monzero-wallet-cli}"
RPC_PORT="${MONZERO_RPC_PORT:-16175}"
DEFAULT_WALLET="${MONZERO_WALLET_FILE:-$HOME/Documents/Wallet1/Wallet1}"
WALLET_FILE="${1:-$DEFAULT_WALLET}"

if [[ ! -x "$WALLET_BIN" ]]; then
  printf 'Error: wallet executable not found: %s\n' "$WALLET_BIN" >&2
  exit 1
fi

if [[ ! -f "$WALLET_FILE.keys" ]]; then
  printf 'Error: wallet key file not found: %s.keys\n' "$WALLET_FILE" >&2
  printf 'Pass an existing wallet path as the first argument, for example:\n' >&2
  printf '  %s /path/to/wallet\n' "$0" >&2
  exit 1
fi

if ! curl --silent --fail --max-time 2 \
  --header 'Content-Type: application/json' \
  --data '{}' \
  "http://127.0.0.1:$RPC_PORT/get_info" >/dev/null 2>&1; then
  printf 'Error: the Monzero daemon is not running at 127.0.0.1:%s.\n' "$RPC_PORT" >&2
  printf 'Start it separately with: %s/start-monzerod.sh\n' "$PROJECT_DIR" >&2
  exit 1
fi

exec "$WALLET_BIN" \
  --wallet-file "$WALLET_FILE" \
  --daemon-address "127.0.0.1:$RPC_PORT"
