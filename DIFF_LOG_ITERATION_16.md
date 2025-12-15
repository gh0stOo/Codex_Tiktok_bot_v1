## Diff Log Iteration 16

**Geänderte/Neu hinzugefügte Dateien**
- backend/app/services/usage.py – Limits-Matrix erweitert, enforce_quota nutzt Default-Limits.
- backend/app/routers/projects.py – Autopilot-Toggle Endpoint importiert HTTPException.
- frontend/src/App.tsx – Autopilot-UI-Blende bleibt, nutzt Toggle-Endpoint.

**Neue Endpoints/Queues/Tabellen**
- Keine neuen Endpoints beyond vorherige Iteration; Usage-Limits erweitert.

**Breaking Changes / Migration Notes**
- Keine Migrationen; Quoten können nun für weitere Metriken konfiguriert werden.
