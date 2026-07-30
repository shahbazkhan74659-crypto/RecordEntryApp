# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Status

This repository currently contains only planning material (`PROJECT.md`, `CLAUDE.md`) — no Django project has been scaffolded yet, so there are no build/lint/test commands to run. Update this file with real commands (`manage.py runserver`, `manage.py test`, etc.) as soon as scaffolding is added.

## Tech Stack

- **Backend:** Python, Django
- **Database:** MySQL
- **Frontend:** Django templates (server-rendered), unless requirements change

## What This Project Is

Entry Recorder is a web app (not a mobile app) for a **single user** to log **Truck Loading Records**. See `PROJECT.md` for the full definition, goals, and status checklist — read it before starting implementation work, since it holds context this file intentionally doesn't duplicate.

Key constraints to keep in mind when making architectural decisions:

- **Single user only** — no auth/multi-account/roles system should be introduced unless the client explicitly asks for it later.
- **Core entity is a truck loading entry**, currently defined by 5 fields (trucks loaded, packing, workers, rolls, net kg, remark) — these field definitions are placeholders and expected to change/expand, so the data model should be easy to extend rather than hard-coded around exactly five fields.
- Basic CRUD + list/filter/search over historical entries is the functional core; avoid building analytics/reporting beyond that unless requested.

## Before Adding Code

Once the Django project is scaffolded, this file should be updated to include:
- Install/build/dev/test commands (e.g. `manage.py runserver`, `manage.py test <app>.<TestCase>.<test_method>` for a single test)
- MySQL connection setup and where settings/env vars live
- The app layout (which Django app owns the truck-entry model/views) and any non-obvious cross-file architecture
