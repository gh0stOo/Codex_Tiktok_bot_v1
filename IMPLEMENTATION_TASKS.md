## Sequenzieller Task-Plan (DoD + Verifikation)

1) **Infra/Base Hardening**
   - DoD: Compose services (backend, worker, scheduler/beat, redis, postgres, frontend, minio) build+start; Alembic env wired; structured logging + request IDs scaffolded.
   - Verify: `docker compose -f infra/docker-compose.yml up --build -d`; `docker compose -f infra/docker-compose.yml exec backend sh -c "cd /app/migrations && PYTHONPATH=/app alembic upgrade head"`; `curl http://localhost:8000/health/healthz`.

2) **Auth + Sessions + RBAC + Tenant Enforcement**
   - DoD: register/login/refresh/logout with refresh rotation + revoke; password reset + email verify scaffolds; RBAC (owner/admin/editor/viewer) enforced on org/project routes; organization_id scoped on all business tables + query filters.
   - Verify: pytest suite for auth/rbac/tenant isolation; manual: register/login, create org/project, cross-tenant access returns 403.

3) **Credentials & Storage**
   - DoD: ProviderCredential model with Fernet/KMS encryption, BYOK/Managed flags, rotation metadata; secrets never logged; object storage abstraction (local + S3/MinIO) with tenant prefixes + signed URLs; .env.example complete.
   - Verify: unit tests for encrypt/decrypt + tenant prefixes; upload/download via storage adapter; `make lint && make test`.

4) **TikTok Official Integration**
   - DoD: OAuth2 start/callback, token encryption, refresh handling; publisher supporting direct/inbox upload, idempotency keys, rate-limit handling, status polling; metrics fetch persisted; feature-flagged UI warnings when not configured.
   - Verify: integration tests with mock provider; manual: OAuth flow using test creds (or expected error when missing key with clear message); publish endpoint returns queued job with idempotency.

5) **LLM/Prompts/Orchestrator**
   - DoD: OpenRouter adapter wired; prompt library (versioned) + brand voice; orchestrator JSON-only with Pydantic schemas + repair loop + audit log; agent modules (research, creative director, script, prompt engineer, compliance, QA/judge, scheduler optimizer, analytics insight).
   - Verify: unit tests for schema validation/repair; orchestrator run produces validated plan/post JSON; audit log entries stored.

6) **RAG & Policy**
   - DoD: KnowledgeDoc ingestion with pgvector/FTS fallback, tenant isolation; retrieval used in orchestrator; similarity guard; policy engine blocking restricted topics with tests.
   - Verify: tests for retrieval isolation and policy blocking; manual: attempt restricted content returns error.

7) **Workflows & Jobs (Celery)**
   - DoD: tasks for month-plan generation (30x3), asset generation (ffmpeg captions+loudnorm+thumb), publish, metrics fetch; retries with backoff/jitter; idempotent job records; DLQ/retention; beat schedules.
   - Verify: run `docker compose -f infra/docker-compose.yml exec worker pytest tests/test_jobs.py`; trigger plan->asset->publish flow via API; inspect storage outputs.

8) **Frontend (Vite/Tailwind/shadcn)**
   - DoD: Auth flows; org switcher; dashboard with usage/credentials; TikTok connect UI; calendar (30x3) with approve/lock/confidence/rationale; queue view; video library with previews (signed URLs); analytics; YouTube tool; autopilot/approval toggles.
   - Verify: `npm test` (if present) or `npm run build`; manual UI smoke in docker compose; login with demo user, navigate all sections.

9) **Observability, Rate Limits, Budgets**
   - DoD: structured JSON logs, request/task IDs; OpenTelemetry wiring; rate limits per org; quota enforcement (tokens, renders, publishes, ASR, storage, concurrency); DLQ handling.
   - Verify: unit tests for quota enforcement; inspect logs include trace/request IDs; rate-limit responses.

10) **Seeds, Docs, Final Verification**
    - DoD: Seed script creates demo org/user/project/month plan (30x3), credentials placeholders, sample knowledge docs, metrics; README/docs updated (ARCHITECTURE, API, CHECKLIST, FINAL_VERIFICATION); implementation report updated zu ✅ wenn erfüllt.
    - Verify: `make seed`; `docker compose -f infra/docker-compose.yml up --build`; `docker compose -f infra/docker-compose.yml exec backend sh -c "PYTHONPATH=/app alembic upgrade head"`; End-to-End Flow nach FINAL_VERIFICATION.
