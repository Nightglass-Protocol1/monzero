# XMZ faucet — architecture (not active)

Status 2026-10-19: design only. The website ships a `/faucet/` page and a
`GET /api/faucet/` status endpoint that always reports `paused`. No claim
endpoint, payout worker, wallet or key exists. Turning the faucet on needs the
owner's explicit approval, a funded treasury and a security test of the pieces
below.

## Goals and limits

- Give newcomers a small amount of XMZ to try a wallet. It is not an airdrop
  or a way to distribute supply.
- Every payout is small, capped per address, per client and per day, and comes
  from a separate hot wallet that holds only a small float.
- The website never holds a spend key. Signing happens in a separate wallet
  process the web server cannot reach directly.

## Components

```
browser ──HTTPS──▶ /api/faucet/claim (PHP)
                     │ validate, anti-bot, limits, enqueue
                     ▼
               claims.sqlite (private, outside docroot)
                     ▲
                     │ poll pending claims
               payout worker (separate user, cron/systemd)
                     │ JSON-RPC over loopback, digest auth
                     ▼
               monzero-wallet-rpc (faucet hot wallet only)
```

1. **Claim endpoint** (PHP, same conventions as `api/v1/lib.php`). It accepts
   `POST {address, captcha_token}` and validates the address with the same
   rules as `/payments/request/` (mainnet, standard or subaddress; integrated
   addresses are rejected). It verifies the anti-bot token server side, applies
   limits, and inserts a `pending` claim. It never calls the wallet.
2. **Claims store**: SQLite outside the document root, owned by the web user.
   Tables: `claims(id, address_hash, client_hash, amount_atomic, status,
   created_at, paid_at, txid, error)` and `events` (append-only audit log).
   Addresses are stored as HMAC with a server secret. The plain address lives
   only in the pending row and is deleted after payout.
3. **Payout worker**: runs as a different OS user. It reads pending claims,
   rechecks every limit inside a transaction, calls `transfer` on the wallet
   RPC, records the txid and marks claims `paid` or `failed`. It stops at the
   first unexpected error.
4. **Hot wallet**: a dedicated wallet in `monzero-wallet-rpc` bound to
   127.0.0.1 with `--rpc-login`. It is refilled by hand from cold storage, in
   amounts no larger than a few days of the daily cap.

## Protections

| Risk | Control |
|---|---|
| Bots and scripts | Server-verified anti-bot check (provider is an owner decision; it must work under the site CSP, or the CSP must be extended for it alone) |
| One person, many claims | Per-address cooldown (e.g. 1 claim / 7 days), per-client HMAC of IP with daily salt (e.g. 1 / day), global daily payout cap |
| Draining the treasury | Hot-wallet float limit; worker refuses when balance < reserve; daily and per-claim amount caps in config, checked by both endpoint and worker |
| Request floods | Per-client and global request limits (as API v1), body size limit, no work before validation |
| Key exposure | No keys on the web server; wallet RPC on loopback with digest auth; worker credentials readable only by the worker user |
| Abuse patterns | Append-only `events` log, alert when the pending queue or failures grow past thresholds |
| Emergency stop | `paused` flag in private config, read on every request by the endpoint and on every loop by the worker; pausing needs no deploy |

## Configuration (outside the document root)

```php
<?php return [
  'FAUCET_ENABLED' => false,          // default; true only after approval
  'FAUCET_AMOUNT_ATOMIC' => '0',      // per claim
  'FAUCET_DAILY_CAP_ATOMIC' => '0',
  'FAUCET_ADDRESS_COOLDOWN_DAYS' => 7,
  'FAUCET_HMAC_SECRET' => '…',        // openssl rand -hex 32
  'FAUCET_CAPTCHA_SECRET' => '…',
];
```

Missing or invalid config means paused. The worker's wallet credentials live
in the worker user's own file, never in this config.

## Activation checklist

1. Owner approves amounts, caps and the anti-bot provider.
2. Claim endpoint and worker implemented with tests: address validation,
   every limit, concurrency (two claims racing), pause flag, malformed captcha
   replies, wallet RPC errors, and no plain addresses in logs.
3. Testnet run with a testnet hot wallet for at least a week.
4. Security review of the endpoint, worker isolation and file permissions.
5. Fund the hot wallet with a small float, enable, and watch the event log.

## Status endpoint (implemented)

`GET /api/faucet/` returns
`{"schema":"monzero-faucet-v1","status":"paused","reason":"…"}`. It reads no
config and cannot report anything else. The claim endpoint will replace it
when activation is approved.
