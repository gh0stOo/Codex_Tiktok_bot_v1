import os
from celery import Celery
from .config import get_settings

settings = get_settings()

celery = Celery(
    "codex",
    broker=settings.broker_url,
    backend=settings.redis_url,
)
celery.autodiscover_tasks(["app.tasks"])

# Task configuration with exponential backoff
celery.conf.task_default_retry_delay = 30
celery.conf.task_time_limit = 300
celery.conf.task_soft_time_limit = 240
celery.conf.task_acks_late = True
celery.conf.broker_connection_retry_on_startup = True

# Exponential backoff configuration
celery.conf.task_retry_backoff = True
celery.conf.task_retry_backoff_max = 600  # Max 10 minutes
celery.conf.task_retry_jitter = True  # Add randomness to prevent thundering herd

# Dead Letter Queue configuration
celery.conf.task_reject_on_worker_lost = True
celery.conf.task_default_queue = "default"
celery.conf.task_default_exchange = "default"
celery.conf.task_default_routing_key = "default"
celery.conf.task_routes = {
    "tasks.*": {"queue": "default"},
}
# DLQ queue for failed tasks after max retries
celery.conf.task_default_delivery_mode = "persistent"
celery.conf.beat_schedule = {
    "check-calendar": {
        "task": "tasks.enqueue_due_plans",
        "schedule": 3600,
    },
    "poll-publish-status": {
        "task": "tasks.poll_publish_status",
        "schedule": 900,
        "args": ("__broadcast__",),
    },
    "refresh-tokens": {
        "task": "tasks.refresh_expiring_tokens",
        "schedule": 1800,  # Every 30 minutes
    },
}


@celery.task(name="tasks.enqueue_due_plans")
def enqueue_due_plans():
    from datetime import date, timedelta
    from .db import SessionLocal
    from . import models
    from .celery_app import celery
    
    db = SessionLocal()
    try:
        # Find plans that are due in the next 24 hours and need assets generated
        tomorrow = date.today() + timedelta(days=1)
        due_plans = (
            db.query(models.Plan)
            .join(models.Project)
            .filter(
                models.Plan.slot_date <= tomorrow,
                models.Plan.slot_date >= date.today(),
                models.Plan.status == "scheduled",
                models.Plan.approved == True,
                models.Project.autopilot_enabled == True,
            )
            .all()
        )
        
        enqueued = 0
        for plan in due_plans:
            # Check if job already exists
            idem = f"gen:{plan.id}"
            existing = (
                db.query(models.Job)
                .filter(
                    models.Job.organization_id == plan.organization_id,
                    models.Job.idempotency_key == idem,
                    models.Job.type == "generate_assets",
                )
                .first()
            )
            if existing:
                continue
            
            # Check if asset already exists
            existing_asset = (
                db.query(models.VideoAsset)
                .filter(models.VideoAsset.plan_id == plan.id)
                .first()
            )
            if existing_asset:
                continue
            
            # Create job
            job = models.Job(
                organization_id=plan.organization_id,
                project_id=plan.project_id,
                type="generate_assets",
                status="pending",
                payload=str(plan.id),
                idempotency_key=idem,
            )
            db.add(job)
            db.commit()
            db.refresh(job)
            
            # Enqueue task
            celery.send_task("tasks.generate_assets", args=[job.id, plan.project_id, plan.id])
            enqueued += 1
        
        return f"enqueued={enqueued}"
    except Exception as e:
        if db:
            db.rollback()
        raise
    finally:
        if db:
            db.close()
