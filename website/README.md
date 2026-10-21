# Monzero website

Website for `monzero.org`, including the PHP-backed block explorer at
`/explorer/` and the local-draft asset workspace at `/app/`. It contains no
build-time dependencies.

The public source repository is
<https://github.com/Nightglass-Protocol1/monzero>.

The homepage links to `/WHITEPAPER.md`. Deploy the repository-root
`WHITEPAPER.md` at that exact document-root path whenever the site is updated;
the packaged copies and public copy must come from the same reviewed source.

## Preview locally

```bash
cd website
php -S 127.0.0.1:8080
```

Open `http://127.0.0.1:8080` for the website and
`http://127.0.0.1:8080/explorer/` for the explorer. Studio is available at
`http://127.0.0.1:8080/app/`; it can preview and download unsigned JSON drafts
but deliberately has no wallet connection, signing, or submission path.

## VPS deployment

Copy this directory's contents to `/var/www/monzero`, install
`nginx-monzero.conf` as `/etc/nginx/sites-available/monzero`, enable the site,
set the `fastcgi_pass` socket to the PHP-FPM listener installed on the host,
test Nginx, and reload it. The included Nginx route proxies only the homepage's
`/api/node-info/` request to the restricted local RPC service. PHP-FPM serves
the allowlisted explorer proxy and opt-in miner statistics endpoint.

On IONOS web hosting, upload the complete contents of this directory to the
domain's assigned document root. PHP must be enabled so `/explorer/api.php` can
proxy the allowlisted, read-only requests to the restricted public node.

`releases/genesis-pre11-notes.txt` is the human-readable companion to the
machine-readable pre11 metadata. It covers the CLI, source, and separately
packaged Windows graphical-wallet archive. Keep its release identity,
platform scope, and limitations aligned with `docs/RELEASE_NOTES.md` without
changing published archive hashes.

## Anonymous miner statistics

The miner table uses an opt-in heartbeat endpoint. It never accepts or returns
a wallet address, hostname, IP address, serial number, or hardware identifier.
Each reporter creates a random UUID; PHP pseudonymizes it with a server-side
HMAC secret before storage and exposes only the first eight pseudonym digits.

Configure these secrets in the PHP environment (use independent random values):

```text
MONZERO_STATS_SECRET=<at least 32 random characters, server only>
MONZERO_STATS_INGEST_TOKEN=<at least 24 random characters, team reporters>
MONZERO_STATS_FILE=/an/apache-writable/private/path/miner-stats.json
```

For shared hosting without environment-variable controls, create
`.monzero-miner-stats.php` one directory above the document root:

```php
<?php
return [
    'MONZERO_STATS_SECRET' => 'server-only-random-value',
    'MONZERO_STATS_INGEST_TOKEN' => 'team-reporter-random-value',
    'MONZERO_STATS_FILE' => __DIR__ . '/.monzero-miner-stats.json',
];
```

Generate suitable values with `openssl rand -hex 32`. Do not place the HMAC
secret in a download or reporter. Give only the ingest token to miners who opt
in, then run the reporter alongside their already-running local daemon:

```bash
MONZERO_STATS_TOKEN='team-ingest-token' \
  python3 utils/monzero-miner-reporter.py --interval 60
```

The table counts a miner as active for three minutes after its last heartbeat.
Hash rate and blocks found are self-reported. Block counts are derived from the
local daemon log and are not consensus-verified leaderboard claims.

The Windows heartbeat helper is
`utils/release/windows/monzero-miner-reporter.ps1`. Install its ingest token in
`%APPDATA%\Monzero\miner-stats-token.txt` with access limited to the reporting
account; never put that token in a public archive. `start-mining.bat` launches
the reporter automatically when that file exists; the reporter's named mutex
prevents duplicate instances. The homepage separately
shows `difficulty / target` as an estimated network hash rate even when no
miner has opted into reporting.

On Windows the daemon's default data and mining log directory is
`%PROGRAMDATA%\monzero`; the reporter diagnostic log remains under
`%APPDATA%\Monzero`.

Linux desktops can keep their opted-in reporter running with the user service:

```bash
install -Dm755 utils/monzero-miner-reporter.py ~/.local/share/monzero/monzero-miner-reporter.py
install -Dm644 utils/systemd/monzero-miner-reporter.service ~/.config/systemd/user/monzero-miner-reporter.service
# Save the operator-provided ingest token privately in ~/.monzero/miner-stats-token.txt.
chmod 600 ~/.monzero/miner-stats-token.txt
systemctl --user daemon-reload
systemctl --user enable --now monzero-miner-reporter.service
```

Run these commands from the repository root. The service reads only the local
mining status and log, sends a heartbeat every 30 seconds, and never starts or
stops mining. It starts with the user's systemd session. Inspect failures with
`journalctl --user -u monzero-miner-reporter.service`.
An explicit inactive heartbeat removes a stopped miner immediately; without a
heartbeat its entry expires after three minutes. Older reporters remain supported.
A reported count of zero means no active reporters, not necessarily no mining.
Individual unreported miners and their speeds cannot be inferred from chain data.

Validate the API and reporter without blockchain nodes:
`python3 -m unittest discover -s utils/tests -p test_miner_stats.py -v`.

## Roadmap maintenance

Update `roadmap/index.html` when a development milestone is verified complete.
Use the actual test result and its scope; label compilation-only work, running tests,
failed checks and unfinished app integration separately from completed milestones.
Keep a dated latest update while preserving the meaning of historical checkpoints.
Do not infer public-network readiness or a revised delivery date from component tests.
Publish aggregate results only, without private wallet material or local machine paths.
A local source update is not proof that the public site has been deployed.
