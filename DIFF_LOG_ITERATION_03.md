## Diff Log Iteration 03

**Geänderte/Neu hinzugefügte Dateien**
- backend/app/models.py — org_id Felder für Plan/VideoAsset ergänzt.
- backend/app/services/orchestrator.py — VideoAsset erzeugt nun organization_id.
- backend/app/routers/plans.py, video.py — org-id Set/Scope beim Anlegen/Generieren.
- migrations/versions/0003_org_scope.py — Migration für organization_id auf plans und video_assets inkl. Backfill.
- scripts/seed.py — entfernt Mock-Credential; legt Credential nur an, wenn echter OpenRouter-Key vorhanden, verschlüsselt via Fernet.

**Neue Endpoints/Queues/Tabellen**
- Tabellen-Änderung: plans und video_assets haben jetzt organization_id (FK auf organizations).

**Breaking Changes / Migration Notes**
- Migration 0003 erforderlich. Bestehende Clients unaffected; DB Schema erweitert. VideoAsset/Plan Erstellung benötigt projektspezifische org_id (wird serverseitig gesetzt).
