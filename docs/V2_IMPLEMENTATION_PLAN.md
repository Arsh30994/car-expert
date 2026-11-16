# Car Expert AI V2 — Vehicle-Centric Competition Release

**Product:** Car Expert AI — Your Personal Automotive Intelligence System.

**Promise:** Understand your car. Investigate problems. Know what needs attention next.

## Locked V2 decisions

- **Frontend:** Django templates, HTML, CSS and vanilla JavaScript.
- **Backend:** Existing Django application and PostgreSQL/SQLite configuration.
- **Core domain:** A permanent, owner-scoped multi-vehicle garage.
- **AI approach:** Evidence-grounded orchestration. The LLM proposes observations and possible causes; deterministic validation, persisted evidence and explicit uncertainty govern the report.
- **Scope:** Focused competition release. Deliver one polished diagnostic journey end-to-end before adding optional features.

The earlier car-shopping/marketplace direction is not part of this V2 competition release. Its code was removed from the active development branch to keep the product focused. It can be reconsidered after this release.

## Existing repository assets to preserve

- Django authentication and registration.
- Existing chat sessions, message history, rename/delete flows and AJAX chat.
- Existing AI/ML API provider integration and image upload validation.
- Existing `garage.Vehicle`, `GarageSelection`, owner-scoped CRUD APIs and selected-vehicle context.
- Existing per-session `chatbot.VehicleProfile` as a backward-compatible fallback for legacy sessions.
- Existing production database, Vercel, static-file and environment configuration.

## Target domain model

```text
User
 └── Vehicle (permanent owner-scoped garage record)
      ├── ChatSession
      │    └── Message / uploaded evidence
      ├── DiagnosticReport (structured JSON + urgency + evidence)
      ├── ServiceRecord
      ├── MaintenanceTask
      ├── UploadedDocument (later milestone)
      ├── OBDSession (simulated first; later milestone)
      ├── FuelLog (later milestone)
      └── ExpenseRecord (later milestone)
```

A chat session has an optional FK to the permanent Vehicle. New sessions inherit the selected garage vehicle. The selected vehicle is used as a context default for legacy sessions, but an established session retains its own vehicle association. Every vehicle lookup and write must be owner-scoped.

## Diagnostic integrity contract

A report contains:
- Summary.
- Observations with source, evidence and categorical confidence.
- Possible causes with likelihood plus supporting and contradicting evidence.
- Urgency: unknown, low, medium, high or critical.
- Safety warnings and recommended actions.
- Follow-up questions and data gaps.

Never persist an arbitrary model-generated health score. A photograph is evidence of visible conditions, not proof of internal mechanical failure. Distinguish observations from hypotheses. Safety-critical warnings must be deterministic and prominent. Missing evidence remains a data gap, not an invitation to invent a fact.

## Competition release milestones

### M1 — Platform foundation + dashboard shell
- Extend permanent Vehicle identity with nickname and registration number while preserving existing API compatibility.
- Persist current odometer semantics (existing `mileage_km` remains the compatibility field).
- Add vehicle-linked service records and maintenance tasks.
- Associate chat sessions with a permanent vehicle.
- Add a premium dashboard shell and navigation.
- Add structured DiagnosticReport persistence and strict schema validation.
- Regression-test existing chat, garage CRUD, selection, authentication and uploads.
**Exit:** migrations and all regression tests pass; user can manage multiple vehicles and see a vehicle-centric dashboard.

### M2 — Diagnostic engine
- Normalize AI output to the strict diagnostic contract.
- Build an orchestrator combining vehicle profile, symptoms, uploaded image observations, OBD codes and service history.
- Ask targeted follow-up questions when critical information is missing.
- Save each report independently and link it to its vehicle and originating chat.
- Render evidence, uncertainty, urgency, possible causes and safe next steps.
**Exit:** tests cover malformed model output, missing evidence, conflicting evidence, provider failures and safety-critical cases.

### M3 — Premium cockpit dashboard
- Overview, Garage, Diagnostics, Maintenance and Knowledge sections.
- Vehicle timeline and report history.
- Transparent health indicators derived only from known records/rules; never a fabricated arbitrary score.
- Responsive layout, accessible controls, reduced-motion support and polished scan/report states.
**Exit:** complete responsive vehicle overview with loading, empty and failure states.

### M4 — Knowledge and maintenance
- PDF/manual upload and text extraction.
- Chunking and retrieval with citations to document title and page.
- Maintenance rules based on odometer, age, service history and cited manufacturer schedule.
- Tasks can be acknowledged/completed and persist to vehicle timeline.
**Exit:** document-grounded answers cite retrievable source locations; schedule logic is unit tested.

### M5 — Competition demo hardening
- Simulated OBD-II session with explicit SIMULATED labeling.
- Seeded demo account/vehicle and a rehearsed warning-light diagnostic scenario.
- Demo: select vehicle → upload dashboard image → ask symptoms → enter simulated P0128 → combine evidence → save report → create inspection task → show vehicle timeline.
- Test slow network, invalid uploads, AI failure, empty garage, cross-owner access and missing data.
- Architecture README, setup/deployment instructions and 90-second demo script.
**Exit:** complete demo can be repeated reliably; tests and deployment smoke checks pass.

## Explicitly deferred

- Real OBD-II hardware integration.
- Voice assistant.
- 3D vehicle viewer and customization.
- Custom-trained model and microservices.
- Repair booking, parts marketplace and car shopping.
- Any claim of universal diagnosis from an image.

## Testing and release gates

- Unit: schema validation, report normalization, maintenance due calculations and safety rules.
- Integration: owner permissions, session-to-vehicle binding, report persistence, upload association and dashboard aggregation.
- Regression: existing authentication, chat, image upload, garage CRUD, selection and provider error behavior.
- Release commands: `python manage.py makemigrations --check --dry-run`, `python manage.py migrate --noinput`, `python manage.py test chatbot garage diagnostics`, `python manage.py check`.


A code commit is not a passing test. Milestones remain in progress until GitHub Actions reports a completed successful run and the deployment smoke test is performed.

## Current implementation status

- [x] Vehicle-centric scope locked; shopping marketplace removed from active V2 branch.
- [x] Existing permanent garage extended with nickname and registration number; existing `mileage_km` remains the compatibility odometer field.
- [x] Added vehicle-linked `ServiceRecord` and `MaintenanceTask` persistence.
- [x] Added permanent vehicle FK to chat sessions while retaining legacy `VehicleProfile`.
- [x] Added structured diagnostic report schema, validator, persistence model and owner-checking service.
- [x] Added authenticated vehicle cockpit dashboard and responsive navigation.
- [x] Added tests for garage records, report schema/ownership, dashboard and chat vehicle binding.
- [x] GitHub Actions completed migrations, regression tests and Django checks successfully on commit `be6757f0658eefaea049cdd33e430c27cf0910e9`.
- [ ] Re-run CI after the final active-session vehicle-binding change and README update.
- [ ] Browser smoke test on a branch preview/staging environment.
- [ ] Complete diagnostic orchestration, report generation from chat evidence and vehicle timeline UI (M2).

**Privacy:** VIN and registration identifiers are deliberately excluded from the text sent to the AI provider. The current `mileage_km` field is retained for compatibility and exposed as `current_odometer_km` in Python.
