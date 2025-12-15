# Master Checklist (per projektplan.md) - WIP

Legend: OK = erledigt, PARTIAL = teilweise, MISSING = offen/falsch.

## Foundations & Ops
- PARTIAL docker-compose (api, worker, scheduler/beat, redis, postgres, frontend) läuft; MinIO optional.
- MISSING Structured JSON logging, request/task IDs, OpenTelemetry.
- MISSING Makefile komplett (up/down/logs/test/lint/format/migrate/seed).
- PARTIAL .env.example weitgehend; weitere Toggles offen.
- OK Health endpoints /healthz /readyz.

## Identity, Security, Tenanting
- PARTIAL Auth (register/login/refresh/logout), Refresh-Rotation, Reset/Verify Scaffold.
- PARTIAL RBAC serverseitig (teilweise Checks).
- PARTIAL Multi-tenant isolation (org_id auf den meisten Tabellen; Guarding unvollständig).
- MISSING Secrets-Redaction/Logging, Auth-Rate-Limits.

## Core Domain
- PARTIAL Organizations/Memberships (keine Invites/Rollen mgmt).
- MISSING Projects mit Autopilot/Approval/Budgets.
- PARTIAL Plans (30x3) mit Approve/Lock/Confidence/Rationale – Approve/Lock/Generate vorhanden; Confidence/Rationale fehlen.
- MISSING Usage Metering/Enforcement (Tokens/Videosek./Publishes/ASR/Storage/Concurrency).
- MISSING Plans/Subscriptions/Quota-Tiers.

## Providers & Integrations (keine Mocks im Prod-Pfad)
- PARTIAL TikTok OAuth + Publish: Tokens verschlüsselt, Auto-Refresh, Idempotency-Header; kein Status-Polling/Inbox.
- PARTIAL Metrics Fetch: Task vorhanden, Persistenz minimal.
- PARTIAL OpenRouter LLM: Client + Repair Loop; keine Agents/Audit.
- PARTIAL Video Pipeline: ffmpeg Render (ohne Captions/Loudnorm).
- MISSING ASR (faster-whisper) + yt-dlp, Übersetzung.
- PARTIAL Storage (local/S3) mit Signed URLs/Streaming; Range fehlt.

## Orchestrator, Agents, RAG, Policy
- PARTIAL Orchestrator: Pydantic ScriptSpec, Repair, Policy-Check; kein Audit/Trace.
- MISSING Agent-Module (Research/Trend/Creative/PromptEng/Compliance/QA/Scheduler/Analytics).
- MISSING Policy-Engine komplett (Similarity-Guard, Verbotslisten).
- MISSING RAG (pgvector/FTS) mit Isolation/Retrieval.
- MISSING Audit Trail + OTel.

## Workflows & Jobs
- PARTIAL Celery Tasks für Generate/Publish/Metrics mit JobRuns/Idempotency; kein DLQ/Jitter.
- MISSING Beat Schedules (Metrics/Rotation/Backfill).
- PARTIAL JobRun/Audit Persistence (JobRuns vorhanden, Audit/TTL fehlt).

## Frontend (Vite/Tailwind/shadcn)
- MISSING Auth/Session.
- MISSING Org-Switcher + RBAC-Navigation.
- MISSING Dashboard (Usage/Creds/TikTok-Connect) – Connect/Plan vorhanden, kein Usage.
- MISSING Calendar (30x3) mit Edit/Approve/Lock/Confidence/Rationale/AI-Improve – Approve/Lock/Generate vorhanden.
- MISSING Queue/Logs View – Jobs/Runs werden angezeigt.
- MISSING Video Library Previews (Signed URLs) – Library mit Signed URLs/Publish vorhanden.
- MISSING Analytics (Slots/Formats/Kosten) – Metrics-Listing/Refresh vorhanden.
- MISSING TikTok Connect UI; YouTube Tool; Autopilot/Approval Toggles – Connect/YouTube Buttons vorhanden, Autopilot offen.

## Testing
- MISSING Unit: Orchestrator Schema/Repair, Quotas, Tenant Isolation, Policy (teilweise vorhanden).
- MISSING Integration: Mock Providers, Posting Idempotency/Backoff, Scheduler Bandit.
- MISSING E2E Demo Flow.

## Seeds & Docs
- PARTIAL Seed Script (Demo Org/User/Project/Plan; keine Assets/Metrics/Quotas).
- PARTIAL README aktualisiert; API/FINAL_VERIFICATION pending.
- MISSING FINAL_VERIFICATION.md vollständig.
