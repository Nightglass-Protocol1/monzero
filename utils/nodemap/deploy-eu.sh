#!/bin/bash
# Install the country-level node census on monzero-eu and give the website its shared secret.
# The census reads the node's peer list, maps IPs to countries with the offline DB-IP Lite
# database and sends only per-country counts to the website every 15 minutes.
# Safe to re-run. Run from the owner's PC:  bash utils/nodemap/deploy-eu.sh
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
EU=${EU_HOST:-monzero-eu} WEB=${WEB_HOST:-monzero-webspace}

echo "== copying the census to $EU"
scp -q "$HERE/node_census.py" "$EU:/tmp/node_census.py"
ssh -o BatchMode=yes "$EU" sudo bash -s <<'REMOTE'
set -euo pipefail
id xmznodemap >/dev/null 2>&1 || useradd --system --home /var/lib/xmznodemap --shell /usr/sbin/nologin xmznodemap
install -d -o xmznodemap -g xmznodemap -m 750 /var/lib/xmznodemap
install -d -o root -g xmznodemap -m 750 /etc/xmznodemap
install -d -o root -g root -m 755 /opt/xmznodemap
install -o root -g root -m 644 /tmp/node_census.py /opt/xmznodemap/node_census.py && rm -f /tmp/node_census.py
(umask 077; [ -s /etc/xmznodemap/secret ] || openssl rand -hex 32 > /etc/xmznodemap/secret)
chown root:xmznodemap /etc/xmznodemap/secret; chmod 640 /etc/xmznodemap/secret
[ -f /etc/xmznodemap/census.json ] || cat > /etc/xmznodemap/census.json <<'EOF'
{
  "node_rpc": "http://127.0.0.1:6185",
  "site_url": "https://monzero.org",
  "secret_file": "/etc/xmznodemap/secret",
  "geo_database": "/var/lib/xmznodemap/dbip-country-lite.csv.gz"
}
EOF
chmod 644 /etc/xmznodemap/census.json

# Monthly database refresh: this month's file, else last month's; checked before it replaces the old one.
cat > /opt/xmznodemap/update-geo.sh <<'EOF'
#!/bin/bash
set -euo pipefail
cd /var/lib/xmznodemap
for month in "$(date -u +%Y-%m)" "$(date -u -d "$(date -u +%Y-%m-01) -1 month" +%Y-%m)"; do
  if curl -sSf -m 300 --max-filesize 100000000 -o dbip.new.csv.gz "https://download.db-ip.com/free/dbip-country-lite-$month.csv.gz"; then
    python3 -I -c 'import sys; sys.path.insert(0, "/opt/xmznodemap"); import node_census as n; d = n.CountryDB(sys.argv[1]); assert d.counts[4] > 50000' dbip.new.csv.gz
    mv dbip.new.csv.gz "dbip-country-lite-$month.csv.gz"
    ln -sfn "dbip-country-lite-$month.csv.gz" dbip-country-lite.csv.gz
    find . -maxdepth 1 -name 'dbip-country-lite-*.csv.gz' ! -name "dbip-country-lite-$month.csv.gz" -delete
    echo "DB-IP country database $month installed"; exit 0
  fi
done
rm -f dbip.new.csv.gz; echo "DB-IP download failed; keeping the current database" >&2; exit 1
EOF
chmod 755 /opt/xmznodemap/update-geo.sh

common='User=xmznodemap
Group=xmznodemap
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
ReadWritePaths=/var/lib/xmznodemap'
cat > /etc/systemd/system/xmznodemap-geo.service <<EOF
[Unit]
Description=Monzero node map: refresh the DB-IP country database
After=network-online.target
Wants=network-online.target
[Service]
Type=oneshot
ExecStart=/opt/xmznodemap/update-geo.sh
$common
EOF
cat > /etc/systemd/system/xmznodemap-geo.timer <<'EOF'
[Unit]
Description=Monthly DB-IP country database refresh
[Timer]
OnCalendar=*-*-03 04:00:00
RandomizedDelaySec=6h
Persistent=true
[Install]
WantedBy=timers.target
EOF
cat > /etc/systemd/system/xmznodemap.service <<EOF
[Unit]
Description=Monzero node map: country-level peer census
After=monzerod.service network-online.target
Wants=network-online.target
[Service]
Type=oneshot
ExecStart=/usr/bin/python3 -I /opt/xmznodemap/node_census.py --config /etc/xmznodemap/census.json
TimeoutStartSec=120
$common
EOF
cat > /etc/systemd/system/xmznodemap.timer <<'EOF'
[Unit]
Description=Country-level peer census every 15 minutes
[Timer]
OnBootSec=5min
OnUnitActiveSec=15min
[Install]
WantedBy=timers.target
EOF
systemctl daemon-reload
[ -e /var/lib/xmznodemap/dbip-country-lite.csv.gz ] || systemctl start xmznodemap-geo.service
systemctl enable --now xmznodemap-geo.timer >/dev/null 2>&1
echo "== dry run (country totals only)"
sudo -u xmznodemap python3 -I /opt/xmznodemap/node_census.py --config /etc/xmznodemap/census.json --dry-run \
  | python3 -c 'import sys,json;p=json.load(sys.stdin);print("  ",p["totals"],"countries:",", ".join(f"{k} {v[\"observed\"]}" for k,v in p["countries"].items()))'
REMOTE

echo "== giving the website the census secret"
ssh -o BatchMode=yes "$EU" sudo cat /etc/xmznodemap/secret | ssh -o BatchMode=yes "$WEB" \
  'umask 077; read -r s; case "$s" in *[!0-9a-f]*|"") echo "!! bad secret"; exit 1;; esac; [ ${#s} -eq 64 ] || { echo "!! bad secret"; exit 1; }
   printf "<?php return [\"secret\" => \"%s\"];\n" "$s" > ~/monzero-private/node-census-config.php.tmp && mv ~/monzero-private/node-census-config.php.tmp ~/monzero-private/node-census-config.php && echo "   website config written"'

echo "== first census and timer"
ssh -o BatchMode=yes "$EU" 'sudo systemctl start xmznodemap.service && sudo systemctl enable --now xmznodemap.timer >/dev/null 2>&1; sudo journalctl -u xmznodemap -n 2 --no-pager -o cat'
curl -s -m 15 https://monzero.org/api/v1/network/nodes/ | head -c 400; echo
