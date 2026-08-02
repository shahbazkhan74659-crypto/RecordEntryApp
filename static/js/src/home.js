import { getCookie } from "./lib/cookies.js";
import { confirmDialog } from "./lib/confirm-dialog.js";
import { promptDialog } from "./lib/prompt-dialog.js";
import { bindModalDismiss, lockBodyScroll, unlockBodyScroll } from "./lib/modal-dismiss.js";
import { downloadPdf } from "./lib/download-pdf.js";

document.addEventListener("DOMContentLoaded", () => {
  const table = document.querySelector(".table-wrapper table");
  const selectAllCheckbox = document.querySelector("#select-all-rows");
  const bar = document.querySelector("#selection-bar");
  const countLabel = document.querySelector("#selection-count");
  const editButton = document.querySelector("#selection-edit");
  const groupButton = document.querySelector("#selection-group");
  const deleteButton = document.querySelector("#selection-delete");
  const downloadButton = document.querySelector("#selection-download");
  if (
    !table || !selectAllCheckbox || !bar || !countLabel || !editButton || !groupButton || !deleteButton ||
    !downloadButton
  ) return;

  const deleteUrl = bar.dataset.deleteUrl;
  const editUrlTemplate = bar.dataset.editUrlTemplate;
  const groupUrl = bar.dataset.groupUrl;
  const downloadUrl = bar.dataset.downloadUrl;

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

  downloadButton.addEventListener("click", async () => {
    const checked = selectedCheckboxes();
    if (checked.length === 0) return;

    const succeeded = await downloadPdf(downloadUrl, {
      scope: "choose",
      ids: checked.map((checkbox) => checkbox.value),
    });
    if (!succeeded) return;

    checked.forEach((checkbox) => {
      checkbox.checked = false;
      checkbox.closest("tr").classList.remove("selected");
    });
    updateBar();
  });

  const saveButton = document.querySelector("#save-pdf-btn");
  const saveModal = document.querySelector("#save-modal");
  const saveModalCancel = document.querySelector("#save-modal-cancel");
  const saveOptionButtons = saveModal ? [...saveModal.querySelectorAll(".save-option-btn")] : [];

  if (saveButton && saveModal && saveModalCancel && saveOptionButtons.length) {
    function closeSaveModal() {
      saveModal.classList.remove("visible");
      unlockBodyScroll();
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
  }

  const dateFilterInput = document.querySelector("#date-filter-input");
  const dateFilterBtn = document.querySelector("#date-filter-btn");
  const dateFilterClear = document.querySelector("#date-filter-clear");
  const searchInput = document.querySelector("#entry-search-input");

  if (dateFilterInput && dateFilterBtn && dateFilterClear) {
    const tbody = table.querySelector("tbody");
    let noResultsRow = null;

    function toggleNoResultsRow(show) {
      if (show) {
        if (!noResultsRow) {
          noResultsRow = document.createElement("tr");
          const cell = document.createElement("td");
          cell.colSpan = table.querySelectorAll("thead th").length;
          cell.textContent = "No matching entries.";
          noResultsRow.appendChild(cell);
          tbody.appendChild(noResultsRow);
        }
        noResultsRow.style.display = "";
      } else if (noResultsRow) {
        noResultsRow.style.display = "none";
      }
    }

    function applyFilters() {
      const dateValue = dateFilterInput.value;
      const searchValue = searchInput ? searchInput.value.trim().toLowerCase() : "";
      const rows = [...tbody.querySelectorAll("tr[data-date]")];
      let visibleCount = 0;

      rows.forEach((row) => {
        const matchesDate = !dateValue || row.dataset.date === dateValue;
        const matchesSearch = !searchValue || row.dataset.vehicle.includes(searchValue);
        const matches = matchesDate && matchesSearch;
        row.style.display = matches ? "" : "none";
        if (matches) visibleCount += 1;
      });

      dateFilterBtn.classList.toggle("active", !!dateValue);
      dateFilterClear.hidden = !dateValue && !searchValue;
      toggleNoResultsRow(rows.length > 0 && visibleCount === 0);
    }

    dateFilterBtn.addEventListener("click", () => {
      if (typeof dateFilterInput.showPicker === "function") {
        dateFilterInput.showPicker();
      } else {
        dateFilterInput.focus();
      }
    });

    dateFilterInput.addEventListener("change", applyFilters);
    dateFilterClear.addEventListener("click", () => {
      dateFilterInput.value = "";
      if (searchInput) searchInput.value = "";
      applyFilters();
    });

    const searchBtn = document.querySelector("#entry-search-btn");

    if (searchInput && searchBtn) {
      searchBtn.addEventListener("click", applyFilters);
      searchInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter") applyFilters();
      });

      // Starts readonly (see home.html) so Chrome's autofill never evaluates
      // it at page-load time — that's when it decides to offer the saved
      // "Addresses and more" suggestion, and autocomplete="off" alone doesn't
      // reliably stop it. Dropped on the earliest real interaction event
      // (before "focus") so the field is already editable by the time focus
      // actually lands.
      function enableSearchInput() {
        searchInput.removeAttribute("readonly");
      }
      searchInput.addEventListener("mousedown", enableSearchInput, { once: true });
      searchInput.addEventListener("touchstart", enableSearchInput, { once: true });
      searchInput.addEventListener("focus", enableSearchInput, { once: true });
    }
  }
});
