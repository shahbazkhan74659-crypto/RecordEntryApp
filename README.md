# Entry Recorder (LoadGate)

A single-user web app for logging **Truck Loading Records** — a digital replacement for a manual register used to record trucks being loaded across three physical plants. Live at **[entryrecorder.onrender.com](https://entryrecorder.onrender.com)**.

## What this is

Each entry represents one truck loading event. Loading (rolls, net weight, workers) is a single shared operation across the load, while each of the three plants — Plant 5, Plant 6, and Warp Plant — separately tracks its own packing/weighing stage before the rolls are combined and loaded.

Core features:

- **Entry table** — create, edit, and bulk-delete entries, with server-side date and vehicle-number search/filtering and pagination.
- **Batches** — group entries (many-to-many, an entry can belong to multiple batches at once) for organizing shipments/customers.
- **PDF export** — download all records, the last N, a custom numeric range, the oldest 100, or just the currently-selected rows, as a landscape-A4 PDF with per-plant column groups and running totals.
- **Single-user auth** — one account, gating both the app and Django admin; login lockout, rate-limited "Forgot Password" flow (email OTP), and self-service Account Settings (username/password/email, all OTP/cooldown-protected).
- **Mobile-responsive** — off-canvas navigation, touch-target-sized controls, and a mobile-safe modal/selection-bar layout.

## Current status

Deployed and live. Core CRUD, batching, PDF export, authentication (including Forgot Password and Account Settings), and a responsive layout are all built and in production. The codebase has been through a full review pass (refactor, code-quality, security, and mobile-responsiveness audits), with fixes threaded throughout rather than left open.

**Known open item:** transactional OTP emails (Forgot Password, Change Email) work locally and are configured for production, but `SENDGRID_API_KEY`/`DEFAULT_FROM_EMAIL` still need to be added to the live Render service's environment before they'll actually send there.

## Tech stack

| Layer | Choice |
|---|---|
| Backend | Python, Django |
| Database | PostgreSQL — Neon in production, local Postgres (or SQLite as a zero-setup fallback) in dev |
| Frontend | Django templates (server-rendered), vanilla JS bundled via esbuild, Zod for client-side validation |
| PDF generation | ReportLab (generation), pypdf (test-only, verifying exported PDFs) |
| Email | `django-anymail` over SendGrid's HTTP API (not raw SMTP — Render doesn't reliably support outbound raw TCP) |
| Hosting | Render (Gunicorn + WhiteNoise for static files) |

## Project structure

```
entryrecorder/    Django project settings, root URLs
recorder/         The app itself — Entry/Batch models, views, forms, migrations, tests
templates/        Django templates (pages + partials/modals)
static/js/src/    Source JS (bundled to static/js/dist/ via esbuild — gitignored build output)
build.sh          Render build step: pip install, npm build, collectstatic, migrate, superuser bootstrap
render.yaml       Render Blueprint (web service config)
Procfile          Gunicorn start command
```

## Getting started

**Prerequisites:** Python 3.11+, Node.js, PostgreSQL (optional — SQLite is the zero-setup dev fallback).

```bash
# Backend
python -m venv venv
venv\Scripts\activate            # Windows
pip install -r requirements.txt
cp .env.example .env               # fill in DATABASE_URL (optional), SendGrid keys, etc.
python manage.py migrate
python manage.py createsuperuser   # interactive — creates the single account
python manage.py runserver

# Frontend JS build (separate terminal)
npm install
npm run watch                      # or `npm run build` for a one-shot bundle
```

Visit `http://localhost:8000` and log in with the account you created.

### Seeding demo data

```bash
python manage.py seed_entries --count 100
```

### Testing

```bash
python manage.py test
```

## License

MIT — see [`LICENSE`](LICENSE).
