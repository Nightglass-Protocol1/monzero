// Homepage panel: the same live donation figures as /fund/, in brief.
(function () {
  "use strict";
  const usd = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
  const percent = (part, whole) => {
    const value = Math.min(100, part / whole * 100);
    return (value > 0 && value < 1 ? value.toFixed(1) : Math.floor(value).toString()) + "%";
  };
  const set = (id, text) => { const node = document.getElementById(id); if (node) node.textContent = text; };
  const width = (id, part, whole) => { const node = document.getElementById(id); if (node) node.style.width = Math.min(100, part / whole * 100).toFixed(1) + "%"; };
  fetch("api/donations/", { cache: "no-cache" })
    .then((response) => (response.ok ? response.json() : Promise.reject(new Error(String(response.status)))))
    .then((data) => {
      let received = 0, count = 0;
      for (const coin of data.coins) {
        if (coin.received === null) continue;
        received += Number(BigInt(coin.received)) / 10 ** coin.decimals * (data.pricesUsd[coin.id] || 0);
        count += coin.transactions;
      }
      set("support-raised", usd.format(received));
      set("support-count", count.toLocaleString("en-US"));
      set("support-goal-percent", percent(Math.min(received, 15000), 15000));
      width("support-goal-bar", received, 15000);
      set("support-all-percent", percent(received, 20000));
      width("support-all-bar", received, 20000);
      set("support-status", "Live from public block explorers, valued in US dollars at today's prices.");
    })
    .catch(() => set("support-status", "Live figures are not available right now; see monzero.org/fund/."));
})();
