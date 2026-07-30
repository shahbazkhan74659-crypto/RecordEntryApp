# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Status

Django project scaffolded (project name: `entryrecorder`). No apps or models exist yet — just the default project skeleton.

## Commands

- Activate venv: `source venv/Scripts/activate` (bash) or `.\venv\Scripts\Activate.ps1` (PowerShell)
- Run dev server: `python manage.py runserver`
- Run migrations: `python manage.py migrate`
- Run tests: `python manage.py test` (single test: `python manage.py test <app>.tests.<TestCase>.<test_method>`)
- Install deps: `pip install -r requirements.txt`; after adding a package, refresh with `pip freeze > requirements.txt`

## Tech Stack

- **Backend:** Python, Django
- **Database:** SQLite for now (Django's default, `db.sqlite3`, gitignored) — MySQL is planned later but not yet wired up; don't add MySQL connection config until asked
- **Frontend:** Django templates (server-rendered), unless requirements change

## What This Project Is

Entry Recorder is a web app (not a mobile app) for a **single user** to log **Truck Loading Records**. See `PROJECT.md` for the full definition, goals, and status checklist — read it before starting implementation work, since it holds context this file intentionally doesn't duplicate.

Key constraints to keep in mind when making architectural decisions:

- **Single user only** — no auth/multi-account/roles system should be introduced unless the client explicitly asks for it later.
- **Core entity is a truck loading entry**, currently defined by 5 fields (trucks loaded, packing, workers, rolls, net kg, remark) — these field definitions are placeholders and expected to change/expand, so the data model should be easy to extend rather than hard-coded around exactly five fields.
- Basic CRUD + list/filter/search over historical entries is the functional core; avoid building analytics/reporting beyond that unless requested.

## Before Adding Code

As the first app/model is added, this file should be updated to include:
- The app layout (which Django app owns the truck-entry model/views)
- Any non-obvious cross-file architecture (e.g. how the entry form maps to storage, how validation is shared)
- MySQL connection setup and where settings/env vars live, once that migration happens
