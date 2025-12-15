from celery import shared_task
from sqlalchemy.orm import Session
from datetime import datetime
import anyio
from .db import SessionLocal
from . import models
from .services.orchestrator import Orchestrator
from .providers.tiktok_official import TikTokClient
from .security import decrypt_secret, encrypt_secret
from .config import get_settings

settings = get_settings()


def _db() -> Session:
    return SessionLocal()


def _job_run(db: Session, job: models.Job, status: str, message: str | None = None):
    run = models.JobRun(job_id=job.id, status=status, message=message)
    db.add(run)
    db.commit()


@shared_task(bind=True, name="tasks.generate_assets")
def generate_assets_task(self, job_id: str, project_id: str, plan_id: str):
    db = _db()
    try:
        job = db.query(models.Job).filter(models.Job.id == job_id).first()
        project = db.query(models.Project).filter(models.Project.id == project_id).first()
        plan = db.query(models.Plan).filter(models.Plan.id == plan_id).first()
        if not job or not project or not plan:
            return "missing entities"
        orchestrator = Orchestrator()
        _job_run(db, job, "in_progress")
        asset = anyio.run(orchestrator.generate_assets, db, project, plan)
        # update plan status for visibility in calendar
        plan.status = "assets_generated"
        db.add(plan)
        job.status = "completed"
        db.add(job)
        _job_run(db, job, "completed", message=asset.id)
        db.commit()
        return asset.id
    except Exception as exc:
        if db:
            if "job" in locals() and job:
                job.status = "failed"
                db.add(job)
                db.commit()
                _job_run(db, job, "failed", message=str(exc))
        raise self.retry(exc=exc, countdown=30, max_retries=3)
    finally:
        db.close()


@shared_task(bind=True, name="tasks.publish_now")
def publish_now_task(self, job_id: str, asset_id: str, access_token: str, open_id: str, use_inbox: bool = False):
    db = _db()
    try:
        job = db.query(models.Job).filter(models.Job.id == job_id).first()
        asset = db.query(models.VideoAsset).filter(models.VideoAsset.id == asset_id).first()
        if not job or not asset:
            return "missing entities"
        orchestrator = Orchestrator()
        _job_run(db, job, "in_progress")
        result = anyio.run(orchestrator.publish_now, asset, access_token, open_id, use_inbox=use_inbox)
        asset.status = "published"
        asset.publish_response = str(result)
        db.add(asset)
        # keep plan in sync
        if asset.plan_id:
            plan = db.query(models.Plan).filter(models.Plan.id == asset.plan_id).first()
            if plan:
                plan.status = "published"
                db.add(plan)
        job.status = "completed"
        db.add(job)
        db.commit()
        _job_run(db, job, "completed", message=str(result))
        # enqueue status polling
        celery = __import__("app.celery_app", fromlist=["celery"]).celery
        celery.send_task("tasks.poll_publish_status", args=[asset.id])
        return "ok"
    except Exception as exc:
        if job:
            job.status = "failed"
            db.add(job)
            db.commit()
            _job_run(db, job, "failed", message=str(exc))
        raise self.retry(exc=exc, countdown=30, max_retries=3)
    finally:
        db.close()


@shared_task(bind=True, name="tasks.fetch_metrics")
def fetch_metrics_task(self, job_id: str, project_id: str):
    db = _db()
    try:
        job = db.query(models.Job).filter(models.Job.id == job_id).first()
        project = db.query(models.Project).filter(models.Project.id == project_id).first()
        if not job or not project:
            return "missing entities"
        _job_run(db, job, "in_progress")
        tokens = (
            db.query(models.OAuthToken, models.SocialAccount)
            .join(models.SocialAccount, models.OAuthToken.social_account_id == models.SocialAccount.id)
            .filter(models.SocialAccount.organization_id == project.organization_id)
            .first()
        )
        if not tokens:
            raise RuntimeError("TikTok account not connected")
        token_row, account = tokens
        access = decrypt_secret(token_row.access_token, settings.fernet_secret)
        refresh = decrypt_secret(token_row.refresh_token, settings.fernet_secret)
        if not access:
            raise RuntimeError("Missing access token")
        client = TikTokClient()
        resp = anyio.run(client.get_metrics, access, account.handle)
        videos = resp.get("data", {}).get("videos", [])
        for v in videos:
            stats = v.get("statistics", {}) or {}
            metric = models.Metric(
                organization_id=project.organization_id,
                project_id=project_id,
                plan_id=None,
                metric="views",
                value=stats.get("view_count", 0),
                open_id=account.handle,
            )
            db.add(metric)
        job.status = "completed"
        db.add(job)
        db.commit()
        _job_run(db, job, "completed", message=f"videos={len(videos)}")
        return "ok"
    except Exception as exc:
        if job:
            job.status = "failed"
            db.add(job)
            db.commit()
            _job_run(db, job, "failed", message=str(exc))
        raise self.retry(exc=exc, countdown=30, max_retries=3)
    finally:
        db.close()


@shared_task(name="tasks.enqueue_due_plans")
def enqueue_due_plans():
    # placeholder: would identify near-term plan slots and enqueue generation
    return "ok"


@shared_task(bind=True, name="tasks.poll_publish_status")
def poll_publish_status(self, asset_id: str):
    db = _db()
    try:
        assets: list[models.VideoAsset]
        if asset_id == "__broadcast__":
            assets = db.query(models.VideoAsset).filter(models.VideoAsset.status.in_(["published", "pending", "processing"])).all()
        else:
            asset = db.query(models.VideoAsset).filter(models.VideoAsset.id == asset_id).first()
            assets = [asset] if asset else []
        if not assets:
            return "missing asset"
        updated = 0
        for asset in assets:
            project = db.query(models.Project).filter(models.Project.id == asset.project_id).first()
            if not project:
                continue
            tokens = (
                db.query(models.OAuthToken, models.SocialAccount)
                .join(models.SocialAccount, models.OAuthToken.social_account_id == models.SocialAccount.id)
                .filter(models.SocialAccount.organization_id == project.organization_id, models.SocialAccount.platform == "tiktok")
                .first()
            )
            if not tokens:
                continue
            token_row, account = tokens
            access = decrypt_secret(token_row.access_token, settings.fernet_secret)
            refresh = decrypt_secret(token_row.refresh_token, settings.fernet_secret)
            if not access:
                continue
            client = TikTokClient()
            # refresh if needed
            if token_row.expires_at and token_row.expires_at < datetime.utcnow() + timedelta(minutes=5):
                if refresh:
                    resp = anyio.run(client.refresh, refresh)
                    new_access = resp.get("data", {}).get("access_token")
                    if new_access:
                        access = new_access
            video_id = None
            if asset.publish_response:
                try:
                    import json
                    parsed = json.loads(asset.publish_response.replace("'", '"'))
                    video_id = parsed.get("data", {}).get("video_id") or parsed.get("video_id")
                except Exception:
                    pass
            if not video_id:
                continue
            resp = anyio.run(client.get_video_status, access, account.handle, video_id)
            asset.publish_response = str(resp)
            status_val = resp.get("data", {}).get("status", "unknown")
            asset.status = status_val
            db.add(asset)
            updated += 1
        db.commit()
        return f"updated={updated}"
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60, max_retries=3)
    finally:
        db.close()
