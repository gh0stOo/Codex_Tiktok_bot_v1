## Issues Iteration 07

1) **Publish flow still limited**
- Befund: Uses stored tokens but lacks idempotency keys, status polling, inbox fallback, approval gates, and JobRun tracking.
- Fix-Plan: Add publish task with idempotency_key, store TikTok response/status, add approval/lock checks, persist JobRun.
- Risiko: Potential duplicate uploads, missing audit.

2) **Streaming not range-aware**
- Befund: `/video/assets/{id}/stream` loads full file into memory.
- Fix-Plan: Implement range streaming or require signed URL usage in frontend.
- Risiko: Large files may exhaust memory.

3) **Celery tasks not fully wired**
- Befund: API still runs publish/generate synchronously; tasks not enqueued; no DLQ/backoff jitter; beat schedule placeholder.
- Fix-Plan: Wire routes to enqueue tasks; add JobRun + retry/backoff/jitter; DLQ queue; beat for metrics.
- Risiko: Background processing absent.

4) **Frontend & remaining plan features**
- Befund: UI still demo; quotas/policy/RAG/agents/logging/analytics gaps persist.
- Fix-Plan: Continue per IMPLEMENTATION_TASKS; next focus TikTok publish robustness + job pipeline + frontend scaffolding.
