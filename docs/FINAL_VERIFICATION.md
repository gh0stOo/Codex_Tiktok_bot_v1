# Final Verification (to execute when features complete)

1) **Start Stack**
   - `docker compose -f infra/docker-compose.yml up --build -d`
   - `docker compose -f infra/docker-compose.yml exec backend sh -c "cd /app/migrations && PYTHONPATH=/app alembic upgrade head"`
   - Health: `curl http://localhost:8000/health/readyz`

2) **Seed Demo**
   - `python scripts/seed.py` (or `make seed`) — creates demo org/user/project/plan (30x3).

3) **Login**
   - Frontend at `http://localhost:5173`; login with demo credentials from README (adjust if changed in .env).

4) **Plan Generation**
   - Trigger month plan (30x3) via UI or `POST /plans/generate/{project_id}`; verify DB rows scoped to org.

5) **Asset Pipeline**
   - Run "Generate Assets" for a plan slot (UI) or `POST /video/generate/{project_id}/{plan_id}`; expect `final.mp4` + `thumbnail.jpg` under tenant prefix in storage.

6) **TikTok Connect & Publish**
   - Start OAuth: `/tiktok/oauth/start?org_id=...`, complete callback; tokens stored encrypted.
   - Publish Now: UI button or `POST /video/publish/{asset_id}` with TikTok access/open_id; status -> published; idempotency respected.

7) **Metrics Fetch**
   - Run metrics job (UI or `GET /analytics/metrics/{project_id}`); metrics persisted for slots.

8) **Analytics/Library/Queue**
   - UI: Calendar shows 30x3, Library previews video/thumb (signed URLs), Queue/Logs display job history, Analytics charts show metrics, Credentials/Usage page reflects quotas.

Record any failures with logs; rerun after fixes until all steps pass.
