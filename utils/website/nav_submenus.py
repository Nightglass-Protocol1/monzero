"""Add the hover/focus submenus to every page's existing header navigation.

  python3 -I utils/website/nav_submenus.py            # rewrite pages in place
  python3 -I utils/website/nav_submenus.py --check    # exit 1 if any page is out of date

The owner's top-level links are kept exactly as each page has them (labels, order, relative or
absolute hrefs); this only wraps six of them with a submenu. Re-running it is idempotent.
The faucet's PHP header reads website/lib/site-nav-submenus.json, which this script also writes.
"""
import html, json, re, sys
from pathlib import Path

WEBSITE = Path(__file__).resolve().parents[2] / "website"
SUBMENUS = {
    "Explorer": [("/explorer/", "Block explorer"), ("/network/", "Network history"), ("/network/nodes/", "Node map")],
    "Stats": [("/stats/", "Network stats"), ("/markets/", "Markets"), ("/exchanges/", "Exchanges")],
    "Public wallets": [("/wallets/", "Public wallets"), ("/payments/request/", "Payment request")],
    "Roadmap": [("/roadmap/", "Roadmap"), ("/community/", "Community"), ("/community/bounties/", "Bounty board"), ("/ecosystem/", "Ecosystem")],
    "Whitepaper": [("/WHITEPAPER.md?rev=1.5-20261017", "Whitepaper"), ("/developers/", "Developers"), ("/developers/api/", "API v1"),
                   ("/developers/payments/", "Accept XMZ")],
    "Mining": [("/#mine", "How to mine"), ("/mining/calculator/", "Mining calculator"), ("/mining/dashboard/", "Your mining"),
               ("/mining/benchmarks/", "CPU benchmarks"), ("/mining/leaderboard/", "Mining leaderboard"), ("/faucet/", "Faucet")],
}
NAV = re.compile(r'(<nav id="site-nav" aria-label="Primary navigation">)(.*?)(</nav>)', re.S)
TOP = re.compile(r'<a href="([^"]*)"( aria-current="page")?>([^<]*)</a>')


def slug(label):
    return re.sub(r"[^a-z]+", "-", label.lower()).strip("-")


def page_path(file):
    rel = file.relative_to(WEBSITE).parent.as_posix()
    return "/" if rel == "." else f"/{rel}/"


def render(inner, path):
    # Strip a previous run, keeping only the original top-level anchors.
    inner = re.sub(r'<div class="nav-sub"[^>]*>.*?</div>', "", inner, flags=re.S)
    inner = re.sub(r'<button class="nav-sub-toggle".*?</button>', "", inner, flags=re.S)
    inner = re.sub(r'</?div[^>]*>', "", inner)
    anchors = TOP.findall(inner)
    if not anchors or TOP.sub("", inner).strip():
        raise ValueError("unexpected navigation markup")
    out = []
    for href, current, label in anchors:
        subs = SUBMENUS.get(html.unescape(label))
        if not subs:
            out.append(f'<a href="{href}"{current}>{label}</a>')
            continue
        here = [h for h, _ in subs if h.split("?")[0] == path and h != "/#mine"]
        group = ' class="nav-group current"' if here or current else ' class="nav-group"'
        top_current = current if not here or here[0] == subs[0][0] else ""
        mark = ' aria-current="page"'
        items = "".join(f'<a href="{h}"{mark if h in here and h != subs[0][0] else ""}>{html.escape(t)}</a>' for h, t in subs)
        sid = f"nav-sub-{slug(label)}"
        out.append(f'<div{group}><a href="{href}"{top_current}>{label}</a>'
                   f'<button class="nav-sub-toggle" type="button" aria-expanded="false" aria-controls="{sid}">'
                   f'<span class="visually-hidden">{label} pages</span></button>'
                   f'<div class="nav-sub" id="{sid}">{items}</div></div>')
    return "".join(out)


def main():
    check = "--check" in sys.argv[1:]
    stale = []
    for file in sorted(WEBSITE.rglob("*.html")):
        text = file.read_text(encoding="utf-8")
        match = NAV.search(text)
        if not match:
            continue
        updated = text[:match.start(2)] + render(match.group(2), page_path(file)) + text[match.end(2):]
        if updated != text:
            stale.append(file.relative_to(WEBSITE).as_posix())
            if not check:
                file.write_text(updated, encoding="utf-8")
    data = json.dumps({k: v for k, v in SUBMENUS.items()}, indent=1) + "\n"
    target = WEBSITE / "lib/site-nav-submenus.json"
    if not target.exists() or target.read_text(encoding="utf-8") != data:
        stale.append("lib/site-nav-submenus.json")
        if not check:
            target.write_text(data, encoding="utf-8")
    if check and stale:
        sys.exit("navigation submenus out of date: " + ", ".join(stale))
    print(("up to date" if not stale else "updated: " + ", ".join(stale)) if not check else "navigation submenus up to date")


if __name__ == "__main__":
    main()
