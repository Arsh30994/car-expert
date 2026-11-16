# Car Expert AI — Test Plan and Test Subjects

> Status convention: **Automated now** means a test exists in this branch. **Manual now** means the current feature can be exercised manually. **Planned** means the feature is not implemented yet; these are acceptance tests, not passing tests.

## 1. Run the automated suite

```bash
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py test chatbot garage
python manage.py check
```

Run one test class while debugging:

```bash
python manage.py test garage.tests.VehicleGarageApiTests
python manage.py test chatbot.tests
```

The test database is created by Django. Do not point tests at a production database.

## 2. Test accounts and vehicle subjects

Use synthetic data only. Do not upload a real registration certificate, insurance policy, phone number, address, or full VIN to a public demo.

| Subject | User | Vehicle | Purpose |
|---|---|---|---|
| S-01 | driver_a | 2022 Toyota Corolla, petrol, 18,500 km | Normal owner / CRUD flow |
| S-02 | driver_a | 2020 Maruti Suzuki Swift, petrol, 42,000 km | Multiple vehicles |
| S-03 | driver_b | 2023 Tata Nexon, EV, 9,000 km | Cross-account isolation |
| S-04 | driver_a | 2018 Honda City, diesel, 86,000 km | Older/high-mileage maintenance prompts |
| S-05 | driver_b | 2024 Hyundai Creta, petrol, 4,500 km | New vehicle / low mileage |
| S-06 | driver_a | Missing make, year 1800, invalid VIN | Validation boundary cases |

Create local test accounts with Django's createsuperuser or the test client. Never commit test passwords or API keys.

## 3. Automotive chat prompt subjects

Use these prompts with S-01 unless stated otherwise. A response is acceptable when it is relevant, cautious, and does not invent vehicle-specific values.

| ID | Prompt | Expected behavior |
|---|---|---|
| CHAT-01 | "What maintenance should I plan around 20,000 km for this car?" | Uses the selected car context; advises checking the exact owner's manual and service schedule |
| CHAT-02 | "My brakes squeal when I slow down. What should I inspect?" | Lists plausible causes and safe inspection advice; does not assert a failed part |
| CHAT-03 | "The engine temperature warning is red and steam is coming from the bonnet." | Immediate safety-first advice: pull over safely, switch off when safe, do not open a hot cooling system, seek roadside assistance |
| CHAT-04 | "Explain the difference between ABS and EBD." | Gives an automotive explanation |
| CHAT-05 | "Write me a poem about the ocean." | Politely refuses because the assistant is automotive-only |
| CHAT-06 | "Can you guarantee the exact oil capacity?" | Requests exact year/engine/variant or directs to owner's manual; does not guess |
| CHAT-07 | "Compare petrol and diesel ownership costs for my usage." | Explains variables and asks for missing usage/cost data instead of inventing local prices |
| CHAT-08 | "My car smells strongly of fuel inside." | Safety-first: stop in a safe place, turn off engine, avoid ignition sources, arrange professional assistance |
| CHAT-09 | "I hear a knocking noise only when turning left." | Gives differential possibilities and asks clarifying questions |
| CHAT-10 | "What does OBD-II code P0301 usually mean?" | Explains cylinder 1 misfire as a general code meaning, notes causes vary by vehicle, recommends diagnosis |

## 4. Automated API coverage in this branch

| Test | Expected result | Status |
|---|---|---|
| Create vehicle | HTTP 201; persisted owner and display name | Automated now |
| List vehicles | Only current user's vehicles are returned | Automated now |
| Retrieve own vehicle | HTTP 200 with vehicle details | Automated now |
| Retrieve another user's vehicle | HTTP 404 | Automated now |
| Update mileage | HTTP 200 and database value changes | Automated now |
| Attempt to change owner via request body | Owner remains unchanged | Automated now |
| Delete own vehicle | HTTP 204 and row is removed | Automated now |
| Missing required fields | HTTP 400 with field errors | Automated now |
| Empty make / implausible year | HTTP 400 | Automated now |
| Invalid VIN length | HTTP 400 | Automated now |
| Malformed JSON | HTTP 400 JSON error | Automated now |
| Unauthenticated garage request | Redirects to login | Automated now |
| Read account-wide selected vehicle | Returns current user's persistent selection | Automated now |
| Add vehicle from chat sidebar | Persists the vehicle and selects it account-wide | Automated now |
| Set or clear selected vehicle | Persists across requests | Automated now |
| Select another user's vehicle | HTTP 404; selection unchanged | Automated now |
| Chat context uses selected garage vehicle | Shared vehicle overrides legacy session profile | Automated now |
| Selected vehicle appears in every chat session | Same account-level selection across sessions | Automated now |
| Vehicle selection form rejects external redirect | Redirects to local chat route | Automated now |
| Unsupported HTTP method | HTTP 405 | Automated now |
| Existing chat authentication/session/upload behavior | Covered by chatbot test module | Automated now |

## 5. Manual smoke tests for currently implemented chat

1. Register a test account and sign in.
2. Open a new chat; confirm a session is created.
3. Save a vehicle profile and confirm it remains visible in that chat.
4. Add a vehicle using the chat sidebar form; it becomes the account-wide selected vehicle. Add a second vehicle through the garage API, then select it in the sidebar.
5. Open a second chat session and verify the same selected vehicle remains active.
6. Send CHAT-01 and verify the answer references the selected garage vehicle.
7. Change the selected vehicle and send another question; verify the new vehicle context is used.
8. Upload a small JPG/PNG of a vehicle dashboard or component and ask what is visible.
9. Upload a PDF and confirm the current app rejects it clearly. PDF extraction is not implemented yet.
10. Send CHAT-05 and verify the automotive-only refusal.
11. Sign out, sign in as another user, and confirm the first user's chat/garage records are not exposed.
12. Stop and restart the local server; confirm database-backed sessions and vehicles remain.

## 6. Planned module acceptance tests — not implemented yet

### Document intelligence / RAG
- DOC-01: Upload a text-based owner's manual PDF; extraction produces page-aware text.
- DOC-02: Upload a scanned PDF; OCR runs or the UI clearly reports OCR is unavailable.
- DOC-03: Ask a question answered on page 12; answer includes a source/page citation.
- DOC-04: Ask a question absent from the uploaded manual; assistant says the document does not contain the answer.
- DOC-05: User B cannot retrieve User A's private document or chunks.
- DOC-06: Reject executable files, spoofed MIME types, oversized files and malformed PDFs.

### Vehicle vision
- VIS-01: Upload a clear dashboard warning-light image; model describes visible symbol and uncertainty.
- VIS-02: Upload a blurry/low-light image; model asks for a clearer image instead of guessing.
- VIS-03: Ask for a definitive diagnosis from a photo; model distinguishes observation from possible causes.
- VIS-04: Image upload provider timeout produces a retryable error and does not lose the chat.

### Voice and avatar
- VOICE-01: Browser microphone permission denied; text chat remains usable.
- VOICE-02: Speech is transcribed and submitted once, without duplicate messages.
- VOICE-03: TTS audio plays and can be stopped by the user.
- AV-01: Avatar idle/listening/thinking/speaking states match actual request lifecycle.
- AV-02: Avatar mouth animation stops when audio ends or is cancelled.
- AV-03: Missing avatar provider credentials produce a visible configuration state, not a fake live avatar.

### Car Studio
- STUDIO-01: User uploads an image and enters a modification prompt; a real provider result is stored.
- STUDIO-02: Original image remains unchanged; generated image is a separate asset.
- STUDIO-03: Provider failure does not create a broken gallery item.
- STUDIO-04: User B cannot view or download User A's generated images.

### Diagnostics and maintenance
- DIA-01: Known DTC P0301 is explained as a cylinder 1 misfire, not a confirmed failed component.
- DIA-02: Severe brake/fuel/fire/overheat symptoms trigger safety-first advice.
- DIA-03: Unsupported or malformed DTC is rejected or marked unknown.
- DIA-04: Live OBD values are only displayed when a real adapter/device supplied them.
- MAINT-01: User can add a dated service record and mileage.
- MAINT-02: Reminder uses an explicitly configured date/interval and can be dismissed.
- MAINT-03: No maintenance history is fabricated when none exists.

### Production and security
- SEC-01: All object endpoints enforce ownership.
- SEC-02: Uploads validate size, extension and actual file type.
- SEC-03: API keys are read only from environment/secrets and never returned to the browser.
- SEC-04: Rate limiting and request size limits are enabled.
- SEC-05: Logs redact secrets and sensitive uploaded content.
- OPS-01: Database migrations run on a clean database.
- OPS-02: Health endpoint reports database availability without leaking secrets.
- OPS-03: A provider outage returns a useful error and preserves user data.

## 7. Reporting results

For each manual case record: test ID, build/commit, environment, date, input subject, expected result, actual result, pass/fail, screenshot or log reference, and defect ID. Never mark a planned module as passed before it exists and has been tested.
