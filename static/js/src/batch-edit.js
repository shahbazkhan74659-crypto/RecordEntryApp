document.addEventListener("DOMContentLoaded", () => {
  const openButton = document.querySelector("#open-add-modal");
  const modal = document.querySelector("#add-records-modal");
  const cancelButton = document.querySelector("#add-records-cancel");
  if (!openButton || !modal || !cancelButton) return;

  function close() {
    modal.classList.remove("visible");
  }

  openButton.addEventListener("click", () => modal.classList.add("visible"));
  cancelButton.addEventListener("click", close);

  modal.addEventListener("click", (event) => {
    if (event.target === modal) close();
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") close();
  });
});
