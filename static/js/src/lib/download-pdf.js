import { getCookie } from "./cookies.js";

// Shared by home.js (scope="all"/"last_10"/"last_50"/"last_100"/"choose")
// and batch.js (scope="batch"). Fetches the PDF as a blob rather than
// navigating to the URL directly, so the same X-CSRFToken header/POST-body
// pattern already used for delete/group can carry `params` without a page
// reload. The filename comes from the server's Content-Disposition header,
// since a blob: URL has no filename of its own for the browser to fall back on.
export async function downloadPdf(downloadUrl, params) {
  const body = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (Array.isArray(value)) {
      value.forEach((item) => body.append(key, item));
    } else {
      body.append(key, value);
    }
  });

  const response = await fetch(downloadUrl, {
    method: "POST",
    headers: { "X-CSRFToken": getCookie("csrftoken") },
    body,
  });

  if (!response.ok) {
    const data = await response.json().catch(() => null);
    window.alert(data?.error || "Could not generate the PDF. Please try again.");
    return false;
  }

  const blob = await response.blob();
  const disposition = response.headers.get("Content-Disposition") || "";
  const match = disposition.match(/filename="?([^"]+)"?/);
  const filename = match ? match[1] : "truck-entries.pdf";

  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
  return true;
}
