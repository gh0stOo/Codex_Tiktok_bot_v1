## Diff Log Iteration 05

**Geänderte/Neu hinzugefügte Dateien**
- backend/app/services/orchestrator.py — neu aufgebaut mit Pydantic ScriptSpec, repair loop, policy checks, storage-backed asset writes.
- backend/app/providers/storage.py (neu) — Storage abstraction (local, S3/MinIO) mit tenant prefixes und signed URL helper.
- backend/app/config.py — S3/MinIO Credentials/Prefix Settings ergänzt.
- backend/app/routers/video.py — Asset-Generation fängt Policy-Fehler ab und markiert Job, gibt 400 zurück.
- .env.example — Storage S3 Felder ergänzt.

**Neue Endpoints/Queues/Tabellen**
- Keine neuen Endpoints/Tabellen in dieser Iteration.

**Breaking Changes / Migration Notes**
- Keine Migration. Asset-Pfade können nun Storage-URIs sein (lokal oder s3://). Clients sollten URIs tolerant behandeln.
