## Issues Iteration 16

1) **Inbox-Fallback & Status UX**
- Befund: Keine Inbox-Upload-Variante, Polling vorhanden aber UI/DB-Status-Harmonisierung rudimentär.
- Fix-Plan: Publish-Task mit optionalem Inbox-Path, UI-Hinweis/Flag; Status normalisieren (processing/succeeded/failed).

2) **Quoten/Usage Dashboard**
- Befund: Limits-Matrix hinzugefügt, aber UI/API fehlen zur Anzeige; keine Enforcement für Storage/ASR/Concurrency in Tasks.
- Fix-Plan: Usage-API + UI-Widget, Enforcement in Tasks (ASR/storage/concurrency).

3) **Auth/RBAC/Approval-Gates im UI**
- Befund: Autopilot-Schalter da, aber keine Rolle-basierte Anzeige, kein Approval-Status oder Lock-Hinweis in Aktionen.
- Fix-Plan: Rollen aus Membership laden, UI-Disable nach Rollen/Status, Approval/Lock-UI ergänzen.

4) **Docs/FINAL_VERIFICATION**
- Befund: Nicht aktualisiert.
- Fix-Plan: Nach Funktionsergänzungen aktualisieren.
