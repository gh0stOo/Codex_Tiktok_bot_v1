## Issues Iteration 13

1) **TikTok Status/Inbox weiterhin offen**
- Befund: Publish-Gate ergänzt, aber kein Status-Polling, keine Inbox-Fallbacks.
- Fix-Plan: Polling-Task/API ergänzen, Publish-Response parse/persist, Inbox-Upload-Pfad bauen.

2) **Quoten weiter rudimentär**
- Befund: Logging für video_generation/publish_now, aber keine Limits per Plan/ASR/Storage oder concurrency.
- Fix-Plan: Quotenmatrix erweitern, Enforcement in Tasks, Dashboard-Anzeige.

3) **Frontend Auth/RBAC/Autopilot fehlt**
- Befund: Logout hinzugefügt, aber kein Refresh/Logout-API, keine RBAC-Guarding/Autopilot-Toggles.
- Fix-Plan: Session-Handling und UI-Gates nachziehen, Autopilot/Approval-Schalter ergänzen.

4) **Docs/FINAL_VERIFICATION unverändert**
- Befund: Noch nicht aktualisiert für neue Gates/Endpoints.
- Fix-Plan: Nach Umsetzung ergänzen.
