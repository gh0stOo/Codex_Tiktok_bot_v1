## Issues Iteration 12

1) **Große Funktionslücken (Quotas/Agents/RAG/Autopilot)**
- Befund: Quoten/Plans/Usage-Enforcement, Agents, RAG/Knowledge, Autopilot/Approval-Gates, Observability weiterhin nicht umgesetzt.
- Root Cause: Priorisierung auf UI/Asset-Flows, begrenzte Zeit.
- Fix-Plan: Implementationsplan aus projektplan.md Schritt für Schritt: UsageLedger/Enforcement mit Policies, Agent-Module und RAG-Speicher, Autopilot- und Approval-Gates serverseitig, Logging/OTel ergänzen.
- Risiko: Compliance/Scope; ohne Quoten kein Schutz vor Übernutzung.

2) **TikTok Publish Status/Inbox/Connect UX**
- Befund: Kein Status-Polling oder Inbox-Fallback, Connect-Flow endet nicht im UI; Publish erfolgt ohne Approval-Gate.
- Root Cause: Backend/Frontend-Flow nur minimal.
- Fix-Plan: Status-Polling/Callback persistieren, Inbox-Fallback-Branch, Approval-Gate vor Publish, UI-Feedback für Connect/Status.
- Risiko: Fehlende Transparenz bei Publishes; mögliche API-Fehler unbemerkt.

3) **Frontend Auth/Session und RBAC unvollständig**
- Befund: Auto-Login Demo, kein Refresh/Logout, keine RBAC-Steuerung; Autopilot-Toggles fehlen.
- Root Cause: Zeitfokus auf Library/Calendar UI.
- Fix-Plan: Echte Login/Session-Verwaltung mit Refresh, Logout-Button, Guarding per Rolle, Autopilot/Approval-Toggles und Usage-Widget ergänzen.
- Risiko: Bedienbarkeit eingeschränkt; kein Security-Gate im UI.

4) **Dokumentation/Final Verification offen**
- Befund: FINAL_VERIFICATION unvollständig, README/API nicht aktualisiert für neue Endpoints.
- Root Cause: Umsetzung noch in Arbeit.
- Fix-Plan: FINAL_VERIFICATION mit Schritt-für-Schritt Flow füllen; README/API erweitern; CHANGELOG fortführen.
- Risiko: Onboarding/Übergabe erschwert.
