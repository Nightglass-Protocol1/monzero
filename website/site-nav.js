// Shared Menu button and submenus for the site header (every page).
(function () {
  "use strict";
  const button = document.querySelector(".site-header .menu-toggle");
  const nav = document.getElementById("site-nav");
  if (!nav) return;
  nav.classList.add("nav-js");
  const groups = Array.from(nav.querySelectorAll(".nav-group"));
  const setGroup = (group, open) => {
    group.classList.toggle("open", open);
    group.classList.toggle("dismissed", !open && group.contains(document.activeElement));
    const toggle = group.querySelector(".nav-sub-toggle");
    if (toggle) toggle.setAttribute("aria-expanded", String(open));
  };
  const closeGroups = (except) => groups.forEach((g) => { if (g !== except) setGroup(g, false); });
  const close = () => {
    closeGroups();
    if (button) { nav.classList.remove("open"); button.setAttribute("aria-expanded", "false"); }
  };
  if (button) button.addEventListener("click", () => button.setAttribute("aria-expanded", String(nav.classList.toggle("open"))));
  groups.forEach((group) => {
    const toggle = group.querySelector(".nav-sub-toggle");
    if (!toggle) return;
    toggle.addEventListener("click", (event) => {
      event.stopPropagation();
      const open = !group.classList.contains("open");
      closeGroups(group);
      setGroup(group, open);
    });
    // Leaving a group with the keyboard closes it; Escape keeps it shut until the pointer or focus leaves.
    group.addEventListener("focusout", (event) => { if (!group.contains(event.relatedTarget)) { setGroup(group, false); group.classList.remove("dismissed"); } });
    group.addEventListener("mouseleave", () => group.classList.remove("dismissed"));
    group.addEventListener("focusin", () => group.classList.remove("dismissed"));
  });
  nav.querySelectorAll("a").forEach((link) => link.addEventListener("click", close));
  document.addEventListener("click", (event) => { if (!nav.contains(event.target)) closeGroups(); });
  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    const open = groups.find((g) => g.classList.contains("open") || g.contains(document.activeElement));
    if (open && window.matchMedia("(min-width: 1340px)").matches) {
      const toggle = open.querySelector(".nav-sub-toggle");
      if (toggle && open.contains(document.activeElement)) toggle.focus();
      setGroup(open, false);
      return;
    }
    close();
  });
})();

// Scrolling headline banner above the header on public pages (not /admin). Reads
// /news/data/latest.json and stays absent when there is no news.
(function () {
  "use strict";
  const header = document.querySelector(".site-header");
  const nav = document.getElementById("site-nav");
  if (!header || !nav || nav.getAttribute("aria-label") !== "Primary navigation" || document.getElementById("news-ticker")) return;
  const ticker = document.createElement("div");
  ticker.className = "news-ticker"; ticker.id = "news-ticker"; ticker.hidden = true;
  ticker.setAttribute("role", "region"); ticker.setAttribute("aria-label", "Top crypto headlines");
  const label = document.createElement("a");
  label.className = "ticker-label"; label.href = "/news/"; label.textContent = "Crypto news";
  const viewport = document.createElement("div");
  viewport.className = "ticker-viewport";
  const track = document.createElement("ul");
  track.className = "ticker-track"; track.id = "ticker-track";
  viewport.append(track);
  const pause = document.createElement("button");
  pause.className = "ticker-pause"; pause.id = "ticker-pause"; pause.type = "button";
  pause.setAttribute("aria-pressed", "false"); pause.setAttribute("aria-label", "Pause the headlines");
  ticker.append(label, viewport, pause);
  header.before(ticker);
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
