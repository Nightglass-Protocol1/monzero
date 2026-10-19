// Shared Menu button for the site header (every page).
(function () {
  "use strict";
  const button = document.querySelector(".site-header .menu-toggle");
  const nav = document.getElementById("site-nav");
  if (!button || !nav) return;
  const close = () => { nav.classList.remove("open"); button.setAttribute("aria-expanded", "false"); };
  button.addEventListener("click", () => button.setAttribute("aria-expanded", String(nav.classList.toggle("open"))));
  nav.querySelectorAll("a").forEach((link) => link.addEventListener("click", close));
  document.addEventListener("keydown", (event) => { if (event.key === "Escape") close(); });
})();
