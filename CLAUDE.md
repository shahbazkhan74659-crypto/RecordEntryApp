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
- `templates/home.html` — the records table page. The header nav for logged-in users shows only Logout (no "Entries" link, removed intentionally). The table is wrapped in `.table-wrapper`, which deliberately breaks out ~60px past the normal container width on each side (not full viewport — that was tried and explicitly dialed back) for a wider look, collapsing to normal width under 768px.

## Branding

- Working name is still "Entry Recorder" in header/`<title>` text, but a **"LoadGate"** logo (`static/images/logo.png` — cropped and background-removed from a source PNG) is already in use on the login page. The app name is **not yet finalized**; if renaming to LoadGate is confirmed, update the header brand text, `<title>` blocks, `PROJECT.md`, and this file together so branding doesn't stay split between "Entry Recorder" (text) and "LoadGate" (logo).

## Before Adding Code

As the first real Django app/model is added, this file should be updated to include:
- The app layout (which Django app owns the truck-entry model/views) — likely a refactor out of the current project-level `views.py`
- Any non-obvious cross-file architecture (e.g. how the entry form maps to storage, how validation is shared)
- MySQL connection setup and where settings/env vars live, once that migration happens
