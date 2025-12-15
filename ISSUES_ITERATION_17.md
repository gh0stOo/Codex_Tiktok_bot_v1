## Issues Iteration 17

1) **Inbox-Fallback Validierung**
- Befund: use_inbox Flag vorhanden, aber API-Formate unbekannt; keine UI-Option.
- Fix-Plan: UI-Schalter hinzufügen, Fehlerbilder dokumentieren; serverseitig Feature-Flag nur aktivieren, wenn erlaubt.

2) **Usage Enforcement/Anzeige**
- Befund: Usage-Widget zeigt nur Rohwerte; Enforcement für Storage/ASR/Concurrency nur teilweise (kein ASR/Storage in Tasks).
- Fix-Plan: ASR/Storage/Concurrency Checks in Tasks, UI-Balken/Limit-Anzeige.

3) **RBAC/Approval UX**
- Befund: Keine Rollenabfrage im Frontend, Approval/Lock-Hinweise minimal.
- Fix-Plan: Membership-Rollen liefern, Buttons disable per Rolle/Status.

4) **Docs/FINAL_VERIFICATION offen**
- Befund: Nicht aktualisiert.
- Fix-Plan: Nach Ergänzungen aktualisieren.
