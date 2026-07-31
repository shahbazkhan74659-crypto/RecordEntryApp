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

    function settle(result) {
      modal.classList.remove("visible");
      confirmBtn.removeEventListener("click", onConfirm);
      cancelBtn.removeEventListener("click", onCancel);
      modal.removeEventListener("click", onOverlayClick);
      document.removeEventListener("keydown", onKeydown);
      resolve(result);
    }

    function onConfirm() {
      settle(true);
    }

    function onCancel() {
      settle(false);
    }

    function onOverlayClick(event) {
      if (event.target === modal) settle(false);
    }

    function onKeydown(event) {
      if (event.key === "Escape") settle(false);
    }

    confirmBtn.addEventListener("click", onConfirm);
    cancelBtn.addEventListener("click", onCancel);
    modal.addEventListener("click", onOverlayClick);
    document.addEventListener("keydown", onKeydown);
  });
}
