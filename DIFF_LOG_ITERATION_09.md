## Diff Log Iteration 09

**Geänderte/Neu hinzugefügte Dateien**
- backend/app/schemas.py — JobOut/JobRunOut für Job-Polling.
- backend/app/routers/jobs.py — Jobliste + Detail mit Runs; response_models.
- backend/app/routers/analytics.py — GET liefert nur persistierte Metrics (kein Sync-Fetch).
- backend/app/services/orchestrator.py — Publish lädt Remote-Videos via Storage, nutzt Idempotency-Key.
- backend/app/providers/tiktok_official.py — Idempotency-Header optional.

**Neue Endpoints/Queues/Tabellen**
- Endpoint: `/jobs/detail/{job_id}` für Jobstatus+Runs.
- Keine neuen Tabellen (Migration 0005 bereits).

**Breaking Changes / Migration Notes**
- GET /analytics/metrics/{project_id} liefert nur gespeicherte Metriken; frische Daten via `/analytics/metrics/{project_id}/refresh`.
