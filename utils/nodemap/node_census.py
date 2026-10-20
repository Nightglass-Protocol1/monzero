#!/usr/bin/env python3
"""Country-level census of Monzero peers, run next to a node.

Reads the node's own peer list and connections over its private loopback RPC, looks each
public IP up in an offline IP-to-country database (DB-IP "IP to Country Lite", CC BY 4.0) and
sends only per-country counts to the website. IP addresses, ports, peer IDs, regions, cities
and coordinates never leave this process and are never written to disk.

  node_census.py --config /etc/xmznodemap/census.json            # send to the website
  node_census.py --config /etc/xmznodemap/census.json --dry-run  # print the payload only

Counts per country:
  reachable  distinct IPs on the node's white list seen in the last 24 hours (the node has
             completed a handshake with them, so they accept incoming connections)
  connected  distinct IPs with an open connection right now (includes nodes that cannot
             accept incoming connections)
  observed   distinct IPs in either set
"""
import argparse, array, bisect, csv, gzip, hashlib, hmac, ipaddress, json, os, re, secrets, sys, time, urllib.request

SCHEMA = "monzero-node-census-v1"
WINDOW_SECONDS = 86400
UNKNOWN = "ZZ"  # ISO 3166 user-assigned code: IP not in the database


class CountryDB:
    """IPv4 and IPv6 ranges from a DB-IP country CSV (start,end,country), optionally gzipped.

    Kept in packed arrays (about 15 MB for the full database). IPv6 ranges are stored at /64
    granularity; country allocations are far larger than a /64, so lookups are unaffected.
    """

    def __init__(self, path):
        opener = gzip.open if path.endswith(".gz") else open
        self.tables = {4: (array.array("L"), array.array("L"), bytearray()), 6: (array.array("Q"), array.array("Q"), bytearray())}
        with opener(path, "rt", encoding="utf-8", newline="") as f:
            for record in csv.reader(f):
                if len(record) < 3 or not re.fullmatch(r"[A-Z]{2}", record[2]):
                    continue
                try:
                    start, end = ipaddress.ip_address(record[0]), ipaddress.ip_address(record[1])
                except ValueError:
                    continue
                if start.version != end.version or int(start) > int(end):
                    continue
                shift = 64 if start.version == 6 else 0
                starts, ends, codes = self.tables[start.version]
                first, last = int(start) >> shift, int(end) >> shift
                if starts and first < starts[-1]:
                    raise ValueError(f"{path}: ranges are not sorted")
                if starts and first == starts[-1]:
                    continue  # several ranges inside one IPv6 /64: keep the first
                starts.append(first); ends.append(last); codes += record[2].encode()
        self.counts = {v: len(t[0]) for v, t in self.tables.items()}
        if not self.counts[4]:
            raise ValueError(f"{path}: no IPv4 ranges found")
        self.version = os.path.basename(os.path.realpath(path))

    def country(self, ip):
        starts, ends, codes = self.tables[ip.version]
        value = int(ip) >> (64 if ip.version == 6 else 0)
        i = bisect.bisect_right(starts, value) - 1
        return codes[2 * i:2 * i + 2].decode() if i >= 0 and ends[i] >= value else UNKNOWN


def public_ip(text):
    """Return an ip_address for a public unicast host string, else None (private, reserved, Tor, I2P...)."""
    try:
        ip = ipaddress.ip_address(str(text).strip("[]"))
    except ValueError:
        return None
    if ip.version == 6 and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    return ip if ip.is_global and not ip.is_multicast else None


def node_post(base, path, payload, timeout=20):
    request = urllib.request.Request(base.rstrip("/") + path, data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as resp:
        body = resp.read(8 * 1048576 + 1)
    if len(body) > 8 * 1048576:
        raise ValueError(f"{path}: response too large")
    return json.loads(body)


def collect(node_rpc, now):
    """Return (reachable_ips, connected_ips) as sets of ip_address objects."""
    peers = node_post(node_rpc, "/get_peer_list", {"public_only": True})
    if peers.get("status") != "OK":
        raise ValueError(f"get_peer_list status {peers.get('status')!r}")
    reachable = set()
    for peer in peers.get("white_list") or []:
        ip = public_ip(peer.get("host", ""))
        if ip and now - int(peer.get("last_seen") or 0) <= WINDOW_SECONDS:
            reachable.add(ip)
    reply = node_post(node_rpc, "/json_rpc", {"jsonrpc": "2.0", "id": 0, "method": "get_connections"})
    if "error" in reply:
        raise ValueError(f"get_connections: {reply['error']}")
    connected = {ip for c in (reply.get("result", {}).get("connections") or []) if (ip := public_ip(c.get("host", "")))}
    return reachable, connected


def census(reachable, connected, db, now):
    countries = {}
    for ip in reachable | connected:
        entry = countries.setdefault(db.country(ip), {"observed": 0, "reachable": 0, "connected": 0})
        entry["observed"] += 1
        entry["reachable"] += ip in reachable
        entry["connected"] += ip in connected
    return {
        "schema": SCHEMA,
        "observed_at": now,
        "window_seconds": WINDOW_SECONDS,
        "totals": {"observed": len(reachable | connected), "reachable": len(reachable), "connected": len(connected)},
        "countries": dict(sorted(countries.items())),
        "geo_database": db.version,
    }


def send(site_url, secret, payload, timeout=30):
    body = json.dumps(payload, separators=(",", ":")).encode()
    ts, nonce = str(int(time.time())), secrets.token_hex(16)
    signature = hmac.new(secret.encode(), f"{ts}\n{nonce}\n".encode() + body, hashlib.sha256).hexdigest()
    request = urllib.request.Request(site_url.rstrip("/") + "/api/node-census/", data=body, method="POST", headers={
        "Content-Type": "application/json", "X-Census-Timestamp": ts, "X-Census-Nonce": nonce,
        "X-Census-Signature": signature, "User-Agent": "monzero-node-census/1"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read(65536) or b"{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read(65536) or b"{}")
        except json.JSONDecodeError:
            return e.code, {}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", required=True)
    parser.add_argument("--dry-run", action="store_true", help="print the payload instead of sending it")
    args = parser.parse_args()
    with open(args.config, encoding="utf-8") as f:
        config = json.load(f)
    db = CountryDB(config["geo_database"])
    now = int(time.time())
    payload = census(*collect(config.get("node_rpc", "http://127.0.0.1:6185"), now), db, now)
    if args.dry_run:
        print(json.dumps(payload, indent=2))
        return
    secret = open(config["secret_file"], encoding="utf-8").read().strip()
    code, reply = send(config.get("site_url", "https://monzero.org"), secret, payload)
    if code != 200:
        sys.exit(f"website refused the census: HTTP {code} {reply}")
    print(f"sent: {payload['totals']['observed']} nodes in {len(payload['countries'])} countries")


if __name__ == "__main__":
    main()
