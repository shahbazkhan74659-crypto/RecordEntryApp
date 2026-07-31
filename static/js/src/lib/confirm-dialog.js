import { bindModalDismiss, lockBodyScroll, unlockBodyScroll } from "./modal-dismiss.js";

export function confirmDialog(message) {
  return new Promise((resolve) => {
    const modal = document.querySelector("#confirm-modal");
    const messageEl = document.querySelector("#confirm-modal-message");
    const confirmBtn = document.querySelector("#confirm-modal-confirm");
    const cancelBtn = document.querySelector("#confirm-modal-cancel");

    if (!modal || !messageEl || !confirmBtn || !cancelBtn) {
      resolve(false);
      return;
    }

    messageEl.textContent = message;
    modal.classList.add("visible");
    lockBodyScroll();

    function settle(result) {
      modal.classList.remove("visible");
      unlockBodyScroll();
      confirmBtn.removeEventListener("click", onConfirm);
      cancelBtn.removeEventListener("click", onCancel);
      unbindDismiss();
      resolve(result);
    }

    function onConfirm() {
      settle(true);
    }

    function onCancel() {
      settle(false);
    }

    const unbindDismiss = bindModalDismiss(modal, () => settle(false));

    confirmBtn.addEventListener("click", onConfirm);
    cancelBtn.addEventListener("click", onCancel);
  });
}
