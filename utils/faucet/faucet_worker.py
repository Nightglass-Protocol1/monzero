#!/usr/bin/env python3
"""Monzero faucet payout worker.

Runs next to a dedicated faucet hot wallet (monzero-wallet-rpc on loopback), leases
pending claims from https://monzero.org/api/faucet/worker/ and pays them.

Safety rules:
  * Every send is journaled before it is attempted ("sending") and after ("sent", txid).
  * A "sending" entry without a result means the outcome is unknown: the worker halts
    and a person must check the wallet before deleting or completing that entry.
  * An uncertain RPC result (timeout, dropped connection) also halts the worker.
  * Payouts happen only with "enable_payouts": true in the config AND --enable-payouts.
Standard library only.
"""
import argparse, hashlib, hmac, http.client, json, os, secrets, sys, time, urllib.parse, urllib.request

EXIT_HALT = 2


class RpcError(Exception):
    """The wallet answered with an error: the call definitely did not succeed."""


class RpcUncertain(Exception):
    """No complete answer: the call may or may not have run."""


class Halt(Exception):
    """Stop everything until a person has looked."""


def log(message):
    print(time.strftime("%Y-%m-%d %H:%M:%S"), message, flush=True)


def digest_header(challenges, user, password, path):
    """Answer an RFC 2617 MD5 qop=auth challenge. monero-wallet-rpc offers MD5
    and MD5-sess together, which urllib's digest handler fails on."""
    for c in challenges:
        if not c.lower().startswith("digest "):
            continue
        f = dict((k.strip().lower(), v.strip().strip('"')) for k, _, v in
                 (p.partition("=") for p in c[7:].split(",")))
        if f.get("algorithm", "MD5").upper() != "MD5" or "auth" not in f.get("qop", "").split(","):
            continue
        h = lambda s: hashlib.md5(s.encode()).hexdigest()
        cnonce, nc = secrets.token_hex(8), "00000001"
        realm, nonce = f["realm"], f["nonce"]
        ha1, ha2 = h(f"{user}:{realm}:{password}"), h(f"POST:{path}")
        resp = h(f"{ha1}:{nonce}:{nc}:{cnonce}:auth:{ha2}")
        return (f'Digest username="{user}", realm="{realm}", nonce="{nonce}", uri="{path}", '
                f'algorithm=MD5, qop=auth, nc={nc}, cnonce="{cnonce}", response="{resp}"')
    return None


def wallet_rpc(url, method, params=None, auth=None, timeout=60):
    body = json.dumps({"jsonrpc": "2.0", "id": "0", "method": method, "params": params or {}}).encode()
    headers = {"Content-Type": "application/json"}
    parts = urllib.parse.urlsplit(url)
    path = parts.path or "/"
    # The digest challenge is per connection, so answer it on the same connection.
    conn = http.client.HTTPConnection(parts.hostname, parts.port or 80, timeout=timeout)
    try:
        for attempt in (1, 2):
            conn.request("POST", path, body, headers)
            resp = conn.getresponse()
            data = resp.read()
            if resp.status == 401 and auth:
                # A 401 is refused before the method runs, so retrying cannot pay twice.
                if attempt == 2:
                    raise RpcError(f"{method}: wallet RPC login rejected")
                header = digest_header(resp.headers.get_all("WWW-Authenticate") or [], *auth, path)
                if not header:
                    raise RpcError(f"{method}: no supported auth challenge")
                headers["Authorization"] = header
                continue
            if resp.status != 200:
                raise RpcError(f"{method}: HTTP {resp.status}")
            reply = json.loads(data)
            break
    except (http.client.HTTPException, TimeoutError, ConnectionError, OSError, json.JSONDecodeError) as e:
        raise RpcUncertain(f"{method}: {e}") from e
    finally:
        conn.close()
    if reply.get("error"):
        raise RpcError(f"{method}: {reply['error']}")
    return reply["result"]


def site_call(config, payload):
    """Signed request to the website worker endpoint. Returns (status, json)."""
    body = json.dumps(payload, separators=(",", ":")).encode()
    ts, nonce = str(int(time.time())), secrets.token_hex(16)
    signature = hmac.new(config["worker_secret"].encode(), f"{ts}\n{nonce}\n".encode() + body, hashlib.sha256).hexdigest()
    request = urllib.request.Request(config["site_url"].rstrip("/") + "/api/faucet/worker/", data=body, method="POST", headers={
        "Content-Type": "application/json", "X-Faucet-Timestamp": ts, "X-Faucet-Nonce": nonce, "X-Faucet-Signature": signature,
        "User-Agent": "monzero-faucet-worker/1"})
    try:
        with urllib.request.urlopen(request, timeout=30) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except json.JSONDecodeError:
            return e.code, {}


class Journal:
    """Append-only JSON lines; each write is flushed and fsynced before continuing."""

    def __init__(self, path):
        self.path = path
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)

    def entries(self):
        if not os.path.exists(self.path):
            return []
        with open(self.path, encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

    def write(self, **entry):
        entry["at"] = int(time.time())
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, separators=(",", ":")) + "\n")
            f.flush()
            os.fsync(f.fileno())

    def state(self):
        """Latest state per claim id."""
        latest = {}
        for e in self.entries():
            latest.setdefault(e["id"], {}).update(e)
        return latest

    def sent_since(self, since):
        return sum(int(e["amount_atomic"]) for e in self.entries() if e.get("state") == "sent" and e["at"] >= since)


class Worker:
    def __init__(self, config, enable_payouts):
        self.config = config
        self.journal = Journal(config["journal"])
        self.payouts = bool(config.get("enable_payouts")) and enable_payouts
        password = open(config["wallet_password_file"], encoding="utf-8").read().strip() if config.get("wallet_password_file") else None
        self.auth = (config["wallet_user"], password) if config.get("wallet_user") else None

    def rpc(self, method, params=None):
        return wallet_rpc(self.config["wallet_rpc"], method, params, self.auth)

    def report(self, claim_id, lease, status, **extra):
        code, reply = site_call(self.config, {"action": "report", "id": claim_id, "lease": lease, "status": status, **extra})
        if code == 200 or code == 409:
            # 409: the site already has a final state for this lease; nothing left to report.
            self.journal.write(id=claim_id, state="reported", result=status, http=code)
            return True
        log(f"claim {claim_id}: report failed (HTTP {code}); will retry")
        return False

    def recover(self):
        for claim_id, entry in sorted(self.journal.state().items()):
            if entry["state"] == "sending":
                raise Halt(f"claim {claim_id} has no recorded result (address {entry['address']}). Check the wallet's "
                           "outgoing transfers, then append a 'sent' (with txid) or 'not_sent' line to the journal.")
            if entry["state"] == "sent":
                self.report(claim_id, entry["lease"], "paid", txid=entry["txid"])
            elif entry["state"] == "not_sent":
                self.report(claim_id, entry["lease"], "failed", reason=entry.get("reason", "Not sent"))

    def pay(self, claim):
        cid, lease, address, amount = claim["id"], claim["lease"], claim["address"], claim["amount_atomic"]
        if amount != str(self.config["amount_atomic"]):
            self.journal.write(id=cid, lease=lease, address=address, amount_atomic=amount, state="not_sent", reason="Unexpected amount")
            return self.report(cid, lease, "failed", reason="Unexpected amount")
        try:
            check = self.rpc("validate_address", {"address": address, "any_net_type": False, "allow_openalias": False})
            balance = self.rpc("get_balance", {"account_index": 0})
        except (RpcError, RpcUncertain) as e:
            # Nothing has been sent yet, so this claim can safely be failed and retried by the user.
            self.journal.write(id=cid, lease=lease, address=address, amount_atomic=amount, state="not_sent", reason=str(e)[:200])
            self.report(cid, lease, "failed", reason="The faucet wallet is unavailable; try again later")
            raise
        if not check.get("valid") or check.get("nettype") != "mainnet":
            self.journal.write(id=cid, lease=lease, address=address, amount_atomic=amount, state="not_sent", reason="Invalid address")
            return self.report(cid, lease, "failed", reason="Invalid payout address")
        if self.journal.sent_since(time.time() - 86400) + int(amount) > int(self.config["max_per_day_atomic"]):
            self.journal.write(id=cid, lease=lease, address=address, amount_atomic=amount, state="not_sent", reason="Daily budget")
            return self.report(cid, lease, "failed", reason="Faucet daily budget reached; try again tomorrow")
        if int(balance.get("unlocked_balance", 0)) < int(amount) + int(self.config["reserve_atomic"]):
            if int(balance.get("balance", 0)) >= int(amount) + int(self.config["reserve_atomic"]):
                # Change from an earlier payout is still locked; nothing is wrong, the member can retry shortly.
                self.journal.write(id=cid, lease=lease, address=address, amount_atomic=amount, state="not_sent", reason="Wallet change locked")
                return self.report(cid, lease, "failed", reason="The faucet is busy; try again in a few minutes")
            self.journal.write(id=cid, lease=lease, address=address, amount_atomic=amount, state="not_sent", reason="Wallet low")
            self.report(cid, lease, "failed", reason="Faucet wallet is being refilled; try again later")
            raise Halt("faucet wallet unlocked balance is below amount + reserve; refill it")
        self.journal.write(id=cid, lease=lease, address=address, amount_atomic=amount, state="sending")
        try:
            result = self.rpc("transfer", {"destinations": [{"amount": int(amount), "address": address}], "account_index": 0, "priority": 0, "get_tx_key": False})
        except RpcError as e:
            self.journal.write(id=cid, state="not_sent", reason=str(e)[:200])
            return self.report(cid, lease, "failed", reason="The payment could not be sent; try again later")
        except RpcUncertain as e:
            raise Halt(f"claim {cid}: transfer outcome unknown ({e}); check the wallet before restarting")
        txid = result.get("tx_hash", "")
        if len(txid) != 64:
            raise Halt(f"claim {cid}: transfer returned no transaction hash; check the wallet before restarting")
        self.journal.write(id=cid, state="sent", txid=txid, amount_atomic=amount)
        log(f"claim {cid}: paid {amount} atomic, tx {txid}")
        return self.report(cid, lease, "paid", txid=txid)

    def cycle(self):
        self.recover()
        if not self.payouts:
            log("payouts disabled (dry run): not leasing claims")
            return
        # Lease only what can be paid now: change from each payout stays locked for about ten blocks,
        # so claims wait in the queue (not failed, no halt) until enough of the balance is unlocked.
        need = int(self.config["amount_atomic"]) + int(self.config["reserve_atomic"])
        balance = self.rpc("get_balance", {"account_index": 0})
        if int(balance.get("unlocked_balance", 0)) < need:
            if int(balance.get("balance", 0)) < need:
                raise Halt("faucet wallet balance is below amount + reserve; refill it")
            log("waiting for locked wallet change to unlock; claims stay queued")
            return
        code, reply = site_call(self.config, {"action": "lease", "limit": int(self.config.get("batch", 1))})
        if code != 200:
            log(f"lease failed (HTTP {code}: {reply.get('error', '')})")
            return
        if reply.get("paused"):
            log("faucet paused on the website")
            return
        for claim in reply.get("claims", []):
            self.pay(claim)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", required=True)
    parser.add_argument("--enable-payouts", action="store_true", help="required in addition to enable_payouts in the config")
    parser.add_argument("--once", action="store_true", help="run one cycle and exit")
    args = parser.parse_args()
    with open(args.config, encoding="utf-8") as f:
        config = json.load(f)
    for key in ("site_url", "worker_secret", "wallet_rpc", "journal", "amount_atomic", "max_per_day_atomic", "reserve_atomic"):
        if key not in config:
            sys.exit(f"config is missing {key}")
    worker = Worker(config, args.enable_payouts)
    while True:
        try:
            worker.cycle()
        except Halt as e:
            log(f"HALT: {e}")
            sys.exit(EXIT_HALT)
        except (RpcError, RpcUncertain, OSError, ValueError) as e:
            # Nothing was sent in this cycle (sends halt on uncertainty above); try again later.
            log(f"cycle error: {e}")
        if args.once:
            return
        time.sleep(int(config.get("poll_seconds", 60)))


if __name__ == "__main__":
    main()
