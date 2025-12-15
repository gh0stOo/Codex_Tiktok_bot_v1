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
celery.conf.task_default_retry_delay = 30
celery.conf.task_time_limit = 300
celery.conf.task_soft_time_limit = 240
celery.conf.task_acks_late = True
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
}


@celery.task(name="tasks.enqueue_due_plans")
def enqueue_due_plans():
    # placeholder: in real app would enqueue jobs for near-term slots
    return "ok"
