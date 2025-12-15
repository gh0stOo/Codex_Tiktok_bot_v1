## Diff Log Iteration 07

**Geänderte/Neu hinzugefügte Dateien**
- backend/app/routers/video.py — publish now can use stored encrypted TikTok tokens (auto-refresh), signed URL/streaming endpoints retained; policy failures propagate.
- backend/app/providers/storage.py — read_bytes_uri for local/S3 streaming.
- backend/app/schemas.py — VideoAssetOut includes signed URLs.
- backend/app/providers/tiktok_official.py — multipart upload fix.
- backend/app/routers/tiktok.py — refresh endpoint already added (unchanged this iter).
- backend/app/tasks.py, backend/app/celery_app.py — task scaffolds present (from prior iter), rebuilt in image.

**Neue Endpoints/Queues/Tabellen**
- Updated `/video/publish/{asset_id}` to default to stored TikTok tokens with refresh.

**Breaking Changes / Migration Notes**
- None (no schema changes). Clients may omit access_token/open_id when `use_stored_token=true`.
