function activateToast(item) {
  requestAnimationFrame(() => item.classList.add("show"));

  setTimeout(() => {
    item.classList.remove("show");
    item.addEventListener("transitionend", () => item.remove(), { once: true });
  }, 5000);
}

function showToast(text, tag) {
  let container = document.querySelector(".messages");
  if (!container) {
    container = document.createElement("ul");
    container.className = "messages";
    document.body.appendChild(container);
  }

  const item = document.createElement("li");
  item.className = `message ${tag}`;
  item.textContent = text;
  container.appendChild(item);

  activateToast(item);
}

window.showToast = showToast;

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".messages .message").forEach(activateToast);
});
