import { getCookie } from "./lib/cookies.js";
import { confirmDialog } from "./lib/confirm-dialog.js";
import { promptDialog } from "./lib/prompt-dialog.js";

document.addEventListener("DOMContentLoaded", () => {
  const table = document.querySelector(".table-wrapper table");
  const selectAllCheckbox = document.querySelector("#select-all-rows");
  const bar = document.querySelector("#selection-bar");
  const countLabel = document.querySelector("#selection-count");
  const editButton = document.querySelector("#selection-edit");
  const groupButton = document.querySelector("#selection-group");
  const deleteButton = document.querySelector("#selection-delete");
  if (
    !table || !selectAllCheckbox || !bar || !countLabel || !editButton || !groupButton || !deleteButton
  ) return;

  const deleteUrl = bar.dataset.deleteUrl;
  const editUrlTemplate = bar.dataset.editUrlTemplate;
  const groupUrl = bar.dataset.groupUrl;

  function allCheckboxes() {
    return [...table.querySelectorAll(".row-select")];
  }

  function selectedCheckboxes() {
    return [...table.querySelectorAll(".row-select:checked")];
  }

  function updateSelectAllState() {
    const all = allCheckboxes();
    const checked = all.filter((checkbox) => checkbox.checked);
    selectAllCheckbox.checked = all.length > 0 && checked.length === all.length;
    selectAllCheckbox.indeterminate = checked.length > 0 && checked.length < all.length;
  }

  function updateBar() {
    const checked = selectedCheckboxes();
    countLabel.textContent = `${checked.length} selected`;
    bar.classList.toggle("visible", checked.length > 0);
    editButton.disabled = checked.length !== 1;
    groupButton.disabled = checked.length <= 1;
    updateSelectAllState();
  }

  table.addEventListener("change", (event) => {
    const checkbox = event.target;
    if (!checkbox.matches(".row-select")) return;

    checkbox.closest("tr").classList.toggle("selected", checkbox.checked);
    updateBar();
  });

  selectAllCheckbox.addEventListener("change", () => {
    const checked = selectAllCheckbox.checked;
    allCheckboxes().forEach((checkbox) => {
      checkbox.checked = checked;
      checkbox.closest("tr").classList.toggle("selected", checked);
    });
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
