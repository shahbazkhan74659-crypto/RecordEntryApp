# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Status

Django project scaffolded (project name: `entryrecorder`). No dedicated Django **app** or data model exists yet — the `home` view and `urls.py` currently live directly in the `entryrecorder` project package (see `entryrecorder/views.py`). A login page, a home page with a (currently unbacked) records table, and the static/template plumbing are in place. Expect to refactor `views.py` into a proper app once the truck-entry model is added.

## Commands

- Activate venv: `source venv/Scripts/activate` (bash) or `.\venv\Scripts\Activate.ps1` (PowerShell)
- Run dev server: `python manage.py runserver`
- Run migrations: `python manage.py migrate`
- Run tests: `python manage.py test` (single test: `python manage.py test <app>.tests.<TestCase>.<test_method>`)
- Install deps: `pip install -r requirements.txt`; after adding a package, refresh with `pip freeze > requirements.txt`
- Frontend JS build (from repo root, needs Node.js): `npm install`, then `npm run build` (one-off bundle) or `npm run watch` (rebuild on save) — run this alongside `runserver` in a separate terminal while editing anything under `static/js/src/`. `npm run lint` runs ESLint.

## Tech Stack

- **Backend:** Python, Django
- **Database:** SQLite for now (Django's default, `db.sqlite3`, gitignored) — MySQL is planned later but not yet wired up; don't add MySQL connection config until asked
- **Frontend:** Django templates (server-rendered) for markup; a small Node/esbuild pipeline (`package.json`, `eslint.config.js`) bundles client-side JS from `static/js/src/*.js` to `static/js/dist/*.js` (gitignored build output — must run `npm run build` after cloning or pulling JS changes). Client-side form validation uses **Zod**, installed via npm (no CDN).

## What This Project Is

Entry Recorder is a web app (not a mobile app) for a **single user** to log **Truck Loading Records**. See `PROJECT.md` for the full definition, goals, and status checklist — read it before starting implementation work, since it holds context this file intentionally doesn't duplicate.

Key constraints to keep in mind when making architectural decisions:

- **Single user only** — no auth/multi-account/roles system should be introduced unless the client explicitly asks for it later.
- **Core entity is a truck loading entry** — the home page table currently renders these columns: S.No, Date, Vehicle Number, Rolls, Workers, Net Kg, Remark (superseding the original 5-field placeholder list in `PROJECT.md`; "Packing" was dropped and "Trucks Loaded" was replaced by per-row Vehicle Number/S.No/Date). No model backs this yet — the table loops over an `entries` context variable that nothing currently populates. Keep the eventual data model easy to extend rather than hard-coded around exactly these columns.
- Basic CRUD + list/filter/search over historical entries is the functional core; avoid building analytics/reporting beyond that unless requested.

## Auth

- **Decision:** single Django superuser account is used for both the custom app login and the `/admin` panel — no separate credential store, since there is only one real user of this app.
- Wired via Django's built-in `django.contrib.auth.views.LoginView`/`LogoutView` at `/login/` and `/logout/` (`entryrecorder/urls.py`). `home` view is `@login_required`. `LOGIN_URL`, `LOGIN_REDIRECT_URL`, `LOGOUT_REDIRECT_URL` are set in `settings.py`.
- **No superuser exists in the database yet.** Run `python manage.py createsuperuser` manually (interactively, so the password is actually yours) before login can work.

## Templates

- `templates/base.html` — shared layout (header with brand + nav, messages block, footer, a `scripts` block) used by `home.html` and any future authenticated pages.
- `templates/registration/login.html` — **deliberately does not extend `base.html`** (an explicit decision to fully decouple the login page from the shared layout). It's a standalone HTML document with its own `<head>`/`<body>`, pulling in only `style.css`, `login.js`, and the logo. `body.login-page` is locked to `height: 100vh; overflow: hidden` with flexbox centering, so the login page never scrolls and the logo+card stay vertically/horizontally centered regardless of viewport height.
- `templates/home.html` — the records table page. The header nav for logged-in users shows "Account Setting" (placeholder link, `href="#"` — no settings page exists yet) and Logout (no "Entries" link, removed intentionally). The table is wrapped in `.table-wrapper`, which deliberately breaks out ~60px past the normal container width on each side (not full viewport — that was tried and explicitly dialed back) for a wider look, collapsing to normal width under 768px. The header row itself (`.header-inner`) and a `.page-header` wrapper (containing the `<h1 class="page-title">` and the admin greeting) use the same breakout so header, heading, and table all share matching left/right edges.
- `.page-header` is a flex row (`justify-content: space-between`) holding `<h1 class="page-title">Truck Loading Entries</h1>` and `<p class="admin-greeting">Administrator Dashboard | Welcome, {{ user.get_username }}</p>` — the greeting is dynamic (pulls the logged-in superuser's username), not hardcoded text.
- **`.header-inner` centering gotcha:** it carries both `.container` (`margin: 0 auto`) and its own rules. Giving it a fixed `margin-left`/`margin-right` to break out (like `.table-wrapper` does) conflicts with the inherited `margin: 0 auto` — the explicit longhand wins and the box loses centering instead of widening symmetrically (this shipped broken once: logo clipped off-screen left, Logout centered mid-page). The working fix is overriding `max-width` (currently `1040px`) instead, which coexists with the inherited auto-centering. If any element needs a breakout margin *and* already relies on `.container`'s auto-centering, use the `max-width` approach, not `margin-left`/`margin-right`.
- **`.site-nav a` specificity gotcha:** `.site-nav a` / `.site-nav a:hover` (class+type selector) are more specific than a lone `.btn-outline` class and will silently override its color/hover styles for any `<a>` placed inside `.site-nav` (this happened to the "Account Setting" button — text rendered muted-gray instead of black, blue on hover instead of white). Any future nav link that needs its own colors must use a type+class selector (`a.btn-outline`) to win the specificity tie via source order, or otherwise out-specificity `.site-nav a`.
- Header buttons: `.btn-outline` (Account Setting) is a white/dark-bordered pill that inverts to solid black/white text on hover; `.link-button` (Logout) is a light-red pill with bold black text. Both share the same padding and a 2px border (transparent on `.link-button`) so their rendered heights match exactly — dropping the border from one without compensating breaks height parity.

## Branding

- Working name is still "Entry Recorder" in header/`<title>` text, but a **"LoadGate"** logo (`static/images/logo.png` — cropped and background-removed from a source PNG) is already in use on the login page. The app name is **not yet finalized**; if renaming to LoadGate is confirmed, update the header brand text, `<title>` blocks, `PROJECT.md`, and this file together so branding doesn't stay split between "Entry Recorder" (text) and "LoadGate" (logo).
- `static/images/LOGO2.png` is a second, separate truck-themed logo now used in the main app header (`base.html`'s `.brand`, via `.brand-logo`, 44px tall) — placed before the "Entry Recorder" text on every authenticated page. It has an opaque near-white background rather than transparency, which blends acceptably against the header's white background but would need proper background removal if the header background ever changes.
- **Favicon:** `static/favicon/` holds a full favicon.io-generated set (`favicon.ico`, `favicon-16x16.png`, `favicon-32x32.png`, `apple-touch-icon.png`, `android-chrome-192x192.png`, `android-chrome-512x512.png`, `site.webmanifest`), wired into the `<head>` of both `base.html` and `login.html` via `{% static %}` tags. `site.webmanifest`'s `name`/`short_name` were filled in as "Entry Recorder" (were blank in the downloaded package), and its icon `src` paths were changed to relative (no leading `/`) so they resolve correctly under `/static/favicon/` regardless of `STATIC_URL`.
- The favicon set is **not** generated from the raw `LOGO2.png`/`logo.png` artwork directly — the full artwork (truck + arrow swoosh + gate outline, multiple thin lines and colors) is illegible at 16–32px. The favicon images were produced from a background-removed, tightly-cropped version isolating just the truck silhouette (arrows/gate discarded). If the source logo is ever replaced, redo this crop-for-legibility step rather than piping the new artwork straight through a resize.

## Before Adding Code

As the first real Django app/model is added, this file should be updated to include:
- The app layout (which Django app owns the truck-entry model/views) — likely a refactor out of the current project-level `views.py`
- Any non-obvious cross-file architecture (e.g. how the entry form maps to storage, how validation is shared)
- MySQL connection setup and where settings/env vars live, once that migration happens
