## Diff Log Iteration 02

**Geänderte/Neu hinzugefügte Dateien (Auswahl)**
- backend/app/auth.py, backend/app/routers/auth.py — Session-basierte JWT/Refresh-Rotation, Logout, Password-Reset/Verify-Skaffold.
- backend/app/models.py — neue Tabellen Session/PasswordReset, User-Verification-Felder.
- backend/app/authorization.py (neu) — RBAC/Membership-Guards.
- backend/app/routers/projects.py, plans.py, video.py, credentials.py, prompts.py, knowledge.py, jobs.py, analytics.py, tiktok.py — Tenant/RBAC-Checks, TikTok OAuth State mit Org-ID, Entfernung von Mock-Pfaden.
- backend/app/config.py, schemas.py — neue Settings, TokenPair-Schema.
- backend/app/routers/youtube.py — Mock-Response entfernt, liefert 503 bis echte ASR vorhanden.
- infra/docker-compose.yml — USE_MOCK_PROVIDERS auf false.
- .env.example — neue Settings, korrigierte TikTok Redirect URI.
- migrations/versions/0002_auth_sessions.py (neu) — Sessions + PasswordResets + User-Verifikationsfelder.
- backend/tests/provider_mocks.py (neu) — Mocks in tests verlagert; app/providers/mocks.py entfernt.

**Neue Endpoints/Queues/Tabellen**
- Endpoints: /auth/logout, /auth/password/reset/request, /auth/password/reset/confirm, /auth/verify/request, /auth/verify/confirm.
- Tabellen: sessions, password_resets; User um email_verified/verification_token/verification_sent_at ergänzt.

**Breaking Changes / Migration Notes**
- Bestehende User benötigen Migration 0002 (setzt email_verified default false). Refresh Tokens jetzt sessions-gebunden; Clients müssen refresh_token speichern. TikTok OAuth Start erwartet org_id in state.
