## Issues Iteration 03

1) **Tenant-Scope noch nicht vollständig durchgezogen**
- Befund: org_id jetzt auf plans/video_assets, aber Abfragen/Modelle für Jobs/Metrics/Usage/etc. benötigen globale Guard/Middleware; kein per-request org-context.
- Root Cause: Schrittweise Nachrüstung.
- Fix-Plan: Introduce request-scoped org context + query filters; audit remaining models/routes; add constraints/indices.
- Risiko: Potenzielle Querzugriffe bei fehlerhaften Parametern.

2) **Docs/Checklist/README weiterhin Mock-/Legacy-Inhalte**
- Befund: docs/CHECKLIST.md, README referenzieren Mock-Provider und erfüllen nicht R1.
- Root Cause: Noch nicht aktualisiert.
- Fix-Plan: Überarbeiten der Dokumente, Entfernen Mock-Hinweise, neue FINAL_VERIFICATION.md.
- Risiko: Onboarding/Compliance Unklarheit.

3) **Frontend/Workflows weiter offen**
- Befund: UI unverändert (Demo-Tabs), keine Auth/Org/Calendar/Queue/Analytics laut Plan.
- Root Cause: Noch nicht umgesetzt.
- Fix-Plan: Neuaufbau UI nach Projektplan mit shadcn/Tailwind und echter API-Anbindung.
- Risiko: Akzeptanzkriterien nicht erreichbar bis umgesetzt.

4) **Provider/Jobs/Quota/Observability fehlen**
- Befund: TikTok Publish/Metrics, OpenRouter Orchestrator mit Repair Loop, ASR/yt-dlp, Celery Tasks, Budgets, structured logging noch nicht umgesetzt.
- Root Cause: In nachfolgenden Iterationen einplanen.
- Fix-Plan: Implementations-Taktung gemäß IMPLEMENTATION_TASKS.md, jeweils mit Tests/Beweisen.
- Risiko: Hoher Restumfang.
