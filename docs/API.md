# API Quick Reference

Base URL: `http://localhost:8000`

## Auth
- `POST /auth/register` – `{email, password}` → user
- `POST /auth/login` – `{email, password}` → `{access_token}`
- `POST /auth/refresh` – `{access_token}` → new token

## Organizations & Projects
- `POST /orgs` – create org, auto-membership owner
- `GET /orgs` – list orgs for current user
- `POST /projects/{org_id}` – create project in org
- `GET /projects/{org_id}` – list projects

## Planning
- `POST /plans/generate/{project_id}` – create 30x3 calendar
- `GET /plans/calendar/{project_id}` – fetch slots (list of dates with slots)

## Production
- `POST /video/generate/{project_id}/{plan_id}` – generate assets via orchestrator; returns `VideoAsset`
- `POST /video/publish/{asset_id}` – publish via TikTok adapter (mock by default)

## Analytics
- `GET /analytics/metrics/{project_id}` – metrics list (mock-seeded when empty)

## Health
- `GET /health/` – `{status: "ok"}`

### Auth
Authenticate with `Authorization: Bearer <token>` from `/auth/login`.
