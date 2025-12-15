## Diff Log Iteration 13

**Geänderte/Neu hinzugefügte Dateien**
- backend/app/routers/video.py – Quoten-Logging, Publish-Gate (Approve/Lock), Usage-Metrik für Publish.
- frontend/src/App.tsx – Logout-Funktion, Status-Reset.

**Neue Endpoints/Queues/Tabellen**
- Keine.

**Breaking Changes / Migration Notes**
- Publish verweigert jetzt ungeprüfte oder gelockte Pläne (außer bereits published); Quoten-Logging für Publish/Generate.
