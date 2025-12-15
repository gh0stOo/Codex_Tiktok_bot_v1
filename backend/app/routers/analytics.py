from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models
from ..auth import get_current_user, get_db
from ..authorization import assert_project_member
from ..providers.tiktok_official import TikTokClient
from ..security import decrypt_secret
from ..config import get_settings
from ..celery_app import celery

settings = get_settings()

router = APIRouter()


@router.get("/metrics/{project_id}")
def list_metrics(project_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    project = assert_project_member(db, user, project_id)
    metrics = (
        db.query(models.Metric)
        .filter(models.Metric.project_id == project_id)
        .order_by(models.Metric.created_at.desc())
        .all()
    )
    return {"metrics": [{"metric": m.metric, "value": m.value, "created_at": m.created_at} for m in metrics]}


@router.post("/metrics/{project_id}/refresh")
def refresh_metrics(project_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    project = assert_project_member(db, user, project_id)
    idem = f"metrics:{project_id}"
    existing = (
        db.query(models.Job)
        .filter(models.Job.organization_id == project.organization_id, models.Job.idempotency_key == idem, models.Job.type == "fetch_metrics")
        .order_by(models.Job.created_at.desc())
        .first()
    )
    if existing and existing.status in ("in_progress", "pending"):
        return {"status": existing.status, "job_id": existing.id}
    job = models.Job(
        organization_id=project.organization_id,
        project_id=project.id,
        type="fetch_metrics",
        status="pending",
        idempotency_key=idem,
        payload=project_id,
    )
    db.add(job)
    db.commit()
    celery.send_task("tasks.fetch_metrics", args=[job.id, project_id])
    return {"status": "queued", "job_id": job.id}
