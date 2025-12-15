## Issues Iteration 14

1) **TikTok Inbox/Status-Polling weiter rudimentär**
- Befund: Status-API existiert, aber kein Hintergrund-Polling oder Inbox-Fallback.
- Fix-Plan: Celery-Task für Status-Polling, Inbox-Upload-Pfad ergänzen, UI-Status-Anzeige verfeinern.

2) **Quoten/Usage fehlende Metriken**
- Befund: Nur video_generation/publish_now geloggt; keine Limits für Storage/ASR/Concurrency.
- Fix-Plan: Quotenmatrix erweitern, Enforcement in Tasks, Anzeige im UI.

3) **Auth/RBAC/Autopilot im Frontend fehlt**
- Befund: Logout vorhanden, aber kein Refresh/Logout-API-Call, keine Rollenprüfung, keine Autopilot/Approval-Toggles.
- Fix-Plan: Session-API nutzen, UI-Gates per Rolle, Autopilot-Switch hinzufügen.

4) **Docs/FINAL_VERIFICATION weiterhin offen**
- Befund: Nicht aktualisiert.
- Fix-Plan: Nach Abschluss der obigen Punkte aktualisieren.
