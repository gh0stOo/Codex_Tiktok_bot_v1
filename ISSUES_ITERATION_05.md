## Issues Iteration 05

1) **Storage Integration Partial**
- Befund: Storage abstraction vorhanden, aber signed URLs nicht im API/UI verfügbar; publish nutzt direkten Pfad (S3 Download fehlt).
- Fix-Plan: Add media proxy/signed URL endpoints; adjust publish to download from S3 if needed; integrate storage in frontend library previews.
- Risiko: Publish/preview scheitert bei S3 Backend.

2) **Orchestrator/Audit/Agents fehlend**
- Befund: ScriptSpec/repair/policy ergänzt, aber keine Audit-Trail-Persistenz, keine Agent-Module, kein OpenTelemetry.
- Fix-Plan: Add AIAudit table + logging; implement agents with Pydantic outputs; wire tracing.
- Risiko: Compliance/Nachvollziehbarkeit unzureichend.

3) **Kernfeatures weiterhin offen (TikTok publish/metrics, ASR/yt-dlp, Quotas, Frontend, Celery Tasks)**
- Befund: Große Teile des Projektplans fehlen.
- Fix-Plan: Nächste Iterationen nach IMPLEMENTATION_TASKS; priorisiere TikTok publish/metrics + Celery tasks + UI.
- Risiko: Akzeptanzkriterien noch weit entfernt.
