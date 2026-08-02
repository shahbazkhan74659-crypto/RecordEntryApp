import { getCookie } from "./lib/cookies.js";
import { confirmDialog } from "./lib/confirm-dialog.js";
import { promptDialog } from "./lib/prompt-dialog.js";
import { bindModalDismiss, lockBodyScroll, unlockBodyScroll } from "./lib/modal-dismiss.js";
import { downloadPdf } from "./lib/download-pdf.js";
import { initDateSearchFilter } from "./lib/date-search-filter.js";

// Row-selection checkboxes + the floating selection bar's Edit/Group/Delete/
// Download actions. Split out from the "Save" PDF-export modal below (see
// initSaveModal) since the two features share no state beyond `bar` and
// `downloadUrl` — kept as two named functions instead of one long inline
// callback so each reads as a single responsibility.
function initSelectionBar({
  table, selectAllCheckbox, bar, countLabel, editButton, groupButton, deleteButton, downloadButton,
  deleteUrl, editUrlTemplate, groupUrl, downloadUrl, mainContainer,
}) {
  function allCheckboxes() {
    return [...table.querySelectorAll(".row-select")];
  }

  function selectedCheckboxes() {
    return [...table.querySelectorAll(".row-select:checked")];
  }

  // Shared by the Group and Download handlers below: both leave the rows
  // themselves in the DOM (unlike Delete, which removes the <tr> entirely)
  // but need to uncheck and un-highlight whatever was just acted on.
  function clearSelection(checked) {
    checked.forEach((checkbox) => {
      checkbox.checked = false;
      checkbox.closest("tr").classList.remove("selected");
    });
  }

  function updateSelectAllState() {
    const all = allCheckboxes();
    const checked = all.filter((checkbox) => checkbox.checked);
    selectAllCheckbox.checked = all.length > 0 && checked.length === all.length;
    selectAllCheckbox.indeterminate = checked.length > 0 && checked.length < all.length;
  }

  function updateBar() {
    const checked = selectedCheckboxes();
    const hasSelection = checked.length > 0;
    countLabel.textContent = `${checked.length} selected`;
    bar.classList.toggle("visible", hasSelection);
    // Reserves extra bottom space below the table/pagination while the
    // floating selection bar is visible, so on short mobile viewports the
    // bar (fixed, bottom: 40px) doesn't cover the last table row(s) or the
    // pagination links sitting just above the page's own bottom padding.
    if (mainContainer) mainContainer.classList.toggle("has-selection-bar", hasSelection);
    editButton.disabled = checked.length !== 1;
    groupButton.disabled = checked.length <= 1;
    downloadButton.disabled = checked.length === 0;
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
      const data = await response.json().catch(() => null);
      window.showToast(data?.error || "Could not group the selected entries. Please try again.", "error");
      return;
    }

    clearSelection(checked);
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
      const data = await response.json().catch(() => null);
      window.showToast(data?.error || "Could not delete the selected entries. Please try again.", "error");
      return;
    }

    checked.forEach((checkbox) => checkbox.closest("tr").remove());
    updateBar();
    window.showToast(`Deleted ${checked.length} ${checked.length === 1 ? "entry" : "entries"}.`, "error");
  });

  downloadButton.addEventListener("click", async () => {
    const checked = selectedCheckboxes();
    if (checked.length === 0) return;

    const succeeded = await downloadPdf(downloadUrl, {
      scope: "choose",
      ids: checked.map((checkbox) => checkbox.value),
    });
    if (!succeeded) return;

    clearSelection(checked);
    updateBar();
  });
}

// The "Save" button's PDF-export menu, plus the stacked "Save by Range"
// sub-modal it can open on top of itself. Only needs `bar` (for
// data-entry-count) and `downloadUrl` from the selection-bar markup — see
// initSelectionBar above for why the two are split into separate functions.
function initSaveModal(bar, downloadUrl) {
  const saveButton = document.querySelector("#save-pdf-btn");
  const saveModal = document.querySelector("#save-modal");
  const saveModalCancel = document.querySelector("#save-modal-cancel");
  const saveOptionButtons = saveModal ? [...saveModal.querySelectorAll(".save-option-btn[data-scope]")] : [];
  const byRangeButton = document.querySelector("#by-range-btn");
  const rangeModal = document.querySelector("#range-modal");
  const rangeModalCancel = document.querySelector("#range-modal-cancel");
  const rangeOptionsContainer = document.querySelector("#range-options");
  const entryCount = Number(bar.dataset.entryCount);

  if (!saveButton || !saveModal || !saveModalCancel || !saveOptionButtons.length) return;

  function closeSaveModal() {
    // A single Escape press fires both this modal's and the range modal's
    // bindModalDismiss listeners; when the range modal is open on top,
    // redirect to closing that one first so Escape closes the topmost
    // modal only (a second press then closes this one as normal).
    if (rangeModal && rangeModal.classList.contains("visible")) {
      closeRangeModal();
      return;
    }
    saveModal.classList.remove("visible");
    unlockBodyScroll();
  }

  function closeRangeModal() {
    rangeModal.classList.remove("visible");
    unlockBodyScroll();
  }

  // Ranges of 100 beyond the first 100 (101-200, 201-300, ...), extending
  // only as long as more than 20 records remain past the last boundary —
  // mirrors "Last 100" etc.'s '-id' most-recent-first ordering. Returned
  // highest-first so the newest (most recently reachable) range shows
  // first in the grid, matching "Last 100" already showing the newest end.
  function buildRanges(count) {
    const ranges = [];
    let boundary = 100;
    while (count - boundary > 20) {
      ranges.push({ start: boundary + 1, end: boundary + 100 });
      boundary += 100;
    }
    return ranges.reverse();
  }

  saveButton.addEventListener("click", () => {
    saveModal.classList.add("visible");
    lockBodyScroll();
  });

  saveModalCancel.addEventListener("click", closeSaveModal);
  bindModalDismiss(saveModal, closeSaveModal);

  saveOptionButtons.forEach((button) => {
    button.addEventListener("click", async () => {
      const scope = button.dataset.scope;
      closeSaveModal();

      if (scope === "choose") {
        window.showToast("Select the records you want, then click the download button.", "success");
        return;
      }

      await downloadPdf(downloadUrl, { scope });
    });
  });

  if (byRangeButton && rangeModal && rangeModalCancel && rangeOptionsContainer) {
    byRangeButton.addEventListener("click", () => {
      const ranges = buildRanges(entryCount);

      if (!ranges.length) {
        closeSaveModal();
        window.showToast("No more records beyond the first 100.", "success");
        return;
      }

      function addRangeOption(label, onClick) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "save-option-btn";
        button.textContent = label;
        button.addEventListener("click", async () => {
          closeRangeModal();
          closeSaveModal();
          await onClick();
        });
        rangeOptionsContainer.appendChild(button);
      }

      rangeOptionsContainer.innerHTML = "";
      ranges.forEach(({ start, end }) => {
        addRangeOption(`${start}-${end}`, () => downloadPdf(downloadUrl, { scope: "range", start, end }));
      });
      // The oldest 100 records — the mirror image of "Last 100", anchored
      // to the other end of the table. Placed last so the grid reads as
      // a continuous countdown toward the very beginning of the ledger.
      addRangeOption("1-100", () => downloadPdf(downloadUrl, { scope: "first_100" }));

      rangeModal.classList.add("visible");
      lockBodyScroll();
    });

    rangeModalCancel.addEventListener("click", closeRangeModal);
    bindModalDismiss(rangeModal, closeRangeModal);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  // Independent of the selection-bar guard below (own null-checks), so it
  // still works if this ever runs on a page without the bulk-selection UI.
  initDateSearchFilter();

  const table = document.querySelector(".table-wrapper table");
  const selectAllCheckbox = document.querySelector("#select-all-rows");
  const bar = document.querySelector("#selection-bar");
  const mainContainer = document.querySelector("main.container");
  const countLabel = document.querySelector("#selection-count");
  const editButton = document.querySelector("#selection-edit");
  const groupButton = document.querySelector("#selection-group");
  const deleteButton = document.querySelector("#selection-delete");
  const downloadButton = document.querySelector("#selection-download");
  // Same combined guard the two features below always shared on the original
  // (single-callback) version of this file: in practice table/selection-bar/
  // save-modal/range-modal markup only ever ships together on home.html, so
  // this doubles as "bail out entirely if this isn't the home page".
  if (
    !table || !selectAllCheckbox || !bar || !countLabel || !editButton || !groupButton || !deleteButton ||
    !downloadButton
  ) return;

  const deleteUrl = bar.dataset.deleteUrl;
  const editUrlTemplate = bar.dataset.editUrlTemplate;
  const groupUrl = bar.dataset.groupUrl;
  const downloadUrl = bar.dataset.downloadUrl;

  initSelectionBar({
    table, selectAllCheckbox, bar, countLabel, editButton, groupButton, deleteButton, downloadButton,
    deleteUrl, editUrlTemplate, groupUrl, downloadUrl, mainContainer,
  });
  initSaveModal(bar, downloadUrl);
});
