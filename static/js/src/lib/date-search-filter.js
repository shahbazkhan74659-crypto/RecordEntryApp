// Server-side date/vehicle-number filtering for a paginated entries table
// (see recorder/views.py:home), and/or plain search-only filtering for
// other paginated lists (e.g. batch name search on recorder/views.py:batch)
// — navigates with the right query params instead of filtering rows
// client-side, since only a page's worth of rows is ever in the DOM at
// once (client-side filtering would only ever search the current page).
// Self-contained (its own querySelector lookups) so it can be wired up
// independently of whatever else a page does, and tolerates either half
// being absent: home.html has both the date filter and search bar
// (templates/partials/search_bar.html); batch.html has only the search bar.
export function initDateSearchFilter() {
  const dateFilterInput = document.querySelector("#date-filter-input");
  const dateFilterBtn = document.querySelector("#date-filter-btn");
  const dateFilterClear = document.querySelector("#date-filter-clear");
  const searchInput = document.querySelector("#entry-search-input");
  const searchBtn = document.querySelector("#entry-search-btn");

  const hasDateFilter = !!(dateFilterInput && dateFilterBtn && dateFilterClear);
  const hasSearch = !!(searchInput && searchBtn);
  if (!hasDateFilter && !hasSearch) return;

  function currentParams() {
    return new URLSearchParams(window.location.search);
  }

  function applyFilters(date, search) {
    const params = new URLSearchParams();
    if (date) params.set("date", date);
    if (search) params.set("q", search);

    // "return_page" remembers which page you were on *before* a filter was
    // ever applied, so "All" can snap back there regardless of how much you
    // paginated within the filtered results — captured once (here) the
    // moment you go from unfiltered to filtered, then carried forward
    // unchanged through every later filter tweak and pagination click for
    // the rest of that filtered session, until "All" consumes and drops it.
    // Only meaningful where a "clear filter" control (dateFilterClear)
    // exists to actually consume it — plain search-only pages like batch
    // have no such control, so there's nothing to thread this through for.
    if (hasDateFilter) {
      const existing = currentParams();
      const wasAlreadyFiltered = !!(existing.get("date") || existing.get("q"));
      const returnPage = wasAlreadyFiltered
        ? existing.get("return_page") || "1"
        : existing.get("page") || "1";
      // Always set explicitly, even "1" — if this were only set for values
      // other than "1", clearFilters()'s fallback below would have no way
      // to tell "started from page 1" apart from "started from wherever
      // you'd since paginated to within the filtered results", and would
      // wrongly grab the latter off the URL's plain page= param instead.
      params.set("return_page", returnPage);
    }

    // page is deliberately omitted -> defaults to page 1 of the new/changed
    // filtered results.
    window.location.href = params.toString() ? `?${params.toString()}` : window.location.pathname;
  }

  function clearFilters() {
    const existing = currentParams();
    const targetPage = existing.get("return_page") || "1";
    window.location.href = targetPage !== "1" ? `?page=${targetPage}` : window.location.pathname;
  }

  if (hasDateFilter) {
    dateFilterBtn.addEventListener("click", () => {
      if (typeof dateFilterInput.showPicker === "function") {
        dateFilterInput.showPicker();
      } else {
        dateFilterInput.focus();
      }
    });

    dateFilterInput.addEventListener("change", () => {
      applyFilters(dateFilterInput.value, searchInput ? searchInput.value.trim() : "");
    });

    dateFilterClear.addEventListener("click", clearFilters);
  }

  if (hasSearch) {
    function submitSearch() {
      applyFilters(hasDateFilter ? dateFilterInput.value : "", searchInput.value.trim());
    }

    searchBtn.addEventListener("click", submitSearch);
    searchInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter") submitSearch();
    });

    // Starts readonly (see partials/search_bar.html) so Chrome's autofill
    // never evaluates it at page-load time — that's when it decides to
    // offer the saved "Addresses and more" suggestion, and
    // autocomplete="off" alone doesn't reliably stop it. Dropped on the
    // earliest real interaction event (before "focus") so the field is
    // already editable by the time focus actually lands.
    function enableSearchInput() {
      searchInput.removeAttribute("readonly");
    }
    searchInput.addEventListener("mousedown", enableSearchInput, { once: true });
    searchInput.addEventListener("touchstart", enableSearchInput, { once: true });
    searchInput.addEventListener("focus", enableSearchInput, { once: true });
  }
}
