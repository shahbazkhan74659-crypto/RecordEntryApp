// Shared "close a modal on backdrop click or Escape" wiring, previously
// reimplemented independently in confirm-dialog.js, home.js (promptDialog),
// account-settings.js, login.js, and batch-edit.js.
//
// The Escape handler is gated on the modal actually having the "visible"
// class: callers that bind once for the whole page lifetime (account
// settings, forgot password, batch-edit's add-records modal) rely on this so
// Escape presses elsewhere on the page don't trigger a dismiss while the
// modal isn't open. Callers that bind per-open (confirmDialog, promptDialog)
// are unaffected either way, since the modal is only visible while their
// listeners are attached.
export function bindModalDismiss(modal, onDismiss) {
  function onOverlayClick(event) {
    if (event.target === modal) onDismiss();
  }

  function onKeydown(event) {
    if (event.key === "Escape" && modal.classList.contains("visible")) onDismiss();
  }

  modal.addEventListener("click", onOverlayClick);
  document.addEventListener("keydown", onKeydown);

  return function unbindModalDismiss() {
    modal.removeEventListener("click", onOverlayClick);
    document.removeEventListener("keydown", onKeydown);
  };
}

// Shared body-scroll lock so page content behind a fixed modal-overlay
// can't be scrolled while a modal is open. Reference-counted so it stays
// correct even if two lock calls somehow overlap (e.g. the Save+Range
// stacked-modal case on home.js, where a second lock can fire before the
// first has been released) — only the outermost lock/unlock pair actually
// touches the DOM.
//
// Plain `overflow: hidden` on <body> (the original approach here) stops
// desktop mouse-wheel scrolling but is well known to NOT reliably stop
// touch-drag scrolling of the background page on iOS Safari. The standard
// workaround is used instead: pin the body in place with `position: fixed`
// (which removes it from the normal scrollable flow entirely, on every
// browser) after recording the current scroll offset, then restore both
// the position and the exact scroll offset on unlock so the page doesn't
// visibly jump.
let lockCount = 0;
let savedScrollY = 0;

export function lockBodyScroll() {
  if (lockCount === 0) {
    savedScrollY = window.scrollY || window.pageYOffset || 0;
    document.body.style.position = "fixed";
    document.body.style.top = `-${savedScrollY}px`;
    document.body.style.left = "0";
    document.body.style.right = "0";
    document.body.style.width = "100%";
  }
  lockCount += 1;
}

export function unlockBodyScroll() {
  lockCount = Math.max(0, lockCount - 1);
  if (lockCount === 0) {
    document.body.style.position = "";
    document.body.style.top = "";
    document.body.style.left = "";
    document.body.style.right = "";
    document.body.style.width = "";
    window.scrollTo(0, savedScrollY);
  }
}
