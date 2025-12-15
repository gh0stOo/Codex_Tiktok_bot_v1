from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..auth import get_current_user, get_db
from ..authorization import assert_org_member
from .. import models

router = APIRouter()


@router.get("/{org_id}")
def usage_snapshot(org_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    assert_org_member(db, user, org_id)
    start = None
    totals = {}
    rows = db.query(models.UsageLedger.metric, models.func.count(models.UsageLedger.id)).filter(models.UsageLedger.organization_id == org_id).group_by(models.UsageLedger.metric).all()
    for metric, cnt in rows:
        totals[metric] = cnt
    active_jobs = (
        db.query(models.Job)
        .filter(models.Job.organization_id == org_id, models.Job.status.in_(["pending", "in_progress"]))
        .count()
    )
    totals["concurrent_jobs"] = active_jobs
    return {"usage": totals}
