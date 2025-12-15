from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas
from ..auth import get_current_user, get_db
from ..authorization import assert_project_member

router = APIRouter()


@router.get("/{project_id}", response_model=dict)
def list_jobs(project_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    project = assert_project_member(db, user, project_id)
    jobs = db.query(models.Job).filter(models.Job.project_id == project_id).order_by(models.Job.created_at.desc()).all()
    return {"jobs": [schemas.JobOut.model_validate(j) for j in jobs]}


@router.get("/detail/{job_id}", response_model=schemas.JobOut)
def job_detail(job_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    assert_project_member(db, user, job.project_id)
    return job
