// Mobile off-canvas nav drawer for the shared header (templates/base.html).
// Loaded unconditionally (like messages.js) since the hamburger itself is
// part of the header chrome, not gated behind auth the way
// account-settings.js is — the drawer just relocates whatever .site-nav
// currently contains (the authenticated Account Setting/Logout controls,
// or the anonymous "Login" link), so it works either way with no changes
// needed here for the logged-out case.
//
// Key design point: the Home/Batch <a class="nav-link"> anchors and the
// <nav class="site-nav"> element (which contains #open-account-settings)
// are never duplicated. Opening the drawer physically moves those exact
// DOM nodes into #mobile-nav-panel; closing it (or resizing back past the
// mobile breakpoint while open) moves them back to their original spot in
// the header. A comment-node placeholder is left behind at each node's
// original position so "move back" always restores the exact original
// location, regardless of what else happens in between — this is what
// keeps #open-account-settings a single element in the DOM at all times,
// so account-settings.js's existing `querySelector("#open-account-settings")`
// keeps working unchanged.
import { bindModalDismiss, lockBodyScroll, unlockBodyScroll } from "./lib/modal-dismiss.js";

document.addEventListener("DOMContentLoaded", () => {
  const toggleBtn = document.querySelector("#mobile-nav-toggle");
  const overlay = document.querySelector("#mobile-nav-overlay");
  const panel = document.querySelector("#mobile-nav-panel");
  const closeBtn = document.querySelector("#mobile-nav-close");
  const brandGroup = document.querySelector(".brand-group");
  const siteNav = document.querySelector(".site-nav");

  if (!toggleBtn || !overlay || !panel || !closeBtn || !brandGroup || !siteNav) return;

  const navLinks = Array.from(brandGroup.querySelectorAll(".nav-link"));
  const movable = [...navLinks, siteNav];

  // Record each movable node's original position with a comment-node
  // marker placed immediately before it, so moveBack() can restore it
  // exactly where it came from.
  const placeholders = movable.map((el) => {
    const marker = document.createComment("mobile-nav-slot");
    el.before(marker);
    return { el, marker };
  });

  let isOpen = false;
  let moveBackTimer = null;

  function moveIntoPanel() {
    clearTimeout(moveBackTimer);
    movable.forEach((el) => panel.appendChild(el));
  }

  function moveBack() {
    placeholders.forEach(({ el, marker }) => marker.after(el));
  }

  function openMenu() {
    if (isOpen) return;
    isOpen = true;
    moveIntoPanel();
    overlay.classList.add("visible");
    toggleBtn.setAttribute("aria-expanded", "true");
    lockBodyScroll();
  }

  function closeMenu() {
    if (!isOpen) return;
    isOpen = false;
    overlay.classList.remove("visible");
    toggleBtn.setAttribute("aria-expanded", "false");
    unlockBodyScroll();
    // Wait for the panel's slide-out transition (see .mobile-nav-panel's
    // 0.25s transform transition in style.css) before relocating the real
    // nodes back to the header — moving them out immediately would empty
    // the panel mid-animation, showing a blank drawer still sliding away.
    // The timer is cleared in moveIntoPanel() if the menu is reopened
    // before it fires.
    moveBackTimer = setTimeout(moveBack, 250);
  }

  toggleBtn.addEventListener("click", () => {
    if (isOpen) closeMenu();
    else openMenu();
  });

  closeBtn.addEventListener("click", closeMenu);
  bindModalDismiss(overlay, closeMenu);

  // Nicety, not a requirement: close the drawer when "Account Setting" is
  // clicked from inside it, so the Account Settings modal doesn't open on
  // top of a still-open nav drawer. This adds a second, independent click
  // listener on the same real button — account-settings.js's own listener
  // (which does the actual modal-opening work) is untouched and keeps
  // working exactly as before.
  const accountSettingsBtn = siteNav.querySelector("#open-account-settings");
  if (accountSettingsBtn) {
    accountSettingsBtn.addEventListener("click", closeMenu);
  }

  // If the viewport grows back past the mobile breakpoint while the
  // drawer is open (e.g. rotating a tablet, or a desktop resize during
  // testing), close it immediately rather than leaving the real nav nodes
  // stranded inside a now-hidden mobile-only panel.
  const mobileQuery = window.matchMedia("(max-width: 768px)");
  function handleBreakpointChange(event) {
    if (!event.matches && isOpen) closeMenu();
  }
  if (typeof mobileQuery.addEventListener === "function") {
    mobileQuery.addEventListener("change", handleBreakpointChange);
  } else if (typeof mobileQuery.addListener === "function") {
    mobileQuery.addListener(handleBreakpointChange);
  }
});
