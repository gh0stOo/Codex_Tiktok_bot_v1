## Diff Log Iteration 17

**Geänderte/Neu hinzugefügte Dateien**
- backend/app/services/usage.py – Limits-Matrix, concurrency check.
- backend/app/services/orchestrator.py – Storage-Usage-Logging.
- backend/app/providers/tiktok_official.py – Inbox-Upload-Methode.
- backend/app/routers/video.py – Publish unterstützt use_inbox.
- backend/app/tasks.py – Publish-Task akzeptiert use_inbox.
- backend/app/routers/usage.py (neu) – Usage-Snapshot API.
- backend/app/main.py – Usage-Router registriert.
- backend/app/routers/projects.py – HTTPException import.
- frontend/src/App.tsx – Usage-Widget, API-Call, UI erweitert.

**Neue Endpoints/Queues/Tabellen**
- GET /usage/{org_id} – Usage-Snapshot.
- Optionales Inbox-Publish via use_inbox Flag.

**Breaking Changes / Migration Notes**
- Keine Migrationen; compose restart empfohlen, um neuen Router/Beat-Polling zu laden.
