# Architecture Overview (Target per projektplan.md)

## Services
- **Backend (FastAPI + SQLAlchemy 2.0 + Alembic)**: Auth/Sessions/RBAC, Orgs/Projects, Planning, Content, Credentials, Usage, Analytics, TikTok OAuth/Publish, LLM Orchestrator, RAG, Policy Engine. Runs behind Uvicorn. Structured JSON logging + request IDs (to be wired).
- **Worker + Scheduler (Celery + Redis)**: Executes plan generation, asset pipeline (LLM -> video -> captions/loudnorm -> thumbnail), publish, metrics fetch, DLQ/backoff, bandit/scheduler tasks.
- **Frontend (Vite/React/Tailwind/shadcn)**: Auth, Org switcher, Calendar (30x3), Queue/Logs, Video Library, Analytics, Credentials/Usage, TikTok connect, YouTube tool.
- **Datastores**: Postgres (business data, pgvector optional), Redis (broker/results), Object Storage (local/MinIO/S3) with tenant prefixes `org_{id}/project_{id}/posts/{post_id}/`.

## Domain Model (Kern)
- Identity: User, Organization, Membership (role), Session (refresh rotation), PasswordReset.
- Plans/Usage: Plan, Subscription (pending), UsageLedger/Aggregate (pending enforcement).
- Content: Project (autopilot/approval toggles), Post/Plan (30x3), VideoAsset, Job, Metric.
- Prompts/Knowledge: PromptVersion (versioned), KnowledgeDoc (pgvector/FTS), Brand voice prompts.
- Credentials: ProviderCredential (encrypted JSON, BYOK/Managed flags), rotation/versioning hooks.
- Social: SocialAccount (TikTok), OAuthToken (encrypted refresh/access).

## Providers (produktiver Pfad, keine Mocks)
- **TikTok Official**: OAuth2 (code exchange + refresh), encrypted tokens (Fernet), upload (direct/inbox) with idempotency keys, rate-limit handling, status polling, metrics fetch. Feature-flag off when unconfigured; returns clear error instead of mock data.
- **LLM (OpenRouter)**: Chat/completion client; orchestrator uses Pydantic schemas + repair loop; audit trail stored.
- **Video**: ffmpeg pipeline (captions burn-in, loudnorm, thumbnail). External generators optional via interface.
- **ASR**: faster-whisper + yt-dlp for YouTube audio; when unconfigured returns 503 (no mock payloads).
- **Storage**: Abstraction for local/S3/MinIO with tenant prefixes; signed URL generation for frontend previews (pending).

## Orchestrator & Agents
- JSON-only contracts with validation/repair: Research, Trend/Format, Creative Director, Script, Prompt Engineer, Compliance, QA/Judge, Scheduler Optimizer, Analytics Insight.
- Audit log per step with trace/request IDs; retries with backoff; usage/quota checks before invoking providers.

## Security & Compliance
- Multi-tenant isolation via `organization_id` on all business tables; RBAC enforced serverseitig.
- Tokens/Secrets encrypted at rest (Fernet/KMS-ready); never logged.
- Rate limits, budgets, and policy engine block prohibited content; is_aigc flag for TikTok uploads.

## Infra
- `infra/docker-compose.yml`: backend, worker, scheduler/beat, postgres, redis, frontend, minio (optional). Shared storage volume.
- Migrations under `migrations/`; alembic upgrade required before use.

## Observability (to be implemented)
- Structured JSON logs with request/task IDs, OpenTelemetry traces across API/Celery, metrics/health (/healthz, /readyz present). Frontend logging/metrics pending.
