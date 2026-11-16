# Car Expert AI V2 — Repository Implementation Plan

**Locked product decisions:** Django-rendered frontend; curated vehicle catalogue; complete platform delivered in independently tested milestones.

## 1. Repository baseline and preservation rules

The existing repository is a Django application with Django templates, static JavaScript/CSS, Django authentication, PostgreSQL in production and SQLite locally. It already has:
- Chat sessions, message history, image attachment handling and the AI/ML API client.
- An owner-scoped garage (`garage.Vehicle`) and account-wide `GarageSelection`.
- Chat context that prefers the selected garage vehicle and falls back to the legacy per-session `chatbot.VehicleProfile`.
- Existing auth, chat, garage and deployment tests.

**Preserve:** current URL names, auth flows, chat session behavior, upload validation, AI provider configuration, garage ownership boundaries, selected-vehicle context, static asset paths and Vercel/PostgreSQL settings. Do not replace the chat app or rewrite the UI in React. Keep `VehicleProfile` as a backwards-compatible legacy chat context; it is not the shopping catalogue or permanent garage.

## 2. Target architecture

- **Presentation:** Django templates, accessible HTML, existing CSS and vanilla JavaScript enhancements. No SPA build chain.
- **Application:** Django apps separated by domain: `marketplace` (catalogue, discovery, recommendations, comparisons, finance, shortlist, test-drive requests), `garage` (owned vehicles), `chatbot` (AI advisor and diagnostic chat), and later `ownership` (maintenance, expenses, resale).
- **Persistence:** PostgreSQL in production; SQLite-compatible migrations and tests locally.
- **Catalogue:** curated `CarVariant` records plus city-specific `CityPrice` records and provenance. Every mutable market datum carries source, source URL, verification date and effective date. Missing values stay unknown; no fabricated specifications, ratings or live dealer availability.
- **Business logic:** deterministic Python services calculate recommendation ranking, comparisons, EMI and total cost of ownership. The LLM explains and answers using retrieved catalogue/estimator context; it does not invent data or decide numeric scores.
- **Security:** authenticated owner-scoped shortlist and test-drive requests; CSRF-protected Django forms; server-side validation; public catalogue read-only; admin-only catalogue editing.
- **Delivery:** branch-based development, migrations, focused tests per milestone, full Django suite and deployment smoke tests before merge.

## 3. Milestones and acceptance criteria

### M0 — Architecture and regression baseline
- Lock Django/curated/complete decisions.
- Inventory routes, models, settings, deployment and existing tests.
- Create isolated `v2-development` branch.
- Document compatibility and release gates.
**Exit:** baseline reviewed; main branch unchanged.

### M1 — Marketplace domain foundation (in progress)
- Add isolated marketplace Django app and domain services.
- Implement deterministic recommendation filtering/ranking with visible score dimensions, reasons and trade-offs.
- Implement reducing-balance EMI calculator with validation and zero-interest handling.
- Add unit tests for hard filters, stable ordering, no-match behavior, score explanation and finance edge cases.
**Exit:** app registered, migrations clean, focused tests and full suite green. No unverified vehicle seed data.

### M2 — Curated catalogue and Smart Car Finder
- Add `CarVariant`, `CityPrice` and source/provenance metadata.
- Admin curation workflow and import/validation command.
- Discovery filters: budget, city, fuel, seats, mileage, safety, ground clearance and boot space.
- Catalogue cards clearly distinguish ex-showroom, on-road and estimates; show last verified date and source.
**Exit:** seeded catalogue contains only source-verified records; filter and detail tests pass.

### M3 — Recommendations and visual comparison
- Persist user buying preferences and recommendation snapshots.
- Explain rank components and trade-offs; support 2–3 car comparison.
- Use accessible HTML/CSS comparison bars and tables, with no chart-only information.
**Exit:** same inputs produce deterministic results; comparison values are traceable to catalogue records.

### M4 — Ownership cost and EMI planner
- EMI, down payment, fuel, insurance, maintenance and depreciation/resale assumptions.
- Five-year total-cost estimate with transparent assumptions and uncertainty ranges.
- Prevent double counting: include purchase principal plus financing interest, or total loan repayments, never both.
**Exit:** finance calculator edge cases and total-cost accounting tests pass.

### M5 — AI buying advisor and shortlist
- Context-aware buying assistant consumes saved preferences, catalogue retrieval, comparison and calculator outputs.
- Save/remove shortlist; enforce user ownership.
- Ground AI responses in retrieved data and show when catalogue data is missing or stale.
**Exit:** integration tests prove model context uses actual catalogue/calculator results; provider failure is graceful.

### M6 — Test-drive requests
- User-submitted request with city, preferred dealer (if curated), date/time window and contact consent.
- Explicit pending/requested state; no claim of confirmed booking absent dealer integration.
- Admin workflow for request status.
**Exit:** authorization, validation and state-transition tests pass.

### M7 — Ownership experience
- Maintenance plans and reminders based on vehicle age/odometer and manufacturer schedule source.
- Expense log, service history, resale estimate with transparent limitations.
- Integrate existing garage vehicle as canonical owned asset; keep shopping shortlist separate.
**Exit:** owner-scoped CRUD and schedule calculation tests pass.

### M8 — Delhi launch data, polish and judge readiness
- City configuration for Delhi NCR: on-road price components, fuel assumptions, charging/refuelling notes and applicable regulatory links with effective dates.
- Responsive visual system, reduced-motion support, keyboard accessibility, loading/empty/error states and purposeful animations.
- Demo dataset provenance, seed instructions, architecture diagram, screenshots, test commands and deployment runbook.
**Exit:** complete user journey demoed from discovery to shortlist, comparison, ownership estimate, AI explanation and test-drive request; full test suite and production smoke checks green.

## 4. Data quality policy

Each catalogue fact is stored with source and verification metadata. Price is variant + city + effective date specific. A source URL is not proof that every field on a row is supported: record field-level sources where possible. Safety ratings must identify the rating agency and test protocol. Claimed mileage must identify test/claimed basis and unit. Estimates are visibly labelled. If a value cannot be verified, render “Not available” rather than infer it.

Initial catalogue data will not be fabricated to make the UI look populated. A curated import is a separate acceptance gate before public launch.

## 5. Test strategy

- Unit: recommendation scoring/filtering, EMI and total-cost arithmetic, date/odometer maintenance scheduling.
- Integration: Django views/forms, catalogue query filters, ownership permissions, shortlist and request persistence, AI context assembly.
- Regression: existing authentication, chat, image upload, garage selection, selected vehicle context, static assets and Vercel checks.
- Release: `python manage.py check`, `python manage.py makemigrations --check --dry-run`, `python manage.py test`, then browser smoke tests against a staging deployment.

## 6. Current implementation status

- [x] Decisions locked: Django frontend, curated data, complete phased scope.
- [x] Inspected existing Django, garage, chatbot, settings, URLs, templates and tests.
- [x] Created isolated `v2-development` branch from the reviewed main commit.
- [x] Added first marketplace service tests and deterministic recommendation/EMI service implementation.
- [ ] Register app and complete the first milestone integration.
- [ ] Execute focused and full test suites in a runnable repository environment.
- [ ] Implement catalogue models and first user-facing discovery workflow.

**Important execution note:** GitHub repository editing is available in this session, but a local Python/Django runtime is not attached to the repository connector. A commit is not evidence that tests ran. Use the repository GitHub Actions workflow or a local clone to execute the documented commands and report actual results before calling a milestone complete.
