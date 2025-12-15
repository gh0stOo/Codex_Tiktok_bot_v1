## Implementation Report - WIP

Legende: OK = vorhanden, PARTIAL = teilweise, MISSING = fehlt/falsch.

### Infrastruktur & Ops
- [PARTIAL] Docker Compose (backend, worker, scheduler/beat, redis, postgres, frontend, minio) end-to-end – läuft ohne MinIO; Prod-Hardening/Features fehlen.
- [PARTIAL] Alembic Migrations – 0001-0006 vorhanden; keine Naming Conventions/Branching.
- [MISSING] Makefile Targets (up/down/logs/test/lint/format/migrate/seed).
- [MISSING] Structured JSON Logs, Request/Task IDs, OpenTelemetry.
- [OK] Health /healthz /readyz.

### Identity, Auth, RBAC, Multi-Tenancy
- [PARTIAL] Auth (register/login/refresh/logout), Refresh-Rotation, Revoke, Reset/Verify Scaffold – Session-Tokens/Rotation, Reset/Verify; kein Mail/Rate-Limit.
- [PARTIAL] Sessions Stored/Rotation/Revoke – Sessions vorhanden; kein Device Mgmt/UI.
- [PARTIAL] RBAC (owner/admin/editor/viewer) serverseitig – teilweise Checks; Policy fehlt.
- [PARTIAL] Multi-Tenant Isolation (org_id überall + Guards) – org_id auf Kern-Tabellen; kein globaler Guard.

### Organizations, Projects, Plans, Quotas
- [PARTIAL] Orgs CRUD + Membership Mgmt – Create/List + Owner; keine Invites/Rollenwechsel.
- [MISSING] Projects mit Autopilot/Approval/Budgets.
- [PARTIAL] Month Plan (30x3) mit Approve/Lock/Confidence/Rationale – Calendar mit Approve/Lock; Confidence/Rationale fehlen.
- [PARTIAL] Status-Transitions (Approve/Lock/Publish mit Gates) – Approve/Lock umgesetzt; keine Gates/Approvals vor Publish.
- [MISSING] Usage Metering/Enforcement (Tokens/Videosek/Publishes/ASR/Storage/Concurrency).
- [MISSING] Plans/Subscriptions/Quotas.

### Credentials & Security
- [PARTIAL] ProviderCredential (BYOK/Managed), Fernet/KMS, Version/Rotation – Fernet in API; Rotation/Enforcement fehlen.
- [MISSING] Secrets nie loggen; Redaction Middleware.
- [MISSING] Key Mgmt UI/API.

### Providers & Integrationen
- [PARTIAL] TikTok Official (OAuth2, Refresh, verschlüsselte Tokens, Direct/Inbox, Idempotency, Rate-Limit, Status) – OAuth, Auto-Refresh, Idempotency-Header; kein Status-Polling/Inbox.
- [PARTIAL] Metrics Fetch (offizielle Endpoints, persistiert) – Task + Persist minimal; Sync-Fetch entfernt.
- [PARTIAL] OpenRouter LLM (Schema-Validation/Repair) – Client + Repair; keine Agents/Audit.
- [PARTIAL] VideoProvider (ffmpeg captions+loudnorm+thumb) – Overlay; keine Captions/Loudnorm.
- [MISSING] ASR (faster-whisper) + yt-dlp – 503 wenn unkonfiguriert.
- [PARTIAL] Storage (local/S3/MinIO, Tenant-Prefix, Signed URLs) – Storage + Signed URL/Stream; Range fehlt.

### Orchestrator, Agents, RAG
- [PARTIAL] Orchestrator (Pydantic JSON, Repair, Audit, OTel) – ScriptSpec/Repair/Policy; kein Audit/OTel.
- [MISSING] Agents (Research, Trend, Creative, Script, PromptEng, Compliance, QA, Scheduler, Analytics).
- [MISSING] Prompt Library/Brand Voice, Repair Loop – Tabelle vorhanden, Flow fehlt.
- [MISSING] RAG (pgvector/FTS), Similarity Guard.
- [MISSING] Policy Engine (Restricted Content) – nur simple Blockliste.

### Workflows & Jobs (Celery)
- [PARTIAL] Tasks für Plan/Assets/Publish/Metrics, Retries/Backoff/Idempotency – Tasks + Idempotency/JobRuns; kein DLQ/Jitter/Inbox/Status.
- [MISSING] Scheduler/Beat (Metrics, Rotation, DLQ).
- [PARTIAL] JobRun/Audit, DLQ – JobRuns vorhanden; DLQ/Audit fehlen.

### Frontend (Vite/React/Tailwind/shadcn)
- [PARTIAL] Auth/Session, Org-Switcher/RBAC – Auto-Login Demo, kein Refresh/Logout.
- [PARTIAL] Dashboard (Usage/Creds/TikTok Connect) – ohne Usage.
- [PARTIAL] Calendar (30x3) mit Approve/Lock/Generate/Publish – keine Confidence/Rationale/AI-Improve.
- [PARTIAL] Queue/Logs, Video Library (Signed URLs), Analytics, TikTok Connect UI, YouTube Tool, Autopilot/Approval Toggles – Library/Queue/Analytics/Connect/YouTube minimal, keine Autopilot-Toggles.

### Documentation & Tooling
- [PARTIAL] README – ohne Mock-Botschaft, Features WIP.
- [PARTIAL] docs/CHECKLIST – WIP-Status aktualisiert.
- [PARTIAL] docs/ARCHITECTURE – Zielarchitektur; Umsetzung offen.
- [MISSING] docs/API – veraltet.
- [PARTIAL] FINAL_VERIFICATION – Skeleton.

### Seeds & Demo
- [PARTIAL] Seed Script (Demo Org/User/Project/Plan 30x3, ohne Mocks) – legt Demo an, keine Assets/Metrics/Quotas.
- [MISSING] Usage/Metrics Seed.

### Tests
- [PARTIAL] Unit (Orchestrator/Quotas/Tenant/Policy) – wenige Tests vorhanden.
- [MISSING] Integration (Mock Providers, Idempotency/Backoff, Scheduler).
- [MISSING] E2E Demo Flow.

### Bekannte Mock-/Dummy-Stellen außerhalb tests/
- frontend/src/App.tsx (Auto-Login Demo, vereinfachte Flows).
- README/docs (WIP-Hinweise, kein Mock-Pfad mehr, aber fehlende Features).
