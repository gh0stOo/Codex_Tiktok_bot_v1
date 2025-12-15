## Diff Log Iteration 11

**Geänderte/Neu hinzugefügte Dateien**
- frontend/src/App.tsx — UI neu gebaut: Auth/Org/Project Auswahl, Calendar (30x3) mit Generate, Queue/Jobs, Credentials, TikTok Connect Hinweis, Analytics (persistierte Metrics), YouTube Tool-Stub, Storage-Signed-URL-Hinweis, Metrics Refresh.
- migrations/versions/0006_publish_response.py — neue Spalte publish_response.
- backend/app/models.py — publish_response Feld.
- backend/app/tasks.py — Publish-Task speichert Response im Asset, setzt Status.
- backend/app/services/orchestrator.py — Idempotency-Header, Remote-Video-Fetch vor Upload.

**Neue Endpoints/Queues/Tabellen**
- Tabelle: video_assets.publish_response (Migration 0006).

**Breaking Changes / Migration Notes**
- Migration 0006 erforderlich; Compose erneut gebaut und ausgeführt.
