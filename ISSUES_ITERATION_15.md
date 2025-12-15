## Issues Iteration 15

1) **TikTok Inbox-Fallback fehlt**
- Befund: Status-Polling existiert, aber kein Inbox-Upload-Fallback für Policies/Audit.
- Fix-Plan: Upload-Pfad für Inbox ergänzen, Feature-Flag im Publish nutzen.

2) **Quoten/Usage unvollständig**
- Befund: Nur video_generation/publish_now; keine Limits für Storage/ASR/Concurrency.
- Fix-Plan: Quotenmatrix und Enforcement erweitern, UI-Anzeige ergänzen.

3) **Frontend Auth/RBAC/Approval/Autopilot UI teils roh**
- Befund: Autopilot-Toggle da, aber keine RBAC-Gates, kein Approval-Gate Feedback, kein Refresh/Logout-API Call.
- Fix-Plan: Session-Endpunkte nutzen, Rollen-Checks im UI, Approval/Usage Widgets.

4) **Docs/FINAL_VERIFICATION weiterhin offen**
- Befund: Nicht aktualisiert.
- Fix-Plan: Nach Umsetzung der oben genannten Punkte ergänzen.
