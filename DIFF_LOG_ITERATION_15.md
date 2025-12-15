## Diff Log Iteration 15

**Geänderte/Neu hinzugefügte Dateien**
- backend/app/tasks.py – Polling-Task für Publish-Status (Einzel/Broadcast), enqueue nach Publish.
- backend/app/celery_app.py – Beat-Schedule für Publish-Status-Polling.
- backend/app/providers/tiktok_official.py – get_video_status API.
- backend/app/routers/video.py – Publish-Status-Endpoint nutzt Tokens/Refresh.
- backend/app/routers/projects.py – Autopilot-Toggle Endpoint.
- frontend/src/App.tsx – Autopilot-Toggle im UI, Publish-Status-Button, Refresh von Status.

**Neue Endpoints/Queues/Tabellen**
- POST /projects/toggle/{project_id}?enabled=bool (Autopilot).
- GET /video/status/{asset_id} (TikTok Status).
- Celery Task: tasks.poll_publish_status (auch Beat alle 15min via "__broadcast__").

**Breaking Changes / Migration Notes**
- Keine Migrationen. Beat-Task pollt alle 15 Minuten alle Assets im Status pending/processing/published.
