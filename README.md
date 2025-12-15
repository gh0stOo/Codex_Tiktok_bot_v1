# Codex TikTok SaaS (Official-API, Multi-Tenant)

Production-shaped SaaS for TikTok automation per `projektplan.md`: FastAPI + Celery + Postgres/Redis/MinIO + React (Vite/Tailwind/shadcn). No mock providers in produktivem Pfad; only tests use mocks. TikTok strictly über offizielle APIs.

## Status (WIP)
- Auth/Sessions mit Refresh-Rotation, RBAC-Checks, org-scope auf Kernobjekten (Plans/Assets). Weitere Features (TikTok Publish/Metrics, Orchestrator/LLM/RAG, UI, Quotas) werden iterativ ergänzt; siehe `CHANGELOG_AUTONOMOUS.md`.

## Schnellstart (Docker)
```bash
docker compose -f infra/docker-compose.yml up --build -d
docker compose -f infra/docker-compose.yml exec backend sh -c "cd /app/migrations && PYTHONPATH=/app alembic upgrade head"
```
Health: `curl http://localhost:8000/health/healthz`

## Lokal (ohne Docker)
```bash
python -m venv .venv && .\\.venv\\Scripts\\activate
pip install -r backend/requirements.txt
cd backend && uvicorn app.main:app --reload
# Frontend
cd ../frontend && npm install && npm run dev
```

## Environment
Copy `.env.example` -> `.env` and set:
- `DATABASE_URL`, `REDIS_URL`, `BROKER_URL`
- `SECRET_KEY`, `FERNET_SECRET`
- TikTok: `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`, `TIKTOK_REDIRECT_URI`
- LLM: `OPENROUTER_API_KEY`, `DEFAULT_LLM_MODEL`
- Storage: `STORAGE_BACKEND`, `STORAGE_PATH` (local) or MinIO/S3 config
- Feature toggles: `ENABLE_PGVECTOR`, `ENABLE_YTDLP`, `ENABLE_LOCAL_ASR`

## Seeds (Demo)
```bash
python scripts/seed.py
```
- legt Demo-User/Org/Project/Plan an. Credentials nur, wenn echte Keys gesetzt (verschlüsselt via Fernet).

## Make Targets
```
make up | down | logs
make migrate   # alembic upgrade head
make seed
make test      # sobald Tests ergänzt
```

## Ordnerstruktur
- `backend/` FastAPI, Celery, Providers
- `frontend/` React Vite Tailwind shadcn (UI wird ausgebaut)
- `infra/` docker-compose, volumes
- `migrations/` Alembic
- `docs/` Architecture, Checklist, API, FINAL_VERIFICATION (wird gefüllt)
- `scripts/` Seed/utility

## Compliance & Sicherheit
- Offizielle TikTok API only, Tokens verschlüsselt (Fernet), keine Secrets im Log.
- Multi-Tenant Isolation via organization_id + RBAC; weitere Guardrails folgen.
- Kein Mock im Produktpfad; bei fehlenden Keys liefert API klare Fehlermeldungen.

## Nächste Schritte
- TikTok Publish/Metrics, Orchestrator/LLM/RAG, Quota/Budget, Storage-Abstraktion, Observability, vollständige UI. Fortschritt in `CHANGELOG_AUTONOMOUS.md` und `IMPLEMENTATION_REPORT.md`.
