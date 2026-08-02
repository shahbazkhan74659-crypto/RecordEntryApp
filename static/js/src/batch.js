import { getCookie } from "./lib/cookies.js";
import { confirmDialog } from "./lib/confirm-dialog.js";
import { downloadPdf } from "./lib/download-pdf.js";
import { initDateSearchFilter } from "./lib/date-search-filter.js";

document.addEventListener("DOMContentLoaded", () => {
  // Independent of the .batch-grid guard below (own null-checks).
  initDateSearchFilter();

  const grid = document.querySelector(".batch-grid");
  if (!grid) return;

  function closeAllMenus() {
    grid.querySelectorAll(".batch-card-menu.open").forEach((menu) => {
      menu.classList.remove("open");
      menu.closest(".batch-card").querySelector(".batch-card-menu-btn").setAttribute("aria-expanded", "false");
    });
  }

  grid.addEventListener("click", async (event) => {
    const menuBtn = event.target.closest(".batch-card-menu-btn");
    if (menuBtn) {
      event.preventDefault();
      const menu = menuBtn.closest(".batch-card").querySelector(".batch-card-menu");
      const isOpen = menu.classList.contains("open");
      closeAllMenus();
      menu.classList.toggle("open", !isOpen);
      menuBtn.setAttribute("aria-expanded", String(!isOpen));
      return;
    }

    const saveBtn = event.target.closest(".batch-card-menu-save");
    if (saveBtn) {
      event.preventDefault();
      const card = saveBtn.closest(".batch-card");
      const { slug, downloadUrl } = card.dataset;
      closeAllMenus();

      await downloadPdf(downloadUrl, { scope: "batch", slug });
      return;
    }

    const deleteBtn = event.target.closest(".batch-card-menu-delete");
    if (deleteBtn) {
      event.preventDefault();
      const card = deleteBtn.closest(".batch-card");
      const { name, deleteUrl } = card.dataset;
      closeAllMenus();

      const confirmed = await confirmDialog(
        `Delete batch "${name}"? Its entries will stay but will no longer be grouped.`
      );
      if (!confirmed) return;

      const response = await fetch(deleteUrl, {
        method: "POST",
        headers: { "X-CSRFToken": getCookie("csrftoken") },
      });

      if (!response.ok) {
        window.alert("Could not delete the batch. Please try again.");
        return;
      }

      // Re-fetch the current (paginated) page rather than just removing the
      // card from the DOM: with pagination, deleting a card should pull the
      // next page's first card up into the vacated slot and update the
      // "Page X of Y" count — none of which a plain card.remove() can do,
      // since it has no idea what's on the next page. Paginator.get_page()
      // also naturally clamps back a page if this deletion emptied the
      // current (e.g. last) page, so re-fetching the same URL still lands
      // somewhere valid without any extra logic here.
      const refreshResponse = await fetch(window.location.href);
      const refreshedDoc = new DOMParser().parseFromString(await refreshResponse.text(), "text/html");
      const refreshedGrid = refreshedDoc.querySelector(".batch-grid");
      const refreshedPagination = refreshedDoc.querySelector(".pagination");
      const currentPagination = document.querySelector(".pagination");

      if (refreshedGrid) grid.innerHTML = refreshedGrid.innerHTML;
      if (currentPagination && refreshedPagination) {
        currentPagination.outerHTML = refreshedPagination.outerHTML;
      } else if (currentPagination && !refreshedPagination) {
        currentPagination.remove();
      } else if (!currentPagination && refreshedPagination) {
        grid.insertAdjacentElement("afterend", refreshedPagination);
      }

      window.showToast(`Deleted batch "${name}".`, "error");
    }
  });

  document.addEventListener("click", (event) => {
    if (!event.target.closest(".batch-card-menu-btn")) closeAllMenus();
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeAllMenus();
  });
});
