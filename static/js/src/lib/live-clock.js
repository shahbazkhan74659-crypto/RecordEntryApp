// Ticking HH:MM:SS clock, shown next to the admin greeting
// (templates/partials/admin_greeting.html). No-ops if #live-clock isn't on
// the page (e.g. the login page, which doesn't extend base.html and
// doesn't load messages.js at all -- this guard just keeps it robust
// regardless).
export function initLiveClock(elementId = "live-clock") {
  const el = document.getElementById(elementId);
  if (!el) return;

  function tick() {
    el.textContent = new Date().toLocaleTimeString("en-GB", { hour12: false });
  }

  tick();
  setInterval(tick, 1000);
}
