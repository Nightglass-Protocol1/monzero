// Homepage live tiles: node census, faucet and service status. Each tile fails on its own.
(function () {
  "use strict";
  const set = (id, text, cls) => { const el = document.getElementById(id); if (!el) return; el.textContent = text; if (cls !== undefined) el.className = cls; };
  const get = (url) => fetch(url, { headers: { Accept: "application/json" } }).then((r) => r.ok ? r.json() : Promise.reject(new Error(String(r.status))));

  const status = get("/api/status/");
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

  status.then((s) => {
    const bad = (s.checks || []).filter((c) => c.state !== "ok").length;
    set("tile-status", s.overall === "ok" ? "All working" : `${bad} need${bad === 1 ? "s" : ""} attention`, s.overall === "ok" ? "" : s.overall);
  }).catch(() => set("tile-status-detail", "Status unavailable right now"));
})();
