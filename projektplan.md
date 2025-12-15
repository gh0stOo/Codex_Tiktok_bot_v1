# Projektplan: ViralForge (TikTok AI SaaS)

## Ziel & Umfang
- AI-first Multi-Tenant SaaS für TikTok Shorts: Research → Monatsplan → Scripts/Storyboards → Video-Generation → Scheduling/Posting (offizielle API) → Analytics/Optimierung.
- Autopilot/Approval pro Organisation/Projekt, strikte Compliance (nur offizielle TikTok APIs, is_aigc Flag, Policy-Engine).

## Architektur (High-Level)
- Backend: FastAPI (Python 3.12), SQLAlchemy 2.0, Alembic, Postgres (prod), SQLite dev-optional.
- Workers: Celery + Redis + Beat (Workflows, Video/QA/Scheduler jobs), idempotente Tasks mit Backoff.
- Frontend: React (Vite) + Tailwind + shadcn/ui; SaaS UI mit Org-Switch, Kalender, Queue, Analytics.
- Storage: S3/MinIO Abstraktion mit tenant-scoped Prefixes. Object URIs: `org_{id}/project_{id}/posts/{post_id}/`.
- Providers: TikTok Official Posting/Display API (OAuth2), OpenRouter (LLM), VideoProvider (Veo/Kling wrapper), TTSProvider (optional), ASR (faster-whisper), yt-dlp (Audio only; optional toggle).

## Domainmodell (Kern-Tabellen)
- Identity: Organization, User, Membership (RBAC owner/admin/editor/viewer), Session (refresh rotation).
- Plans/Usage: Plan, Subscription, UsageLedger, UsageAggregate.
- Credentials: ProviderCredential (Fernet-verschlüsselte JSON, BYOK/Managed Flag, Versioning/Rotation-Policy).
- Prompts/Knowledge: PromptTemplate (versioned, schema_json), KnowledgeDoc (pgvector, tenant-isoliert).
- Social: SocialAccount (TikTok), OAuthToken (encrypted refresh/access).
- Content: Project (autopilot, budgets, brand kit, llm/video config), ContentPlan (month JSON), PostItem (status, approvals, lock), Asset, JobRun, Metrics.

## AI Control Plane & Agenten
- Orchestrator-Service (deterministisch, budgets/quotas-check, audit-log, OpenTelemetry Traces + IDs durchreichend zu Tasks).
- Agenten (Pydantic-JSON Output mit confidence + rationale): Research, Trend/Format, Creative Director, Script (DE), Prompt Engineer, Compliance/Claims, QA/Judge, Scheduler Optimizer, Analytics Insight.
- Prompt Library: PromptTemplate-Tabelle, Brand Voice Prompt pro Org/Projekt, Repair-Pipeline bei Schema-Verletzung (N Retries mit “repair prompt”).
- RAG: pgvector KnowledgeDoc; Retrieval für Brand Constraints, Past Winners, Avoid List, Experiments.
- Similarity Guard: verhindert near-duplicate Hooks/Posts im Monatsplan.

## Kern-Workflows (Celery orchestriert)
- A) Generate Month Plan (30 Tage x 3 Slots): Research → Format-Mix → Hooks/Outline → QA/Repair → ContentPlan persist.
- B) Produce Assets (post_id): Prompt→Render (VideoProvider)→ffmpeg (captions, loudnorm, thumb)→QA→store Asset + metrics stub.
- C) Publish (post_id): Compliance check → optional Approval → TikTokOfficialPublisher (Direct/Inbox) mit idempotency-key + polling/webhook.
- D) Learn & Optimize: Fetch metrics → Slot-Bandit update → Analytics Insights/Experiments → persist KnowledgeDoc.
- E) YouTube→Transcript→DE Translation→Shortform Ideas (optional plan generation).

## Compliance & Sicherheit
- Offizielle TikTok APIs only; keine Scrapes/Headless. is_aigc setzen. Policy-Engine blockt verbotene Kategorien/Claims (medizinisch/finanziell/Taboo-Liste) hart, versioniert und getestet.
- Token/Secrets: Fernet-verschlüsselt, kein Logging; ProviderCredential BYOK/Managed per Org, Rotation/Versioning-Policy.
- Budgets/Quotas: Org/Projekt token- und Videosekunden-Limits, max Regenerations pro Post, cheap-first-pass Strategy. API-Rate-Limits per Org; Celery Concurrency-Limits.

## Services & Endpunkte (Backend)
- Auth: /api/auth/register, login, refresh, logout.
- Orgs: /api/orgs, /api/orgs/{id}/members, /plan, /usage, /credentials.
- Prompts/Knowledge: /prompts, /knowledge/upload.
- Projects: create/list, settings.
- Planning: POST /projects/{id}/plans/generatemonth=YYYY-MM, GET calendar.
- Posts: PUT /posts/{id}, /approve, /lock, /generate_assets, /publish_now.
- Jobs: /api/jobs?org_id=...
- Analytics: /api/analytics?project_id=...
- YouTube tool: /api/youtube/transcribe.
- TikTok OAuth: /auth/tiktok/start|callback. Health: /healthz, /readyz.

## Frontend (Vite/React/Tailwind/shadcn)
- Auth-Flows, Org-Switcher, RBAC Navigation.
- Org Dashboard: Plan/Usage bars, Credentials, Connected TikTok Accounts.
- Project Settings: Brand kit, topics, autopilot toggle, approval toggle, budgets, provider routing (BYOK/Managed).
- Calendar (30x3): edit scripts/storyboard/prompts, confidence/rationale, approve/lock, AI improve.
- Production Queue: Jobs status/retries/logs.
- Video Library: preview/download assets (signierte URLs, ablaufend, Media-Proxy-Schicht).
- Analytics: slot performance, format performance, cost.
- YouTube Tool UI: upload URL, transcribe, translate, create ideas/plan.

## Observability & Ops
- OpenTelemetry Tracing (API + Celery) mit Request-/Task-ID; strukturierte JSON-Logs; Audit-Logs für AI-Entscheidungen.
- Rate Limits & Concurrency: per-Org API-Limits, Celery-Queue Limits, Hard/Soft Budget-Stops.
- Resilience: DLQ für Celery, Retry mit Jitter, Wiederanlauf-Strategie bei Worker/Queue-Ausfall, TTL/Retention für Jobs/Logs.
- Migration/Upgrade: Alembic Conventions, Seed/Fixtures, Backfill-Jobs für neue Felder. Key-Rotation Jobs für Credentials.

## Testing
- Unit: Prompt Schema/Repair, Quota/Budget Enforcement, RAG Isolation, Policy-Engine Rules.
- Integration: Mock OpenRouter/TikTok/Video/TTS/ASR, Posting idempotency/backoff, Scheduler Bandit.
- E2E: lokales Demo-Szenario (Demo Org/Project/Plan 30x3) inkl. JobRuns/Metrics.

## Infra & Deploy
- Monorepo: backend/, frontend/, infra/docker-compose.yml, migrations/, README.md.
- docker-compose: api, worker, scheduler, redis, postgres, frontend, minio (optional). Object storage via MinIO local.
- Makefile, .env.example. Structured logging mit request-id.

## Erste Meilensteine (Umsetzungsreihenfolge)
1) Bootstrap monorepo: tooling, docker-compose, .env.example, Makefile, base FastAPI + healthz.
2) DB Schema + Alembic + seed demo org/user/project/plan.
3) Auth + RBAC + org/project APIs; ProviderCredential encryption (Fernet key env) + Rotation Hooks.
4) Prompt/Knowledge subsystem (pgvector), Orchestrator skeleton + OpenRouter mock.
5) TikTok OAuth scaffolding + official posting client (stub/mocked für dev).
6) AI Agents Pydantic contracts + repair loop; Workflow A (plan) end-to-end mit mocks.
7) Workflow B (assets) mit VideoProvider stub + ffmpeg pipeline.
8) Workflow C (publish) mit idempotent tasks; approval gates/autopilot modes.
9) Workflow D (learn/optimize) + Scheduler Optimizer bandit stub.
10) Frontend: auth, org/project settings, calendar, queue, analytics, YouTube tool.
11) Hardening: budgets/quotas, audit logging, policy engine tests, DLQ/Retention, key rotation.
