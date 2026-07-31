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
// can't be touch-scrolled while a modal is open. Reference-counted so it
// stays correct even if two lock calls somehow overlap (e.g. a caller
// re-opening before a previous close's unlock has run); restores the
// exact previous inline value on full unlock rather than assuming "".
let lockCount = 0;
let previousBodyOverflow = "";

export function lockBodyScroll() {
  if (lockCount === 0) previousBodyOverflow = document.body.style.overflow;
  lockCount += 1;
  document.body.style.overflow = "hidden";
}

export function unlockBodyScroll() {
  lockCount = Math.max(0, lockCount - 1);
  if (lockCount === 0) document.body.style.overflow = previousBodyOverflow;
}
