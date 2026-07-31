import { bindModalDismiss } from "./modal-dismiss.js";

// Sibling to confirmDialog: a promise-based modal that resolves the trimmed
// text typed into #group-modal-input (home.html-only, per CLAUDE.md), or
// null on Cancel/Escape/backdrop-click. Shares the same settle/dismiss shape
// as confirmDialog rather than home.js keeping its own copy.
export function promptDialog(message) {
  return new Promise((resolve) => {
    const modal = document.querySelector("#group-modal");
    const messageEl = document.querySelector("#group-modal-message");
    const input = document.querySelector("#group-modal-input");
    const cancelBtn = document.querySelector("#group-modal-cancel");
    const doneBtn = document.querySelector("#group-modal-done");

    if (!modal || !messageEl || !input || !cancelBtn || !doneBtn) {
      resolve(null);
      return;
    }

    messageEl.textContent = message;
    input.value = "";
    modal.classList.add("visible");
    input.focus();

    function settle(result) {
      modal.classList.remove("visible");
      doneBtn.removeEventListener("click", onDone);
      cancelBtn.removeEventListener("click", onCancel);
      document.removeEventListener("keydown", onEnterKey);
      unbindDismiss();
      resolve(result);
    }

    function onDone() {
      const value = input.value.trim();
      if (!value) {
        input.focus();
        return;
      }
      settle(value);
    }

    function onCancel() {
      settle(null);
    }

    function onEnterKey(event) {
      if (event.key === "Enter") onDone();
    }

    const unbindDismiss = bindModalDismiss(modal, () => settle(null));

    doneBtn.addEventListener("click", onDone);
    cancelBtn.addEventListener("click", onCancel);
    document.addEventListener("keydown", onEnterKey);
  });
}
