import { getCookie } from "./lib/cookies.js";
import { confirmDialog } from "./lib/confirm-dialog.js";

document.addEventListener("DOMContentLoaded", () => {
  const table = document.querySelector(".table-wrapper table");
  const bar = document.querySelector("#selection-bar");
  const countLabel = document.querySelector("#selection-count");
  const editButton = document.querySelector("#selection-edit");
  const groupButton = document.querySelector("#selection-group");
  const deleteButton = document.querySelector("#selection-delete");
  const confirmModal = document.querySelector("#confirm-modal");
  const confirmMessage = document.querySelector("#confirm-modal-message");
  const confirmCancel = document.querySelector("#confirm-modal-cancel");
  const confirmConfirm = document.querySelector("#confirm-modal-confirm");
  const groupModal = document.querySelector("#group-modal");
  const groupMessage = document.querySelector("#group-modal-message");
  const groupInput = document.querySelector("#group-modal-input");
  const groupCancel = document.querySelector("#group-modal-cancel");
  const groupDone = document.querySelector("#group-modal-done");
  if (
    !table || !bar || !countLabel || !editButton || !groupButton || !deleteButton ||
    !confirmModal || !confirmMessage || !confirmCancel || !confirmConfirm ||
    !groupModal || !groupMessage || !groupInput || !groupCancel || !groupDone
  ) return;

  const deleteUrl = bar.dataset.deleteUrl;
  const editUrlTemplate = bar.dataset.editUrlTemplate;
  const groupUrl = bar.dataset.groupUrl;

  function promptDialog(message) {
    return new Promise((resolve) => {
      groupMessage.textContent = message;
      groupInput.value = "";
      groupModal.classList.add("visible");
      groupInput.focus();

      function settle(result) {
        groupModal.classList.remove("visible");
        groupDone.removeEventListener("click", onDone);
        groupCancel.removeEventListener("click", onCancel);
        groupModal.removeEventListener("click", onOverlayClick);
        document.removeEventListener("keydown", onKeydown);
        resolve(result);
      }

      function onDone() {
        const value = groupInput.value.trim();
        if (!value) {
          groupInput.focus();
          return;
        }
        settle(value);
      }

      function onCancel() {
        settle(null);
      }

      function onOverlayClick(event) {
        if (event.target === groupModal) settle(null);
      }

      function onKeydown(event) {
        if (event.key === "Escape") settle(null);
        if (event.key === "Enter") onDone();
      }

      groupDone.addEventListener("click", onDone);
      groupCancel.addEventListener("click", onCancel);
      groupModal.addEventListener("click", onOverlayClick);
      document.addEventListener("keydown", onKeydown);
    });
  }

  function selectedCheckboxes() {
    return [...table.querySelectorAll(".row-select:checked")];
  }

  function updateBar() {
    const checked = selectedCheckboxes();
    countLabel.textContent = `${checked.length} selected`;
    bar.classList.toggle("visible", checked.length > 0);
    editButton.disabled = checked.length !== 1;
    groupButton.disabled = checked.length <= 1;
  }

  table.addEventListener("change", (event) => {
    const checkbox = event.target;
    if (!checkbox.matches(".row-select")) return;

    checkbox.closest("tr").classList.toggle("selected", checkbox.checked);
    updateBar();
  });

  editButton.addEventListener("click", () => {
    const checked = selectedCheckboxes();
    if (checked.length !== 1) return;

    window.location.href = editUrlTemplate.replace("/0/", `/${checked[0].value}/`);
  });

  groupButton.addEventListener("click", async () => {
    const checked = selectedCheckboxes();
    if (checked.length <= 1) return;

    const name = await promptDialog(`Name this batch of ${checked.length} entries.`);
    if (!name) return;

    const body = new URLSearchParams();
    checked.forEach((checkbox) => body.append("ids", checkbox.value));
    body.append("name", name);

    const response = await fetch(groupUrl, {
      method: "POST",
      headers: { "X-CSRFToken": getCookie("csrftoken") },
      body,
    });

    if (!response.ok) {
      window.alert("Could not group the selected entries. Please try again.");
      return;
    }

    checked.forEach((checkbox) => {
      checkbox.checked = false;
      checkbox.closest("tr").classList.remove("selected");
    });
    updateBar();
    window.showToast(`Grouped ${checked.length} entries into "${name}".`, "success");
  });

  deleteButton.addEventListener("click", async () => {
    const checked = selectedCheckboxes();
    if (checked.length === 0) return;

    const confirmed = await confirmDialog(
      `Delete ${checked.length} selected ${checked.length === 1 ? "entry" : "entries"}? This cannot be undone.`
    );
    if (!confirmed) return;

    const body = new URLSearchParams();
    checked.forEach((checkbox) => body.append("ids", checkbox.value));

    const response = await fetch(deleteUrl, {
      method: "POST",
      headers: { "X-CSRFToken": getCookie("csrftoken") },
      body,
    });

    if (!response.ok) {
      window.alert("Could not delete the selected entries. Please try again.");
      return;
    }

    checked.forEach((checkbox) => checkbox.closest("tr").remove());
    updateBar();
    window.showToast(`Deleted ${checked.length} ${checked.length === 1 ? "entry" : "entries"}.`, "error");
  });
});
