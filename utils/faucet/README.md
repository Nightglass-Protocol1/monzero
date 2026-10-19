# Faucet payout worker

The website (`/faucet/`) only queues claims. This worker pays them from a dedicated
faucet hot wallet on a server you control (the EU node). The website never sees a key.

## 1. Website configuration (webspace)

Create `~/monzero-private/faucet-config.php` (outside the document root, mode 600):

```php
<?php return [
    'enabled' => false,                         // turn on after the worker is running
    'amount_atomic' => '10000000000',           // 0.1 XMZ
    'daily_cap_atomic' => '500000000000',       // 5 XMZ per rolling 24 hours
    'per_client_daily' => 3,
    'turnstile_site_key' => 'from Cloudflare',  // Turnstile → Add site → monzero.org
    'turnstile_secret' => 'from Cloudflare',
    'worker_secret' => 'output of: openssl rand -hex 32',
];
```

Without Turnstile keys the faucet shows "Accounts are not open yet". With keys but
`enabled => false`, people can create accounts but cannot claim.

If the site is later proxied through Cloudflare, add Cloudflare's published IP ranges as
`'trusted_proxies' => [...]` so per-network limits use the visitor's address, not
Cloudflare's. Never add ranges you do not control or trust.

## 2. Faucet wallet (EU node)

Create a new wallet just for the faucet (not the pool wallet), back up its seed offline,
and run its RPC on loopback with a login:

```
monzero-wallet-rpc --wallet-file /var/lib/xmzfaucet/faucet --password-file /etc/xmzfaucet/wallet.pass \
  --daemon-address 127.0.0.1:6185 --trusted-daemon \
  --rpc-bind-ip 127.0.0.1 --rpc-bind-port 6191 --rpc-login faucet:<random>
```

Fund it with a few days of payouts only (5 XMZ/day at the default cap).

## 3. Worker configuration

`/etc/xmzfaucet/worker.json` (mode 600, owned by the worker user):

```json
{
  "site_url": "https://monzero.org",
  "worker_secret": "same value as on the website",
  "wallet_rpc": "http://127.0.0.1:6191/json_rpc",
  "wallet_user": "faucet",
  "wallet_password_file": "/etc/xmzfaucet/rpc.pass",
  "journal": "/var/lib/xmzfaucet/journal.jsonl",
  "amount_atomic": "10000000000",
  "max_per_day_atomic": "500000000000",
  "reserve_atomic": "100000000000",
  "enable_payouts": false,
  "poll_seconds": 60
}
```

Test with `python3 faucet_worker.py --config /etc/xmzfaucet/worker.json --once` (dry run:
it never leases claims). Payouts need both `"enable_payouts": true` and `--enable-payouts`.

## 4. systemd unit

```
[Unit]
Description=Monzero faucet payout worker
After=network-online.target

[Service]
User=xmzfaucet
ExecStart=/usr/bin/python3 /opt/xmzfaucet/faucet_worker.py --config /etc/xmzfaucet/worker.json --enable-payouts
Restart=on-failure
# Exit code 2 means HALT: a person must check the wallet first. Do not restart it.
RestartPreventExitStatus=2

[Install]
WantedBy=multi-user.target
```

## When it halts

The worker writes `sending` to the journal before every transfer and `sent` (with the
transaction hash) after. If it stops between the two, it refuses to continue. Check the
faucet wallet's outgoing transfers (`get_transfers` with `out` and `pool`):

* If the payment went out, append `{"id": N, "state": "sent", "txid": "...", "amount_atomic": "10000000000"}`.
* If it did not, append `{"id": N, "state": "not_sent", "reason": "checked manually"}`.

Then start the worker again; it reports the result to the website. Also restart it after
refilling the wallet if it halted on a low balance.
