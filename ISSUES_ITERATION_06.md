## Issues Iteration 06

1) **Signed URLs/Streaming limited**
- Befund: Streaming endpoint reads whole file into memory; no range support; S3 signed URLs not exposed separately for frontend.
- Fix-Plan: Add HEAD/range streaming, expose signed URLs via API responses and frontend consumption.
- Risiko: Large files could impact memory.

2) **TikTok publish/metrics still incomplete**
- Befund: Publish still requires caller-provided access_token/open_id; should use stored encrypted tokens + refresh automatically; metrics parsing minimal.
- Fix-Plan: Enhance publish path to pull tokens from OAuthToken, handle refresh, persist job status/metrics; add policy/idempotency.
- Risiko: Akzeptanzkriterien für TikTok nicht erfüllt.

3) **Celery tasks placeholder**
- Befund: Tasks exist but not wired from API; no DLQ/backoff jitter; no JobRun persistence.
- Fix-Plan: Wire tasks to enqueue from routes; add retry/backoff/jitter, JobRun table, beat schedules.
- Risiko: Background flows not functional.

4) **Observability/Quotas/UI remain undone**
- Befund: Structured logs, quotas, frontend, RAG/agents untouched.
- Fix-Plan: Continue per IMPLEMENTATION_TASKS.
