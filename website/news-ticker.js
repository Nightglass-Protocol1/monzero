// Scrolling headline banner (homepage). Reads news/data/latest.json; stays hidden without news.
(function () {
  "use strict";
  const ticker = document.getElementById("news-ticker");
  const track = document.getElementById("ticker-track");
  const pause = document.getElementById("ticker-pause");
  if (!ticker || !track || !pause) return;
  const https = (v) => { try { const u = new URL(v); return u.protocol === "https:" && !u.username && !u.password; } catch { return false; } };

  function item(story, copy) {
    const li = document.createElement("li");
    const a = document.createElement("a");
    a.href = story.url;
    a.rel = "noopener noreferrer nofollow";
    a.textContent = story.title;
    const source = document.createElement("small");
    source.textContent = story.source;
    li.append(a, source);
    // The second copy only makes the loop seamless: hide it from screen readers and the Tab key.
    if (copy) { li.setAttribute("aria-hidden", "true"); a.tabIndex = -1; }
    return li;
  }

  fetch("/news/data/latest.json", { headers: { Accept: "application/json" }, cache: "no-cache" })
    .then((r) => (r.ok ? r.json() : null))
    .then((d) => {
      if (!d || d.schema !== "monzero-news-v1" || !Array.isArray(d.stories)) return;
      const stories = d.stories.filter((s) => s && typeof s.title === "string" && s.title.length <= 300 && typeof s.source === "string" && https(s.url));
      if (!stories.length) return;
      track.replaceChildren(...stories.map((s) => item(s, false)), ...stories.map((s) => item(s, true)));
      ticker.hidden = false;
      // Constant reading speed (about 60 px per second) whatever the number of headlines.
      const width = track.scrollWidth / 2;
      track.style.setProperty("--ticker-duration", `${Math.max(30, Math.round(width / 60))}s`);
    })
    .catch(() => {});

  pause.addEventListener("click", () => {
    const paused = ticker.classList.toggle("paused");
    pause.setAttribute("aria-pressed", String(paused));
    pause.setAttribute("aria-label", paused ? "Play the headlines" : "Pause the headlines");
  });
})();
