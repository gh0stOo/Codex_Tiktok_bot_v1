## Issues Iteration 01

1) **Fehlende Kernfunktionen (Auth/RBAC/Tenant/Quotas/Workflows)**
- Befund: Projekt deckt projektplan.md kaum ab (keine RBAC-Enforcement, keine Quotas, keine Plan/Publish-Workflows, keine Agents/RAG, keine realen Provider).
- Root Cause: Vorheriger Code war Mock-getriebenes Demo-System.
- Fix-Plan: Folge IMPLEMENTATION_TASKS.md sequenziell; nächste Iterationen mit Auth/RBAC/Tenant-Enforcement, Secrets/Storage, Provider-Integration.
- Risiko: Hoher Umfang; mehrere Iterationen erforderlich.

2) **Mock-Pfade im Produktivcode (Verstoß gegen R1)**
- Befund: Mock Provider/Transcribe Buttons/Docs im Hauptcodepfad (Frontend, Docs, README).
- Root Cause: Demo-orientierter Aufbau.
- Fix-Plan: Mocks in tests/ verlagern, produktive Adapter implementieren, UI kennzeichnet unkonfigurierte Provider statt Fake-Daten.
- Risiko: Compliance-Blocker bis beseitigt.

3) **TikTok Integration nicht umgesetzt**
- Befund: Kein vollständiger OAuth/Publish/Metric Flow; Tokens unverschlüsselt in Teilen.
- Root Cause: Nur Scaffold.
- Fix-Plan: Offizielle Endpoints implementieren, Token-Verschlüsselung via Fernet, Publisher mit Idempotency/Rate-Limit + Status Polling, Metrics speichern; UI-Connect-Flow.
- Risiko: Hoher Implementierungsaufwand; abhängig von Keys (Feature-Flag + klare Fehlermeldung bei fehlender Konfiguration).

4) **Observability/Resilience nicht vorhanden**
- Befund: Keine strukturierten Logs, keine Traces, keine Retry/Backoff/Idempotenz, kein DLQ.
- Root Cause: Minimaler Scaffold.
- Fix-Plan: Logging/Tracing Middleware einführen, Celery Retry/Backoff, JobRun/DLQ-Tabellen, Rate Limits.
- Risiko: Debugbarkeit/Compliance eingeschränkt bis umgesetzt.

Nicht-steckenbleiben-Mechanismus: Falls Blockade >30min bei Provider-Integration, zwei Wege dokumentieren (A minimal Feature-Flag + klare Fehlermeldung, B robuste Implementierung) und sofort umsetzen.
