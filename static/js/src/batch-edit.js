import { bindModalDismiss, lockBodyScroll, unlockBodyScroll } from "./lib/modal-dismiss.js";

document.addEventListener("DOMContentLoaded", () => {
  const openButton = document.querySelector("#open-add-modal");
  const modal = document.querySelector("#add-records-modal");
  const cancelButton = document.querySelector("#add-records-cancel");
  if (!openButton || !modal || !cancelButton) return;

  function close() {
    modal.classList.remove("visible");
    unlockBodyScroll();
  }

  openButton.addEventListener("click", () => {
    modal.classList.add("visible");
    lockBodyScroll();
  });
  cancelButton.addEventListener("click", close);

  bindModalDismiss(modal, close);
});
