from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas
from ..auth import get_current_user, get_db
from ..authorization import assert_project_member

router = APIRouter()


@router.get("/{project_id}", response_model=dict)
def list_jobs(project_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    project = assert_project_member(db, user, project_id)
    # Hole Jobs für Projekt UND org-level Jobs (z.B. Transcription ohne project_id)
    project_jobs = db.query(models.Job).filter(models.Job.project_id == project_id).all()
    org_jobs = db.query(models.Job).filter(
        models.Job.organization_id == project.organization_id,
        models.Job.project_id.is_(None)  # Org-level Jobs ohne Projekt
    ).all()
    # Kombiniere und sortiere nach created_at
    all_jobs = sorted(project_jobs + org_jobs, key=lambda j: j.created_at, reverse=True)
    return {"jobs": [schemas.JobOut.model_validate(j) for j in all_jobs]}


@router.get("/detail/{job_id}", response_model=schemas.JobOut)
def job_detail(job_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    # Prüfe Zugriff: Entweder über Projekt oder über Organisation
    if job.project_id:
        assert_project_member(db, user, job.project_id)
    else:
        # Org-level Job (z.B. Transcription)
        from ..authorization import assert_org_member
        assert_org_member(db, user, job.organization_id)
    return job
