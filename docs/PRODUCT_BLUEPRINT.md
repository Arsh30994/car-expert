# Car Expert AI — Automotive Intelligence Platform

## Product goal
Turn the existing Django automotive chat application into a working multimodal automotive intelligence platform. The AI companion is the primary interface; every module shares an owner-scoped vehicle knowledge layer.

## Existing baseline
The repository already contains Django authentication, conversation sessions, AI/ML API integration, image analysis and a per-session VehicleProfile. The per-session profile remains for compatibility during migration. It is **not** the new persistent garage.

## Research-inspired modules
| Inspiration | Adopted capability | Acceptance criterion |
| --- | --- | --- |
| CARFAX Car Care / Drivvo | Persistent vehicle garage | User can create, list, edit and delete their own cars |
| OBDLink / OBDeleven | Diagnostic trouble codes | Real OBD code interpretation; hardware integration is optional and explicitly labeled |
| Porsche vehicle configurator | Car customization | Users can preview vehicle variants |
| Adobe Firefly | AI image editing | Image generation provider returns a real persisted image |
| AI avatar platforms | Conversational avatar | Real TTS output and synchronized visible speaking state |
| NotebookLM / RAG | Document-grounded answers | Answers cite the user's uploaded manual/invoice |
| Automotive learning platforms | Interactive learning | Quizzes and progress saved |

## Architecture
- React + TypeScript frontend (future milestone), Django REST backend.
- PostgreSQL in production; SQLite for local development.
- Owner-scoped Vehicle is the canonical garage entity.
- Conversations, documents, diagnostics and generated images reference Vehicle.
- AI provider abstraction prevents coupling to a single model.
- Async jobs for document parsing, video and image generation.
- Private object storage for uploads; validate content and size.
- Deterministic escalation for safety-critical symptoms.

## Milestones
1. **Foundation:** owner-scoped vehicle CRUD, tests, migration, documented API.
2. **Knowledge:** link conversations to Vehicle; document upload, parsing, RAG.
3. **Vision & diagnostics:** validated image analysis, DTC knowledge and reports.
4. **Voice & avatar:** STT, TTS, 3D avatar UI and speech animation.
5. **Car Studio:** provider-backed image editing, gallery, before/after.
6. **Productization:** responsive dashboard, monitoring, deployment, integration tests.

## Safety and academic integrity
Do not claim a diagnostic certainty from a photograph or infer a part number without evidence. Do not represent UI mockups as functioning integrations. Document all provider credentials and hardware prerequisites. Record test outputs and screenshots only after running them.

## Initial API
- GET /api/garage/vehicles/ — list current user's vehicles
- POST /api/garage/vehicles/ — create vehicle (JSON)
- GET /api/garage/vehicles/{id}/ — retrieve own vehicle
- PATCH /api/garage/vehicles/{id}/ — update own vehicle
- DELETE /api/garage/vehicles/{id}/ — delete own vehicle

Django session authentication and CSRF apply to modifying requests.
