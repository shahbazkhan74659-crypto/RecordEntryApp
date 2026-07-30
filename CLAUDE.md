# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Status

This repository currently contains only planning material (`PROJECT.md`) — no code, tech stack, build tooling, or tests exist yet. There are no commands to build, lint, or run because there is nothing to build, lint, or run. Update this file with real commands as soon as a stack is chosen and scaffolding is added.

## What This Project Is

Entry Recorder is a web app (not a mobile app) for a **single user** to log **Truck Loading Records**. See `PROJECT.md` for the full definition, goals, and status checklist — read it before starting implementation work, since it holds context this file intentionally doesn't duplicate.

Key constraints to keep in mind when making architectural decisions:

- **Single user only** — no auth/multi-account/roles system should be introduced unless the client explicitly asks for it later.
- **Core entity is a truck loading entry**, currently defined by 5 fields (trucks loaded, packing, workers, rolls, net kg, remark) — these field definitions are placeholders and expected to change/expand, so the data model should be easy to extend rather than hard-coded around exactly five fields.
- Basic CRUD + list/filter/search over historical entries is the functional core; avoid building analytics/reporting beyond that unless requested.

## Before Adding Code

Once a stack is chosen, this file should be updated to include:
- Install/build/dev/test commands (and how to run a single test)
- The chosen data storage approach and where the schema/model lives
- Any non-obvious cross-file architecture (e.g., how the entry form maps to storage, how validation is shared between client/server)
