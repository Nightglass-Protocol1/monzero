#!/bin/bash
# Print the faucet wallet's 25-word seed so the owner can write it down offline.
# Run it in your own terminal, not through an assistant or a logged session.
set -euo pipefail
EU=${EU_HOST:-monzero-eu}
ssh -o BatchMode=yes "$EU" sudo bash -s <<'REMOTE'
set -euo pipefail
curl -s -m 20 --digest -u "faucet:$(cat /etc/xmzfaucet/rpc.pass)" http://127.0.0.1:6192/json_rpc \
  -d '{"jsonrpc":"2.0","id":0,"method":"query_key","params":{"key_type":"mnemonic"}}' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["result"]["key"])'
REMOTE
