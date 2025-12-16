from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas
from ..auth import get_current_user, get_db
from ..authorization import assert_org_member

router = APIRouter()


@router.post("/{org_id}", response_model=schemas.ProjectOut)
def create_project(org_id: str, payload: schemas.ProjectCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    assert_org_member(db, user, org_id)
    project = models.Project(
        organization_id=org_id, 
        name=payload.name, 
        autopilot_enabled=payload.autopilot_enabled,
        # Legacy: Script-Generierung verwendet immer GPT-4.0 Mini (fest)
        video_provider="openrouter",
        video_model_id="openai/gpt-4o-mini",
        # Neue: Video-Generierung Standard-Einstellungen
        video_generation_provider="falai",  # Standard: Fal.ai für Video-Generierung
        video_generation_model_id="fal-ai/kling-video/v2.6/pro/text-to-video"  # Standard: Kling 2.6 Pro
    )
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


@router.put("/video-settings/{project_id}", response_model=schemas.ProjectOut)
def update_video_settings(
    project_id: str,
    video_provider: str | None = None,
    video_model_id: str | None = None,
    video_credential_id: str | None = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """Update Video-Generierung Einstellungen für ein Projekt (Legacy - für Script-Generierung)"""
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    assert_org_member(db, user, project.organization_id, roles=["owner", "admin", "editor"])
    
    # Legacy: Update Video-Einstellungen (wird nicht mehr verwendet, Script ist fest GPT-4.0 Mini)
    if video_provider is not None:
        if video_provider not in ["openrouter", "falai"]:
            raise HTTPException(status_code=400, detail="video_provider muss 'openrouter' oder 'falai' sein")
        project.video_provider = video_provider
    
    if video_model_id is not None:
        project.video_model_id = video_model_id
    
    if video_credential_id is not None:
        # Prüfe ob Credential existiert und zur Org gehört
        if video_credential_id:
            credential = db.query(models.Credential).filter(
                models.Credential.id == video_credential_id,
                models.Credential.organization_id == project.organization_id
            ).first()
            if not credential:
                raise HTTPException(status_code=404, detail="Credential nicht gefunden")
        project.video_credential_id = video_credential_id
    
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.put("/video-generation-settings/{project_id}", response_model=schemas.ProjectOut)
def update_video_generation_settings(
    project_id: str,
    video_generation_provider: str | None = None,
    video_generation_model_id: str | None = None,
    video_generation_credential_id: str | None = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """Update Video-Generierungs-Einstellungen für ein Projekt (Text-to-Video APIs)"""
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    assert_org_member(db, user, project.organization_id, roles=["owner", "admin", "editor"])
    
    # Update Video-Generierungs-Einstellungen (für Text-to-Video APIs)
    if video_generation_provider is not None:
        if video_generation_provider not in ["falai"]:
            raise HTTPException(status_code=400, detail="video_generation_provider muss 'falai' sein")
        project.video_generation_provider = video_generation_provider
    
    if video_generation_model_id is not None:
        project.video_generation_model_id = video_generation_model_id
    
    if video_generation_credential_id is not None:
        # Prüfe ob Credential existiert und zur Org gehört
        if video_generation_credential_id:
            credential = db.query(models.Credential).filter(
                models.Credential.id == video_generation_credential_id,
                models.Credential.organization_id == project.organization_id,
                models.Credential.provider == (video_generation_provider or project.video_generation_provider or "falai")
            ).first()
            if not credential:
                raise HTTPException(status_code=404, detail="Credential nicht gefunden oder falscher Provider")
        project.video_generation_credential_id = video_generation_credential_id
    
    db.add(project)
    db.commit()
    db.refresh(project)
    return project
