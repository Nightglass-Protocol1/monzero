# XMZ faucet — architecture

Status 2026-10-21: implemented, not yet switched on. Owner rules: 0.1 XMZ once per 24 hours
per account; accounts need email confirmation, a password and mandatory TOTP two-factor
authentication; a payout address in the profile; Cloudflare Turnstile on sign-up, sign-in
and every claim. Payouts stay off until the owner funds the faucet wallet, installs the
worker (`utils/faucet/README.md`) and sets `enabled => true`.

Implemented: `/faucet/` (accounts, profile, claims), `GET /api/faucet/` (status),
`POST /api/faucet/worker/` (signed lease/report interface) and
`utils/faucet/faucet_worker.py`. Tests: `tests/website/test_faucet.py`.

Rules enforced on the website, inside one serialised transaction per claim: one claim per
account per cooldown (24 h); one claim per payout address per 24 h, and each address may
belong to only one account; a per-network daily limit (HMAC of the client address); a
rolling daily budget; the enabled flag. Failed payouts do not count, so the member can
claim again. TOTP codes are single-use per member. Address changes need a TOTP code.
The worker re-checks the amount, validates the address with the wallet, enforces its
own daily maximum and a balance reserve, and halts on any uncertain send.

## Goals and limits

- Give newcomers a small amount of XMZ to try a wallet. It is not an airdrop
  or a way to distribute supply.
- Every payout is small, capped per address, per client and per day, and comes
  from a separate hot wallet that holds only a small float.
- The website never holds a spend key. Signing happens in a separate wallet
  process the web server cannot reach directly.

## Components

```
browser ──HTTPS──▶ /faucet/ (PHP: accounts, TOTP, profile, claims)
                     │ Turnstile check, limits, one serialised insert
                     ▼
               ~/monzero-private/faucet.sqlite (outside the document root)
                     ▲
                     │ POST /api/faucet/worker/  (HMAC-signed lease / report)
               faucet_worker.py on the EU node (own OS user, systemd)
                     │ JSON-RPC over loopback, digest auth
                     ▼
               monzero-wallet-rpc (faucet hot wallet only)
```

1. **Accounts** (`faucet/index.php`, `faucet/lib.php`): email + password (Argon2id),
   email confirmation link, mandatory TOTP before any claim, single-use TOTP steps,
   password reset by email link plus TOTP code. Sessions use hashed tokens in
   `__Host-` Secure HttpOnly SameSite=Strict cookies (30 min idle, 12 h maximum),
   CSRF tokens and an Origin check. Turnstile is verified server side on sign-up,
   sign-in, resend/forgot requests and every claim.
2. **Store**: `members`, `tokens`, `sessions`, `claims`, `limits`, `worker_nonces`
   and an append-only `events` table (triggers block updates and deletes). Client
   and address hashes are HMACs with a per-installation secret. The payout address
   is stored in the clear because the worker needs it to pay.
3. **Worker interface**: every request carries a timestamp, a random nonce and an
   HMAC-SHA256 signature with the shared worker secret; stale timestamps and reused
   nonces are refused. `lease` moves pending claims to `processing` (never back), and
   `report` records `paid` with a txid or `failed` with a short reason.
4. **Worker** (`utils/faucet/faucet_worker.py`): journals before and after each
   transfer, validates addresses with the wallet, enforces its own daily maximum and a
   balance reserve, and halts on uncertainty. Setup: `utils/faucet/README.md`.
5. **Hot wallet**: a dedicated wallet bound to 127.0.0.1 with `--rpc-login`, refilled
   by hand with no more than a few days of the daily cap.

## Protections

| Risk | Control |
|---|---|
| Bots and scripts | Cloudflare Turnstile verified server side; CSP widened for Turnstile on `/faucet/` only |
| One person, many claims | Confirmed email, mandatory TOTP, one address per account, 24 h per account and per address, per-network daily limit, daily budget |
| Draining the treasury | Daily budget on the site, separate daily maximum and balance reserve in the worker, small hot-wallet float |
| Double payment | Leases never return to pending; journal before and after each send; halt on unknown outcome |
| Account takeover | Argon2id, login throttling per account and per network, TOTP required for sign-in, address changes and resets |
| Key exposure | No keys on the web server; wallet RPC on loopback with digest auth on a separate host |
| Emergency stop | `enabled => false` in the private config stops new claims and leasing immediately |

## Configuration

Website: `~/monzero-private/faucet-config.php`; worker: `/etc/xmzfaucet/worker.json`.
Both are documented with examples in `utils/faucet/README.md`. Missing or invalid
website configuration means accounts closed and claims paused.

## Activation checklist

1. Turnstile keys and worker secret in the website config (accounts open, claims paused).
2. Faucet wallet created, seed backed up offline, funded with a small float.
3. Worker installed, dry run checked, then started with payouts enabled.
4. `enabled => true`; watch the first claims and the events table.

## Status endpoint

`GET /api/faucet/` returns the schema, `open` or `paused`, whether accounts are open,
the amount and the cooldown. It never includes secrets or member data.
