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
