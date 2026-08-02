import { getCookie } from "./cookies.js";

// Shared by account-settings.js and login.js (forgot-password flow): POSTs a
// plain URL-encoded form body with the CSRF header, and normalizes the
// response into { ok, data } so callers don't each repeat the same
// fetch/json-parse boilerplate.
export async function postForm(url, fields) {
  const body = new URLSearchParams();
  Object.entries(fields).forEach(([key, value]) => body.append(key, value));

  let response;
  try {
    response = await fetch(url, {
      method: "POST",
      headers: { "X-CSRFToken": getCookie("csrftoken") },
      body,
    });
  } catch {
    // fetch() itself rejected (offline, DNS failure, etc.) rather than
    // resolving with an HTTP error response — normalized into the same
    // { ok, data } shape callers already handle instead of an unhandled
    // promise rejection.
    return { ok: false, data: { error: "Network error. Please check your connection and try again." } };
  }

  const data = await response.json().catch(() => ({}));
  return { ok: response.ok, data };
}
