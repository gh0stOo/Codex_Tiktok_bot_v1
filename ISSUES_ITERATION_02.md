## Issues Iteration 02

1) **Tenant-Isolation noch unvollständig**
- Befund: org_id fehlt auf manchen Tabellen (plans/video_assets/jobs/metrics tokens etc. teils indirekt), kein globaler Query-Guard.
- Root Cause: Initiales Schema minimal.
- Fix-Plan: Schema-Revision für org_id auf allen Business-Tabellen + Alembic-Migration, Abfragen konsequent scope'n, ggf. session-bound org context.
- Risiko: Datenleck zwischen Tenants möglich bis umgesetzt.

2) **Frontend weiterhin Demo/Mock-getrieben**
- Befund: App.tsx enthält Mock-Credential/Transcribe Buttons, keine Auth-/Org-Flows laut Plan.
- Root Cause: UI bisher nur Demo-Tabs.
- Fix-Plan: Neuaufbau UI (auth/org switcher/calendar/queue/analytics/TikTok connect), Mocks entfernen, API-Anbindung an neue Endpoints.
- Risiko: UI nicht nutzbar für Akzeptanzkriterien.

3) **TikTok/Provider-Integrationen unvollständig**
- Befund: TikTok Client ohne refresh/publish/metrics Flows, Tokens teils unverschlüsselt; ASR/YouTube/LLM/Video-Pipeline fehlen.
- Root Cause: Nur Scaffold.
- Fix-Plan: Implementierung laut projektplan (OAuth2 refresh, upload direct/inbox, idempotency, metrics persist, ASR/yt-dlp/faster-whisper, OpenRouter orchestration); Feature-Flags mit klaren Fehlermeldungen wenn unkonfiguriert.
- Risiko: Akzeptanzkriterien unerfüllt, Compliance-Risiko bis fertig.

4) **Seeds/Docs/Makefile veraltet**
- Befund: Seed nutzt Mock-Credential, keine neuen Felder; README/Docs referenzieren Mocks; Makefile minimal.
- Root Cause: Legacy Demo Setup.
- Fix-Plan: Seed auf echte Flows (demo org/project/plan 30x3, metrics, credentials placeholder mit Verschlüsselung) umbauen; Docs/Checklist/Architecture aktualisieren; Makefile Targets ergänzen.
- Risiko: Onboarding/Verification erschwert.
