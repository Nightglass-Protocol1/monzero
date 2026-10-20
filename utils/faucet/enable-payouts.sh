#!/bin/bash
# Turn the faucet on: worker payouts on monzero-eu, then claims on the website.
# Refuses unless the faucet wallet's unlocked balance covers at least one day of payouts plus the reserve.
# Run from the owner's PC:  bash utils/faucet/enable-payouts.sh
# Undo (stops new claims at once):  ssh monzero-webspace php ~/monzero-private/faucet-config-set.php enabled false
set -euo pipefail
EU=${EU_HOST:-monzero-eu} WEB=${WEB_HOST:-monzero-webspace}
ssh -o BatchMode=yes "$EU" sudo bash -s <<'REMOTE'
set -euo pipefail
CFG=/etc/xmzfaucet/worker.json UNIT=/etc/systemd/system/xmzfaucet.service
LOGIN="faucet:$(cat /etc/xmzfaucet/rpc.pass)"
python3 - "$CFG" "$LOGIN" <<'PY'
import json, subprocess, sys
cfg = json.load(open(sys.argv[1]))
reply = subprocess.run(["curl", "-s", "-m", "20", "--digest", "-u", sys.argv[2], cfg["wallet_rpc"], "-d",
                        '{"jsonrpc":"2.0","id":0,"method":"get_balance","params":{"account_index":0}}'], capture_output=True, text=True).stdout
unlocked = int(json.loads(reply)["result"]["unlocked_balance"])
need = int(cfg["max_per_day_atomic"]) + int(cfg["reserve_atomic"])
print(f"   unlocked balance {unlocked / 1e11:.4f} XMZ, need at least {need / 1e11:.4f} XMZ")
sys.exit(0 if unlocked >= need else "!! fund the faucet wallet (and wait for the funds to unlock) first")
PY
cp -p "$CFG" "$CFG.before-payouts"; cp -p "$UNIT" "$UNIT.before-payouts"
python3 - "$CFG" <<'PY'
import json, sys
cfg = json.load(open(sys.argv[1])); cfg["enable_payouts"] = True
json.dump(cfg, open(sys.argv[1], "w"), indent=2)
PY
grep -q -- '^ExecStart=.*--enable-payouts' "$UNIT" || sed -i -E 's#^(ExecStart=/usr/bin/python3 /opt/xmzfaucet/faucet_worker.py --config /etc/xmzfaucet/worker.json)$#\1 --enable-payouts#' "$UNIT"
grep -q -- '^ExecStart=.*--enable-payouts' "$UNIT" || { echo "!! unit not updated; restoring"; cp -p "$CFG.before-payouts" "$CFG"; cp -p "$UNIT.before-payouts" "$UNIT"; exit 1; }
systemctl daemon-reload; systemctl restart xmzfaucet; sleep 5
systemctl is-active xmzfaucet
journalctl -u xmzfaucet -n 3 --no-pager -o cat
REMOTE
ssh -o BatchMode=yes "$WEB" 'php ~/monzero-private/faucet-config-set.php enabled true'
curl -s -m 15 https://monzero.org/api/faucet/; echo
