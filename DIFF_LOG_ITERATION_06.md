## Diff Log Iteration 06

**Geänderte/Neu hinzugefügte Dateien**
- backend/app/providers/storage.py — read_bytes_uri added for local/S3 streaming.
- backend/app/schemas.py — VideoAssetOut enthält signed URLs.
- backend/app/routers/video.py — signed URLs endpoint, streaming endpoint, policy error handling, storage signed URLs in responses.
- backend/app/providers/tiktok_official.py — upload uses proper multipart; minor handling.
- backend/app/routers/analytics.py — metrics persistence cleanup.
- backend/app/routers/tiktok.py — refresh endpoint added (token refresh).
- backend/app/tasks.py (neu) — Celery tasks for generate_assets/publish/enqueue placeholders.
- backend/app/celery_app.py — retry/backoff settings, autodiscover tasks.

**Neue Endpoints/Queues/Tabellen**
- Endpoints: `/video/assets/{asset_id}/signed`, `/video/assets/{asset_id}/stream`, `/tiktok/refresh`.
- Celery tasks: tasks.generate_assets, tasks.publish_now, tasks.enqueue_due_plans.

**Breaking Changes / Migration Notes**
- Keine Migration. Asset paths may now be S3 URIs; streaming endpoint proxies data.
