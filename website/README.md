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
test Nginx, and reload it. The included Nginx configuration executes `/api/node-info/index.php` through
PHP-FPM for `/api/node-info/`, preserving tip freshness and mainnet readiness
checks. PHP-FPM also serves the allowlisted explorer proxy and opt-in miner
statistics endpoint. Static cache rules retain the server security headers.
This port-80 example assumes a separately configured HTTPS terminator; verify
TLS and public headers before deployment.

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

### Mainnet network statistics

`/stats/` shows the latest 720 mainnet block headers, with 120/360/720-block
windows for estimated hashrate (difficulty / current target interval), difficulty,
block intervals and non-coinbase transaction counts. The GET-only `stats/api.php`
uses the fixed public node, a shared 60-second public-data cache and serialized
refreshes. It returns an error when mainnet data cannot be obtained; the browser
labels any retained snapshot with its original update time. No analytics SDK,
wallet identity collection, or fabricated user-growth series is included.
The existing opt-in miner endpoint supplies current reporting installations only.

Validation: PHP syntax, JavaScript syntax and real mainnet API retrieval; Chromium
checks at 1440px and 390px, 720/120-block selection, retained-snapshot and first-load
outage states. Wine mainnet GUI screenshots use a separate empty demonstration
wallet connected to the public remote node, without mining or transfers.

### Nginx configuration regression check

With Nginx and `php-cgi` available, run:

```sh
python3 tests/website/check_nginx.py
```

If needed, set `NGINX_BINARY` to the Nginx executable and
`NGINX_FASTCGI_PARAMS` to its distribution's `fastcgi_params` file. The check
uses temporary files and loopback ports, validates configuration syntax, and
checks PHP directory routing, POST preservation, static/error security headers,
module/checksum MIME types, cache behavior and hidden-file denial. It neither
changes the installed server configuration nor contacts the blockchain node.
The standard website suite tests the actual PHP observation logic separately.
This local HTTP check does not validate a production TLS terminator, PHP-FPM
socket permissions, Apache `.htaccess`, or public-hosting response headers.

Keep security `add_header` directives at server scope: a location with its own
`add_header` can suppress inherited headers. The static locations use `expires`
for caching without adding a location-level `add_header`.
See the [Nginx headers documentation](https://nginx.org/en/docs/http/ngx_http_headers_module.html).

Behind a reverse proxy, configure Nginx's `set_real_ip_from` for only the actual
trusted proxy IPs/CIDRs and `real_ip_header` for the header that proxy overwrites.
Do not copy a broad trust range or accept visitor-supplied forwarding headers.
Verify that PHP receives distinct client `REMOTE_ADDR` values before publishing:
the pool dashboard's per-client limits and public-profile proxy depend on it.
The example deliberately does not guess the deployment's trusted proxy addresses.
Directory redirects are relative to preserve the external HTTPS origin; the
node-status slash redirect uses 308 so POST requests retain their method.

### Public node observation cache

The node-status PHP adapter shares public observations for at most 15 seconds.
Its private temporary directory is named from the deployed script directory;
files are mode 0600 in a mode-0700 directory. Only public node information and
its observation time are stored, without request bodies or visitor identifiers.
A nonblocking lock permits one upstream refresh at a time; competing refreshes
return 503 with Retry-After. Failed node lookups have a five-second cooldown.
Expired observations are not served as an outage fallback. Tip age and readiness
are recalculated on each response, and the UI labels the original observation
time. Browser/proxy caching remains disabled with Cache-Control: no-store.

PHP must be able to create and lock files in its temporary directory. Cache
storage errors fail closed with 503. Upstream responses are capped at 256 KiB,
redirects are disabled, and each request retains its existing timeout. The node
URL remains the existing HTTP endpoint; this cache does not authenticate that
transport or replace production TLS and edge abuse-control requirements.

### Legacy supply endpoint

`/api/supply/` retains its numeric plain-text output and existing JSON fields for
listing-site compatibility. This is an explicit legacy exception: those numbers
are an estimate from a saved anchor plus unpenalized emission, not a reverified
circulating-supply measurement. JSON metadata and the `X-Monzero-Supply-Status`
header disclose that limitation; existing plain-text consumers may not read them.
The homepage therefore shows supply unavailable rather than reusing that value.
Do not treat `circulating_supply` or `total_supply` as verified totals without
checking the anchor against a trusted unrestricted node and accounting for reward
penalties and the intended supply definition. GMP is required by the calculation.
