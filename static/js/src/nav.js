// Mobile off-canvas sidebar drawer for the shared app shell
// (templates/base.html). Loaded unconditionally (like messages.js) since
// the hamburger itself is part of the shell chrome, not gated behind auth.
//
// The sidebar (#sidebar) IS the drawer -- toggling ".mobile-open" slides it
// in/out via CSS transform (see style.css's 768px query). #mobile-nav-overlay
// is just the click-to-dismiss backdrop behind it, reusing the same
// .modal-overlay/"visible" convention every other modal in this app uses
// (via bindModalDismiss/lockBodyScroll below) -- unlike the old top-nav
// version of this file, no DOM nodes are relocated.
import { bindModalDismiss, lockBodyScroll, unlockBodyScroll } from "./lib/modal-dismiss.js";

document.addEventListener("DOMContentLoaded", () => {
  const toggleBtn = document.querySelector("#mobile-nav-toggle");
  const overlay = document.querySelector("#mobile-nav-overlay");
  const sidebar = document.querySelector("#sidebar");

  if (!toggleBtn || !overlay || !sidebar) return;

  let isOpen = false;

  function openMenu() {
    if (isOpen) return;
    isOpen = true;
    sidebar.classList.add("mobile-open");
    overlay.classList.add("visible");
    toggleBtn.setAttribute("aria-expanded", "true");
    lockBodyScroll();
  }

  function closeMenu() {
    if (!isOpen) return;
    isOpen = false;
    sidebar.classList.remove("mobile-open");
    overlay.classList.remove("visible");
    toggleBtn.setAttribute("aria-expanded", "false");
    unlockBodyScroll();
  }

  toggleBtn.addEventListener("click", () => {
    if (isOpen) closeMenu();
    else openMenu();
  });

  bindModalDismiss(overlay, closeMenu);

  // Nicety, not a requirement: close the drawer when the sidebar's
  // mobile-only Account Setting button is clicked, so the Account Settings
  // modal doesn't open on top of a still-open drawer. This adds a second,
  // independent click listener on the same button — account-settings.js's
  // own listener (which does the actual modal-opening work) is untouched.
  const mobileSettingsBtn = document.querySelector("#open-account-settings-mobile");
  if (mobileSettingsBtn) {
    mobileSettingsBtn.addEventListener("click", closeMenu);
  }

  // If the viewport grows back past the mobile breakpoint while the
  // drawer is open (e.g. rotating a tablet, or a desktop resize during
  // testing), close it immediately rather than leaving it open behind a
  // now-hidden backdrop.
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
