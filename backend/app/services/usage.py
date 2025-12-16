from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from .. import models

DEFAULT_LIMITS = {
    "video_generation": 120,
    "publish_now": 120,
    "asr_minutes": 300,
    "storage_mb": 10240,
    "concurrent_jobs": 10,
}


class QuotaExceeded(Exception):
    pass


def log_usage(db: Session, organization_id: str, metric: str, amount: int = 1):
    entry = models.UsageLedger(organization_id=organization_id, metric=metric, amount=amount)
    db.add(entry)
    db.commit()
    return entry


def enforce_quota(db: Session, organization_id: str, metric: str, limit: int | None = None):
    limit = limit or DEFAULT_LIMITS.get(metric, DEFAULT_LIMITS["video_generation"])
    start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    # concurrency check special-case
    if metric == "concurrent_jobs":
        active = (
            db.query(models.Job)
            .filter(models.Job.organization_id == organization_id, models.Job.status.in_(["pending", "in_progress"]))
            .count()
        )
        total = active
    else:
        # FIX: Use sum(amount) instead of count() to correctly enforce quotas
        from sqlalchemy import func
        result = (
            db.query(func.sum(models.UsageLedger.amount))
            .filter(
                models.UsageLedger.organization_id == organization_id,
                models.UsageLedger.metric == metric,
                models.UsageLedger.created_at >= start,
            )
            .scalar()
        )
        total = result if result is not None else 0
    if total >= limit:
        raise QuotaExceeded(f"Quota exceeded for {metric}: {total}/{limit}")
