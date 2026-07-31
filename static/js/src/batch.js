import { getCookie } from "./lib/cookies.js";
import { confirmDialog } from "./lib/confirm-dialog.js";

document.addEventListener("DOMContentLoaded", () => {
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

      card.remove();
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
