from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas
from ..auth import get_current_user, get_db
from ..authorization import assert_org_member

router = APIRouter()


@router.post("/{org_id}", response_model=schemas.ProjectOut)
def create_project(org_id: str, payload: schemas.ProjectCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    assert_org_member(db, user, org_id)
    project = models.Project(organization_id=org_id, name=payload.name, autopilot_enabled=payload.autopilot_enabled)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/{org_id}", response_model=list[schemas.ProjectOut])
def list_projects(org_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    assert_org_member(db, user, org_id)
    return db.query(models.Project).filter(models.Project.organization_id == org_id).all()


@router.post("/toggle/{project_id}")
def toggle_autopilot(project_id: str, enabled: bool, db: Session = Depends(get_db), user=Depends(get_current_user)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    assert_org_member(db, user, project.organization_id, roles=["owner", "admin"])
    project.autopilot_enabled = enabled
    db.add(project)
    db.commit()
    db.refresh(project)
    return {"autopilot_enabled": project.autopilot_enabled}
