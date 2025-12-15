## Issues Iteration 08

1) **Jobs asynchron, aber kein Status-Polling/Frontend**
- Befund: API liefert job_id, aber kein Endpoint zum Polling/Listing mit JobRun Details; Frontend fehlt.
- Fix-Plan: Add job status endpoint including JobRuns; wire frontend queue view.
- Risiko: Nutzer sieht keine Ergebnisse.

2) **Publish Idempotency/Status begrenzt**
- Befund: Idempotency-Key hinzugefügt, aber keine Status-Polling gegen TikTok, kein Inbox-Fallback, kein Approval-Gate.
- Fix-Plan: Add publish task to persist TikTok response/status, support inbox upload fallback, approval/lock checks.
- Risiko: Doppelposts/Unklare Status.

3) **Metrics & Storage**
- Befund: Metrics fetch task existiert, aber Analytics-GET macht weiterhin Synch-Fetch; Storage Streaming ohne Range.
- Fix-Plan: Remove sync fetch or gate behind flag; range-support oder nur signed URLs im Frontend.
- Risiko: Ineffizient/Memory-Risiko.

4) **Große Funktionsblöcke weiterhin offen**
- Frontend (Auth/Org/Calendar/Queue/Analytics), RAG/Agents, Policy/Quotas, Observability, API Docs/FINAL_VERIFICATION.
- Fix-Plan: Weiter gemäß IMPLEMENTATION_TASKS, priorisiere Frontend + TikTok Publish/Analytics Stabilität + Quotas/Policy.
