## Diff Log Iteration 12

**Geänderte/Neu hinzugefügte Dateien**
- backend/app/schemas.py – VideoAssetOut erweitert um plan/project/org/publish_response/created_at Felder.
- backend/app/tasks.py – Plan-Status wird nach Generate/Publish synchronisiert.
- backend/app/routers/video.py – Asset-Liste pro Projekt inkl. Signed URLs.
- backend/app/services/orchestrator.py – Deterministischer LLM-Fallback (llm.complete verfügbar).
- frontend/src/App.tsx – UI neu aufgebaut: Dashboard/Org-Switch, Calendar mit Approve/Lock/Generate/Publish, Video Library mit Previews/Publish, Queue/Analytics/Credentials/YouTube, Statusanzeige.

**Neue Endpoints/Queues/Tabellen**
- GET /video/assets/project/{project_id} (Signed URLs für Library).

**Breaking Changes / Migration Notes**
- Keine neuen Migrationen in dieser Iteration.
