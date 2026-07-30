# Entry Recorder

## Project Definition

Entry Recorder is a web-based (not mobile app) record-keeping system built for a **single user**. It is designed to log and track **Truck Loading Records** — a digital replacement for a manual register/logbook currently used to record details of trucks being loaded.

Each entry in the system represents one truck loading event and captures core details about that load. The initial five core fields identified are:

1. **Number of Trucks Loaded** — count/reference for the truck loading event
2. **Packing** — number/type of packing units for the load
3. **Number of Workers** — workers involved in loading that truck
4. **Number of Rolls** — count of rolls loaded
5. **Net Kg** — net weight (in kilograms) of the load
6. **Remark** — free-text notes/observations for that entry

> Note: Field definitions above are placeholders. Exact meaning, data type, and validation rules for each field will be finalized in a follow-up requirements pass, and additional fields may be added later based on client requests.

## Goals

- Provide a simple, reliable web interface for a single user to **create, view, edit, and delete** truck loading entries.
- Replace manual/paper-based tracking of truck loading data with a structured digital record.
- Ensure data is stored persistently and can be **searched/filtered** (e.g., by date, truck, remarks).
- Allow **easy review of historical entries** (daily/weekly/monthly summaries) for record-keeping and reporting purposes.
- Keep the system **lightweight and single-user focused** — no multi-user accounts, roles, or permissions needed initially.
- Design the data model to be **extensible**, so new fields can be added later without major rework, as per client requests.

## Tech Stack

See `TECH_STACK.txt`.

## Out of Scope (for now)

- Multi-user support / authentication for multiple accounts
- Native mobile app (Android/iOS)
- Complex analytics/reporting beyond basic listing and filtering

## Status

- [ ] Finalize definitions for all 5 (or more) fields — including data type, required/optional, validation rules
- [ ] Confirm any additional fields requested by the client
- [x] Define tech stack — Python/Django + MySQL (SQLite for now during development)
- [x] Scaffold Django project (`entryrecorder`) with virtual environment
- [ ] Design data model / database schema
- [ ] Build UI (entry form + records list/table view)
- [ ] Build backend (CRUD operations)
- [ ] Testing
- [ ] Deployment
