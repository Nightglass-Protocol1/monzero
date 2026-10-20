// Homepage live tiles: node census, faucet and service status. Each tile fails on its own.
(function () {
  "use strict";
  const set = (id, text, cls) => { const el = document.getElementById(id); if (!el) return; el.textContent = text; if (cls !== undefined) el.className = cls; };
  const get = (url) => fetch(url, { headers: { Accept: "application/json" } }).then((r) => r.ok ? r.json() : Promise.reject(new Error(String(r.status))));

  const status = get("/api/status/");
  get("/api/v1/supply/").then((s) => {
    const d = s && s.data;
    if (!d || typeof d.circulating_supply !== "string") throw new Error("bad supply");
    set("metric-supply", `${Math.floor(Number(d.circulating_supply)).toLocaleString("en")} XMZ`);
  }).catch(() => set("metric-supply", "Unavailable"));
  get("/api/v1/network/nodes/").then((body) => {
    const d = body && body.data;
    if (!d || !d.totals) throw new Error("bad census");
    const countries = Object.keys(d.countries || {}).filter((c) => c !== "ZZ").length;
    set("tile-nodes", String(d.totals.observed));
    set("tile-nodes-detail", `in ${countries} ${countries === 1 ? "country" : "countries"}${d.stale ? " (census delayed)" : ""}`);
  }).catch(() => set("tile-nodes-detail", "Census unavailable right now"));

  Promise.all([get("/api/faucet/"), status.catch(() => null)]).then(([faucet, status]) => {
    const check = status && Array.isArray(status.checks) ? status.checks.find((c) => c.id === "faucet") : null;
    if (faucet.status === "open") {
      set("tile-faucet", "Open", check && check.state !== "ok" ? check.state : "");
      if (check && typeof check.days_left === "number") set("tile-faucet-detail", `Funded for about ${Math.floor(check.days_left)} days`);
    } else {
      set("tile-faucet", "Paused", "warn");
      set("tile-faucet-detail", "Claims are paused");
    }
  }).catch(() => set("tile-faucet-detail", "Faucet status unavailable"));

  get("/news/data/latest.json").then((d) => {
    if (!d || d.schema !== "monzero-news-v1" || !Array.isArray(d.stories) || !d.stories.length) return;
    const https = (v) => { try { return new URL(v).protocol === "https:"; } catch { return false; } };
    const list = document.getElementById("news-strip-list");
    list.replaceChildren(...d.stories.filter((s) => typeof s.title === "string" && https(s.url)).slice(0, 5).map((s) => {
      const li = document.createElement("li");
      const a = document.createElement("a");
      a.href = s.url; a.textContent = s.title; a.rel = "noopener noreferrer nofollow";
      const meta = document.createElement("small");
      meta.textContent = `${s.source}${s.outlets > 1 ? ` · ${s.outlets} outlets` : ""}`;
      li.append(a, meta);
      return li;
    }));
    if (list.children.length) document.getElementById("news-strip").hidden = false;
  }).catch(() => {});

  status.then((s) => {
    const bad = (s.checks || []).filter((c) => c.state !== "ok").length;
    set("tile-status", s.overall === "ok" ? "All working" : `${bad} need${bad === 1 ? "s" : ""} attention`, s.overall === "ok" ? "" : s.overall);
  }).catch(() => set("tile-status-detail", "Status unavailable right now"));
})();
