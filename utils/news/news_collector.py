#!/usr/bin/env python3
"""Top crypto headlines of the day for https://monzero.org/news/.

Reads the RSS/Atom feeds in feeds.json, keeps headlines from the last 24 hours, drops sponsored
posts, press releases and price-prediction filler, groups headlines about the same story across
outlets and ranks stories by how many outlets cover them (then by recency). Only titles, links,
outlet names and times are kept: no article text or images. The result is sent to the website,
signed like the network history upload.

  news_collector.py --feeds feeds.json --secret-file /etc/xmznews/secret          # collect and upload
  news_collector.py --feeds feeds.json --dry-run                                  # print the ranking
Standard library only.
"""
import argparse, concurrent.futures, email.utils, gzip, hashlib, hmac, html, json, re, secrets, sys, time, urllib.error, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

SCHEMA = "monzero-news-v1"
WINDOW = 86400
TOP = 15
MAX_FEED_BYTES = 4 * 1048576
USER_AGENT = "Mozilla/5.0 (compatible; MonzeroNews/1.0; +https://monzero.org/news/)"
ATOM = "{http://www.w3.org/2005/Atom}"
SPONSORED = re.compile(r"\b(sponsored|press release|partner content|paid content|advertorial|promoted|pr newswire|globe newswire|\[pr\])\b", re.I)
SPONSORED_PATH = re.compile(r"/(press-releases?|sponsored|pr|partner-content|advertorial)(/|$)", re.I)
FILLER = re.compile(r"\b(price predictions?|price analysis|technical analysis|price forecast|could (soar|surge|explode|rally) \d|\d+x (gains?|potential)|best (crypto|coins?|altcoins?) to buy|presale)\b", re.I)
STOP = set("""a an and are as at be been but by for from has have how in into is it its new of on or over says that the their this to up was were what when why will with after amid
against about out more than first now could would may might just today week year report reports news update live""".split())
ALIASES = {"btc": "bitcoin", "eth": "ethereum", "ether": "ethereum", "xrp": "ripple", "sol": "solana", "etfs": "etf", "doge": "dogecoin", "xmr": "monero",
           "stablecoins": "stablecoin", "exchanges": "exchange", "hackers": "hack", "hacked": "hack", "exploit": "hack", "exploited": "hack", "sec's": "sec"}


def clean_text(value, limit=300):
    text = html.unescape(re.sub(r"<[^>]+>", " ", value or ""))
    text = re.sub(r"[\x00-\x1f\x7f​-‏  ﻿]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit].rstrip()


def clean_link(value):
    link = (value or "").strip()
    try:
        parts = urllib.parse.urlsplit(link)
    except ValueError:
        return None
    if parts.scheme != "https" or not parts.hostname or parts.username or parts.password or len(link) > 1000:
        return None
    query = urllib.parse.urlencode([(k, v) for k, v in urllib.parse.parse_qsl(parts.query) if not k.lower().startswith(("utm_", "mc_", "fbclid", "gclid"))])
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc.lower(), parts.path, query, ""))


def parse_time(value):
    value = (value or "").strip()
    if not value:
        return None
    try:
        return int(email.utils.parsedate_to_datetime(value).timestamp())
    except (TypeError, ValueError, IndexError, OverflowError):
        pass
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return int((dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)).timestamp())
    except ValueError:
        return None


def fetch(url, timeout=15):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml"})
    with urllib.request.urlopen(request, timeout=timeout) as resp:
        data = resp.read(MAX_FEED_BYTES + 1)
    if len(data) > MAX_FEED_BYTES:
        raise ValueError("feed too large")
    return data


def parse_feed(data):
    """Yield dicts with title, link, published, categories from RSS 2.0 or Atom bytes."""
    head = data[:4096].decode("utf-8", "ignore")
    if "<!ENTITY" in head or "<!entity" in head:
        raise ValueError("feed declares entities")  # never expand custom entities
    root = ET.fromstring(data)
    if root.tag == "rss" or root.find("channel") is not None:
        for item in root.iter("item"):
            yield {"title": item.findtext("title"), "link": item.findtext("link") or item.findtext("guid"),
                   "published": item.findtext("pubDate") or item.findtext("{http://purl.org/dc/elements/1.1/}date"),
                   "categories": [c.text or "" for c in item.findall("category")]}
    elif root.tag == ATOM + "feed":
        for entry in root.iter(ATOM + "entry"):
            link = next((l.get("href") for l in entry.findall(ATOM + "link") if l.get("rel", "alternate") == "alternate"), None)
            yield {"title": entry.findtext(ATOM + "title"), "link": link,
                   "published": entry.findtext(ATOM + "published") or entry.findtext(ATOM + "updated"),
                   "categories": [c.get("term", "") for c in entry.findall(ATOM + "category")]}
    else:
        raise ValueError("not an RSS or Atom feed")


def headlines(feed, data, now):
    out = []
    for raw in parse_feed(data):
        title, link, published = clean_text(raw["title"]), clean_link(raw["link"]), parse_time(raw["published"])
        if not title or len(title) < 12 or not link or published is None or published > now + 3600 or now - published > WINDOW:
            continue
        if SPONSORED.search(title) or any(SPONSORED.search(c or "") for c in raw["categories"]) or SPONSORED_PATH.search(urllib.parse.urlsplit(link).path):
            continue
        if FILLER.search(title):
            continue
        out.append({"title": title, "url": link, "source": feed["name"], "published_at": min(published, now)})
    return out


def tokens(title):
    words = re.findall(r"[a-z0-9$][a-z0-9'$.-]*[a-z0-9]|[a-z0-9]", title.lower())
    result = set()
    for w in words:
        w = ALIASES.get(w.strip(".'"), w.strip(".'"))
        if len(w) >= 3 and w not in STOP:
            result.add(w)
    return result


def similar(a, b):
    shared = len(a & b)
    union = len(a | b) or 1
    return shared / union >= 0.4 or (shared >= 4 and shared / union >= 0.25)


def rank(items, order, now, top=TOP):
    """Group headlines about one story (different outlets only) and rank by outlet count, then recency."""
    items = sorted(items, key=lambda i: -i["published_at"])
    stories = []
    for item in items:
        t = tokens(item["title"])
        for story in stories:
            if item["source"] not in story["sources"] and any(similar(t, other) for other in story["tokens"]):
                story["items"].append(item); story["sources"].add(item["source"]); story["tokens"].append(t)
                break
        else:
            stories.append({"items": [item], "sources": {item["source"]}, "tokens": [t]})
    def lead(story):  # headline from the highest-listed outlet in feeds.json
        return min(story["items"], key=lambda i: (order.get(i["source"], 999), -i["published_at"]))
    ranked = sorted(stories, key=lambda s: (-len(s["sources"]), -max(i["published_at"] for i in s["items"]), order.get(lead(s)["source"], 999)))
    out = []
    for story in ranked[:top]:
        head = lead(story)
        others = sorted((i for i in story["items"] if i is not head), key=lambda i: order.get(i["source"], 999))
        out.append({"title": head["title"], "url": head["url"], "source": head["source"], "published_at": head["published_at"],
                    "outlets": len(story["sources"]), "also": [{"source": i["source"], "url": i["url"]} for i in others[:6]]})
    return out


def collect(feeds, now, workers=8):
    items, report = [], {}
    def one(feed):
        try:
            return feed["name"], headlines(feed, fetch(feed["feed"]), now), None
        except (OSError, ValueError, ET.ParseError, urllib.error.URLError) as e:
            return feed["name"], [], str(e)[:120]
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        for name, got, error in pool.map(one, feeds):
            items.extend(got)
            report[name] = error or len(got)
    return items, report


def build(feeds, items, report, now):
    order = {f["name"]: i for i, f in enumerate(feeds)}
    return {"schema": SCHEMA, "generated_at": now, "date": time.strftime("%Y-%m-%d", time.gmtime(now)), "window_hours": WINDOW // 3600,
            "stories": rank(items, order, now),
            "sources": [{"name": f["name"], "home": f["home"], "region": f["region"], "ok": not isinstance(report.get(f["name"]), str)} for f in feeds]}


def upload(site_url, secret, payload, timeout=60):
    body = gzip.compress(json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode(), mtime=0)
    ts, nonce = str(int(time.time())), secrets.token_hex(16)
    signature = hmac.new(secret.encode(), f"{ts}\n{nonce}\n".encode() + body, hashlib.sha256).hexdigest()
    request = urllib.request.Request(site_url.rstrip("/") + "/api/news/", data=body, method="POST", headers={
        "Content-Type": "application/octet-stream", "X-News-Timestamp": ts, "X-News-Nonce": nonce, "X-News-Signature": signature, "User-Agent": "monzero-news/1"})
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
    parser.add_argument("--feeds", required=True)
    parser.add_argument("--secret-file")
    parser.add_argument("--site-url", default="https://monzero.org")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    feeds = json.load(open(args.feeds, encoding="utf-8"))["feeds"]
    now = int(time.time())
    items, report = collect(feeds, now)
    payload = build(feeds, items, report, now)
    failed = [n for n, r in report.items() if isinstance(r, str)]
    if args.dry_run:
        for i, s in enumerate(payload["stories"], 1):
            print(f"{i:2}. [{s['outlets']}] {s['title']} ({s['source']})")
        print(f"{len(items)} headlines from {len(feeds) - len(failed)} of {len(feeds)} outlets" + (f"; failed: {', '.join(failed)}" if failed else ""))
        return
    if len(feeds) - len(failed) < 5:
        sys.exit(f"only {len(feeds) - len(failed)} outlets answered; keeping the published news")
    code, reply = upload(args.site_url, open(args.secret_file, encoding="utf-8").read().strip(), payload)
    if code != 200:
        sys.exit(f"website refused the news: HTTP {code} {reply}")
    print(f"uploaded {len(payload['stories'])} stories from {len(feeds) - len(failed)} outlets")


if __name__ == "__main__":
    main()
