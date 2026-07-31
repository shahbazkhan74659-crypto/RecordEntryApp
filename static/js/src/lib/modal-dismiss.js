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
