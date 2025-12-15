## Issues Iteration 09

1) **Docker Compose Pull-Probleme (Registry)**
- Befund: `docker compose up` bricht bei `minio/minio` bzw. `redis:7` mit „unexpected end of JSON input“ ab; `docker pull` hängt. Compose lief früher, aktuell Registry/Daemon problematisch.
- Fix-Plan: Prüfen Docker/Netz, ggf. Registry-Mirror; MinIO bereits auf optionales Profil gesetzt, aber Redis-Pull blockiert weiter. Wiederholen, sobald Zugriff möglich.
- Risiko: Compose-Verification blockiert, Services nicht startbar im Moment.

2) **Job-Polling/UI fehlen**
- Befund: API liefert job_id und Job/Run Endpoints, aber kein Frontend/Queue-Polling.
- Fix-Plan: Frontend Queue-View implementieren; ggf. SSE/Polling; Backend Filter/Status-Endpoint optimieren.

3) **Publish/Inbox/Status**
- Befund: Keine Status-Persistenz von TikTok-Response, kein Inbox-Fallback, Approval-Gates fehlen.
- Fix-Plan: Persist publish_result, status polling/idempotency, optional inbox upload; Approval/Lock Checks vor Publish.

4) **Metrics/Streaming**
- Befund: GET Metrics nur persistiert (ok), Refresh per Task; kein Range-Streaming, kein Frontend-Verbrauch von Signed URLs.
- Fix-Plan: Range-Support oder Frontend-Signed-URL Nutzung; UI Anpassung.

5) **Großer Restumfang**
- Frontend komplett, Quotas/Policy/RAG/Agents/Observability/API-Doku/FINAL_VERIFICATION bleiben offen.
