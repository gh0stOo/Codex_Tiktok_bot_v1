## Diff Log Iteration 08

**Geänderte/Neu hinzugefügte Dateien**
- backend/app/models.py — Job erhält idempotency_key; Metric open_id schon vorher, JobRun Beziehung genutzt.
- migrations/versions/0005_job_idempotency.py — neue Spalte idempotency_key.
- backend/app/tasks.py — Celery Tasks mit JobRun-Logging, Retry, Metrics-Fetch; nutzen stored Tokens.
- backend/app/routers/video.py — Generate/Publish enqueuen Celery Tasks, Idempotency-Prüfung, Tokens aus Vault, Jobs zurückgegeben.
- backend/app/routers/analytics.py — Refresh-Endpoint enqueued fetch_metrics task.
- backend/app/providers/storage.py — read_bytes_uri für Streaming (lokal/S3).
- backend/app/providers/tiktok_official.py — Multipart Upload fix.
- migrations angewendet.

**Neue Endpoints/Queues/Tabellen**
- Endpoint: `POST /analytics/metrics/{project_id}/refresh`.
- Jobs now carry idempotency_key; JobRun table already present (0004).
- Celery tasks: generate_assets, publish_now, fetch_metrics (with JobRun logging).

**Breaking Changes / Migration Notes**
- Migration 0005 erforderlich (jobs.idempotency_key). Publish/Generate now async via tasks (API liefert job_id). Clients müssen ggf. Polling ergänzen.
