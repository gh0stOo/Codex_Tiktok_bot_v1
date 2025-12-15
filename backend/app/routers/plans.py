from datetime import date, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from .. import models, schemas
from ..auth import get_current_user, get_db
from ..authorization import assert_project_member, assert_plan_member

router = APIRouter()


@router.post("/generate/{project_id}", response_model=list[schemas.PlanOut])
def generate_calendar(project_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    project = assert_project_member(db, user, project_id)
    start_date = date.today()
    created = []
    for day in range(30):
        for slot in range(1, 4):
            existing = (
                db.query(models.Plan)
                .filter(
                    models.Plan.project_id == project_id,
                    models.Plan.slot_date == start_date + timedelta(days=day),
                    models.Plan.slot_index == slot,
                )
                .first()
            )
            if existing:
                continue
            plan = models.Plan(
                organization_id=project.organization_id,
                project_id=project_id,
                slot_date=start_date + timedelta(days=day),
                slot_index=slot,
                status="scheduled",
            )
            db.add(plan)
            created.append(plan)
    db.commit()
    return db.query(models.Plan).filter(models.Plan.project_id == project_id).all()


@router.get("/calendar/{project_id}", response_model=list[schemas.CalendarSlot])
def get_calendar(project_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    project = assert_project_member(db, user, project_id)
    plans = db.query(models.Plan).filter(models.Plan.project_id == project_id).all()
    by_date = {}
    for plan in plans:
        by_date.setdefault(plan.slot_date, []).append(plan)
    return [schemas.CalendarSlot(date=k, slots=v) for k, v in sorted(by_date.items())]


@router.post("/approve/{plan_id}")
def approve_plan(plan_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    plan = assert_plan_member(db, user, plan_id, roles=["owner", "admin", "editor"])
    plan.approved = True
    db.commit()
    return {"status": "approved"}


@router.post("/lock/{plan_id}")
def lock_plan(plan_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    plan = assert_plan_member(db, user, plan_id, roles=["owner", "admin"])
    plan.locked = True
    db.commit()
    return {"status": "locked"}
