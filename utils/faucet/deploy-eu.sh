#!/bin/bash
# Install the faucet hot wallet and payout worker on monzero-eu, and give the website the
# shared worker secret. Payouts stay OFF: the worker runs as a dry run until enable-payouts.sh.
# Safe to re-run: existing wallet, passwords, secret and worker.json are kept.
# Run from the owner's PC:  bash utils/faucet/deploy-eu.sh
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
EU=${EU_HOST:-monzero-eu} WEB=${WEB_HOST:-monzero-webspace}

echo "== copying the worker to $EU"
scp -q "$HERE/faucet_worker.py" "$EU:/tmp/faucet_worker.py"
ssh -o BatchMode=yes "$EU" sudo bash -s <<'REMOTE'
set -euo pipefail
rpc() { local params=${3:-"{}"}; curl -s -m 20 "http://127.0.0.1:$1/json_rpc" -d "{\"jsonrpc\":\"2.0\",\"id\":0,\"method\":\"$2\",\"params\":$params}" ${4:+--digest -u "$4"}; }
[ -x /usr/bin/monzero-wallet-rpc ] || { echo "!! /usr/bin/monzero-wallet-rpc missing (installed by the pool deploy)"; exit 1; }
id xmzfaucet >/dev/null 2>&1 || useradd --system --home /var/lib/xmzfaucet --shell /usr/sbin/nologin xmzfaucet
install -d -o xmzfaucet -g xmzfaucet -m 700 /var/lib/xmzfaucet
install -d -o root -g xmzfaucet -m 750 /etc/xmzfaucet
install -d -o root -g root -m 755 /opt/xmzfaucet
install -o root -g root -m 644 /tmp/faucet_worker.py /opt/xmzfaucet/faucet_worker.py && rm -f /tmp/faucet_worker.py
gen() { head -c 32 /dev/urandom | base64 | tr -d '/+='; }
(umask 077
 [ -s /etc/xmzfaucet/wallet.pass ] || gen > /etc/xmzfaucet/wallet.pass
 [ -s /etc/xmzfaucet/rpc.pass ] || gen > /etc/xmzfaucet/rpc.pass
 [ -s /etc/xmzfaucet/worker-secret ] || openssl rand -hex 32 > /etc/xmzfaucet/worker-secret)
chown root:xmzfaucet /etc/xmzfaucet/wallet.pass /etc/xmzfaucet/rpc.pass /etc/xmzfaucet/worker-secret
chmod 640 /etc/xmzfaucet/wallet.pass /etc/xmzfaucet/rpc.pass /etc/xmzfaucet/worker-secret
LOGIN="faucet:$(cat /etc/xmzfaucet/rpc.pass)"

echo "== faucet wallet"
if [ ! -f /var/lib/xmzfaucet/faucet.keys ]; then
  sudo -u xmzfaucet /usr/bin/monzero-wallet-rpc --daemon-address 127.0.0.1:6185 --trusted-daemon --rpc-bind-ip 127.0.0.1 \
    --rpc-bind-port 6193 --disable-rpc-login --wallet-dir /var/lib/xmzfaucet --non-interactive --log-file /var/lib/xmzfaucet/create.log >/dev/null 2>&1 &
  CPID=$!
  for i in $(seq 1 60); do rpc 6193 get_version | grep -q result && break; sleep 1; done
  rpc 6193 create_wallet "{\"filename\":\"faucet\",\"password\":\"$(cat /etc/xmzfaucet/wallet.pass)\",\"language\":\"English\"}" | grep -q '"result"' || { kill $CPID; echo "!! wallet creation failed"; exit 1; }
  rpc 6193 close_wallet >/dev/null; kill $CPID; wait $CPID 2>/dev/null || true
  install -d -m 700 /root/xmzfaucet-backup; cp -p /var/lib/xmzfaucet/faucet /var/lib/xmzfaucet/faucet.keys /etc/xmzfaucet/wallet.pass /root/xmzfaucet-backup/
  echo "   created /var/lib/xmzfaucet/faucet (copy in /root/xmzfaucet-backup/)"
fi
cat > /etc/systemd/system/xmzfaucet-wallet.service <<'EOF'
[Unit]
Description=Monzero faucet wallet RPC
After=monzerod.service
Requires=monzerod.service
[Service]
User=xmzfaucet
Group=xmzfaucet
ExecStart=/bin/sh -c 'exec /usr/bin/monzero-wallet-rpc --daemon-address 127.0.0.1:6185 --trusted-daemon --rpc-bind-ip 127.0.0.1 --rpc-bind-port 6192 --rpc-login "faucet:$$(cat /etc/xmzfaucet/rpc.pass)" --wallet-file /var/lib/xmzfaucet/faucet --password-file /etc/xmzfaucet/wallet.pass --non-interactive --log-file /var/lib/xmzfaucet/wallet-rpc.log'
Restart=on-failure
RestartSec=10
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
ReadWritePaths=/var/lib/xmzfaucet
[Install]
WantedBy=multi-user.target
EOF

echo "== worker config (payouts off)"
if [ ! -f /etc/xmzfaucet/worker.json ]; then
  python3 - <<'PY'
import json, os
cfg = {"site_url": "https://monzero.org", "worker_secret": open("/etc/xmzfaucet/worker-secret").read().strip(),
       "wallet_rpc": "http://127.0.0.1:6192/json_rpc", "wallet_user": "faucet", "wallet_password_file": "/etc/xmzfaucet/rpc.pass",
       "journal": "/var/lib/xmzfaucet/journal.jsonl", "amount_atomic": "10000000000", "max_per_day_atomic": "500000000000",
       "reserve_atomic": "100000000000", "enable_payouts": False, "poll_seconds": 60}
fd = os.open("/etc/xmzfaucet/worker.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o640)
with os.fdopen(fd, "w") as f: json.dump(cfg, f, indent=2)
PY
  chown root:xmzfaucet /etc/xmzfaucet/worker.json
fi
cat > /etc/systemd/system/xmzfaucet.service <<'EOF'
[Unit]
Description=Monzero faucet payout worker
After=network-online.target xmzfaucet-wallet.service
Wants=network-online.target
Requires=xmzfaucet-wallet.service
[Service]
User=xmzfaucet
Group=xmzfaucet
ExecStart=/usr/bin/python3 /opt/xmzfaucet/faucet_worker.py --config /etc/xmzfaucet/worker.json
Restart=on-failure
RestartSec=30
# Exit code 2 means HALT: a person must check the wallet first (utils/faucet/README.md).
RestartPreventExitStatus=2
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
ReadWritePaths=/var/lib/xmzfaucet
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now xmzfaucet-wallet >/dev/null 2>&1; systemctl restart xmzfaucet-wallet
for i in $(seq 1 60); do rpc 6192 get_address '{"account_index":0}' "$LOGIN" | grep -q '"address"' && break; sleep 2; done
ADDR=$(rpc 6192 get_address '{"account_index":0}' "$LOGIN" | python3 -c 'import sys,json;print(json.load(sys.stdin)["result"]["address"])')
systemctl enable --now xmzfaucet >/dev/null 2>&1; systemctl restart xmzfaucet
echo "   faucet address: $ADDR"
REMOTE

echo "== giving the website the worker secret"
scp -q "$HERE/faucet-config-set.php" "$WEB:monzero-private/faucet-config-set.php"
ssh -o BatchMode=yes "$EU" sudo cat /etc/xmzfaucet/worker-secret | ssh -o BatchMode=yes "$WEB" 'php ~/monzero-private/faucet-config-set.php worker_secret'

echo "== checking the worker secret against the website (only while claims are paused)"
if curl -s -m 15 https://monzero.org/api/faucet/ | grep -q '"status":"paused"'; then
ssh -o BatchMode=yes "$EU" sudo -u xmzfaucet python3 - <<'PY'
import json, sys
sys.path.insert(0, "/opt/xmzfaucet")
import faucet_worker
config = json.load(open("/etc/xmzfaucet/worker.json"))
code, reply = faucet_worker.site_call(config, {"action": "lease", "limit": 1})
ok = code == 200 and reply.get("paused") is True and reply.get("claims") == []
print("   website accepted the worker signature (claims paused)" if ok else f"!! website answered HTTP {code}: {reply}")
sys.exit(0 if ok else 1)
PY
else
  echo "   claims are open: skipped, so no claim is leased by this check (the running worker proves the secret)"
fi
echo "== worker status (dry run: never leases claims)"
sleep 5
ssh -o BatchMode=yes "$EU" 'sudo systemctl is-active xmzfaucet-wallet xmzfaucet; sudo journalctl -u xmzfaucet -n 3 --no-pager -o cat'
echo "Next: back up the seed, fund the address above, then run utils/faucet/enable-payouts.sh"
