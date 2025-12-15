from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from .. import models, schemas
from ..auth import get_current_user, get_db
from ..authorization import assert_org_member

router = APIRouter()


@router.post("/{org_id}", response_model=schemas.PromptVersionOut)
def add_prompt(org_id: str, payload: schemas.PromptVersionOut, db: Session = Depends(get_db), user=Depends(get_current_user)):
    assert_org_member(db, user, org_id, roles=["owner", "admin", "editor"])
    record = models.PromptVersion(
        organization_id=org_id,
        name=payload.name,
        version=payload.version,
        body=payload.body,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/{org_id}", response_model=list[schemas.PromptVersionOut])
def list_prompts(org_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    assert_org_member(db, user, org_id)
    return (
        db.query(models.PromptVersion)
        .filter(models.PromptVersion.organization_id == org_id)
        .order_by(models.PromptVersion.name, models.PromptVersion.version.desc())
        .all()
    )
