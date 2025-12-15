## Issues Iteration 11

1) **Frontend weiterhin unvollständig**
- Befund: Neue UI-Grundstruktur vorhanden, aber keine echten Auth-Flows (auto-login demo), keine Video-Asset-Liste (Backend-Endpoint fehlt), keine Signed-URL-Previews, keine Approval/Lock/Confidence Felder.
- Fix-Plan: Backend-Endpoints für Assets/Plans ergänzen, UI für Previews/Approvals/Confidence bauen, echte Auth/Session implementieren.

2) **TikTok Publish/Status**
- Befund: Publish speichert Response, aber kein Status-Polling/Inbox/Approval-Gates; Token aus Vault, aber kein UI-Connect-Flow-Ende.
- Fix-Plan: Publish-Status persistieren, Inbox-Fallback, Approval/Lock prüfen, Frontend-Connect-Flow.

3) **Quotas/Policy/RAG/Agents/Observability**
- Befund: Keine Quoten/Rate-Limits/Policy-Engine, keine RAG/Agents, keine strukturierten Logs/OTel.
- Fix-Plan: Implementieren gemäß Plan.

4) **Tests/Doku**
- Befund: Keine Tests, API-Doku/FINAL_VERIFICATION offen.
- Fix-Plan: Unit/Integration/E2E hinzufügen, Doku aktualisieren.
