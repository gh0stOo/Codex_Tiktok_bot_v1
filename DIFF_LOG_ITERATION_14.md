## Diff Log Iteration 14

**Geänderte/Neu hinzugefügte Dateien**
- backend/app/providers/tiktok_official.py – Status-Endpoint get_video_status, Path-Import.
- backend/app/routers/video.py – Publish-Status-API mit Token-Refresh, Usage-Logging für Publish/Generate, Plan-Gate bleibt.
- frontend/src/App.tsx – Publish-Status-Button in Library, Logout-Reset.

**Neue Endpoints/Queues/Tabellen**
- GET /video/status/{asset_id} – prüft TikTok Video-Status über offizielle API.

**Breaking Changes / Migration Notes**
- Keine neuen Migrationen. TikTok Credentials weiterhin erforderlich für Status-Abfragen.
