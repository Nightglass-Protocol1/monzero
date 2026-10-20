#!/bin/bash
# Install the crypto news collector on monzero-eu (every 30 minutes) and give the website its
# upload secret. Safe to re-run; keeps the secret. Run from the owner's PC:  bash utils/news/deploy-eu.sh
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
EU=${EU_HOST:-monzero-eu} WEB=${WEB_HOST:-monzero-webspace}
echo "== copying the collector to $EU"
scp -q "$HERE/news_collector.py" "$HERE/feeds.json" "$EU:/tmp/"
ssh -o BatchMode=yes "$EU" sudo bash -s <<'REMOTE'
set -euo pipefail
id xmznews >/dev/null 2>&1 || useradd --system --home /nonexistent --no-create-home --shell /usr/sbin/nologin xmznews
install -d -o root -g xmznews -m 750 /etc/xmznews
install -d -o root -g root -m 755 /opt/xmznews
install -o root -g root -m 644 /tmp/news_collector.py /tmp/feeds.json /opt/xmznews/ && rm -f /tmp/news_collector.py /tmp/feeds.json
(umask 027; [ -s /etc/xmznews/secret ] || openssl rand -hex 32 > /etc/xmznews/secret)
chown root:xmznews /etc/xmznews/secret; chmod 640 /etc/xmznews/secret
cat > /etc/systemd/system/xmznews.service <<'EOF2'
[Unit]
Description=Monzero crypto news: collect headlines and upload to monzero.org
After=network-online.target
Wants=network-online.target
[Service]
Type=oneshot
User=xmznews
Group=xmznews
ExecStart=/usr/bin/python3 -I /opt/xmznews/news_collector.py --feeds /opt/xmznews/feeds.json --secret-file /etc/xmznews/secret
TimeoutStartSec=180
Nice=10
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
EOF2
cat > /etc/systemd/system/xmznews.timer <<'EOF2'
[Unit]
Description=Crypto news every 30 minutes
[Timer]
OnBootSec=5min
OnUnitActiveSec=30min
RandomizedDelaySec=120
[Install]
WantedBy=timers.target
EOF2
systemctl daemon-reload
echo "== dry run (top 5)"
sudo -u xmznews python3 -I /opt/xmznews/news_collector.py --feeds /opt/xmznews/feeds.json --dry-run | sed -n '1,5p;$p'
REMOTE
echo "== giving the website the upload secret"
ssh -o BatchMode=yes "$EU" sudo cat /etc/xmznews/secret | ssh -o BatchMode=yes "$WEB" \
  'umask 077; read -r s; case "$s" in *[!0-9a-f]*|"") echo "!! bad secret"; exit 1;; esac; [ ${#s} -eq 64 ] || { echo "!! bad secret"; exit 1; }
   printf "<?php return [\"secret\" => \"%s\"];\n" "$s" > ~/monzero-private/news-config.php.tmp && mv ~/monzero-private/news-config.php.tmp ~/monzero-private/news-config.php && echo "   website config written"'
echo "== first upload and timer"
ssh -o BatchMode=yes "$EU" 'sudo systemctl start xmznews.service; sudo systemctl enable --now xmznews.timer >/dev/null 2>&1; sudo journalctl -u xmznews -n 2 --no-pager -o cat | grep -v "^Starting\|^Finished"; systemctl is-active xmznews.timer'
curl -s -m 15 https://monzero.org/news/data/latest.json | python3 -c 'import sys,json;d=json.load(sys.stdin);print("live:",len(d["stories"]),"stories; top:",d["stories"][0]["title"])'
