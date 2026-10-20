#!/bin/bash
# Split the faucet wallet's balance into 16 outputs sent to itself, so one payout's locked change
# does not block the next claims. Run after funding or refilling (a refill arrives as one output).
# Pauses the payout worker meanwhile; claims stay queued. Run from the owner's PC:
#   bash utils/faucet/split-outputs.sh
set -euo pipefail
EU=${EU_HOST:-monzero-eu}
ssh -o BatchMode=yes "$EU" sudo bash -s <<'REMOTE'
set -euo pipefail
systemctl stop xmzfaucet
trap 'systemctl start xmzfaucet' EXIT
python3 - <<'PY'
import json, subprocess, sys, time
OUTPUTS = 16
login = "faucet:" + open("/etc/xmzfaucet/rpc.pass").read().strip()

def rpc(method, params):
    out = subprocess.run(["curl", "-s", "-m", "120", "--digest", "-u", login, "http://127.0.0.1:6192/json_rpc", "-d",
                          json.dumps({"jsonrpc": "2.0", "id": 0, "method": method, "params": params})], capture_output=True, text=True).stdout
    reply = json.loads(out)
    if "error" in reply: sys.exit(f"!! {method}: {reply['error']}")
    return reply["result"]

own = rpc("get_address", {"account_index": 0})["address"]
for _ in range(80):
    bal = rpc("get_balance", {"account_index": 0})
    if int(bal["balance"]) > 0 and int(bal["unlocked_balance"]) == int(bal["balance"]): break
    print(f"   waiting: {bal.get('blocks_to_unlock')} blocks to unlock", flush=True); time.sleep(30)
else:
    sys.exit("!! funds still locked after 40 minutes; nothing sent")
unlocked = int(bal["unlocked_balance"])
each = (unlocked - 2 * 10**10) // OUTPUTS  # leave 0.2 XMZ for the fee; the change becomes the 16th output
cfg = json.load(open("/etc/xmzfaucet/worker.json"))
need = int(cfg["amount_atomic"]) + int(cfg["reserve_atomic"])  # each output must cover one payout plus the reserve
if each < need: sys.exit(f"!! only {unlocked / 1e11} XMZ unlocked; outputs of {each / 1e11:.4f} XMZ would be below {need / 1e11:.4f} XMZ")
tx = rpc("transfer", {"destinations": [{"amount": each, "address": own}] * (OUTPUTS - 1), "account_index": 0, "priority": 0})
print(f"   split {unlocked / 1e11:.4f} XMZ into {OUTPUTS} outputs of about {each / 1e11:.4f} XMZ: tx {tx['tx_hash']} fee {int(tx['fee']) / 1e11:.8f} XMZ")
print("   claims stay queued until the outputs unlock (about 10 blocks)")
PY
REMOTE
