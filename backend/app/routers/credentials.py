from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas
from ..auth import get_current_user, get_db
from ..authorization import assert_org_member
from ..security import encrypt_secret
from ..config import get_settings

router = APIRouter()
settings = get_settings()


@router.post("/{org_id}", response_model=schemas.CredentialOut)
def add_credential(org_id: str, payload: schemas.CredentialCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    assert_org_member(db, user, org_id, roles=["owner", "admin"])
    cred = models.Credential(
        organization_id=org_id,
        provider=payload.provider,
        name=payload.name,
        encrypted_secret=encrypt_secret(payload.secret, settings.fernet_secret),
    )
    db.add(cred)
    db.commit()
    db.refresh(cred)
    return cred


@router.get("/{org_id}", response_model=list[schemas.CredentialOut])
def list_credentials(org_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    assert_org_member(db, user, org_id)
    return db.query(models.Credential).filter(models.Credential.organization_id == org_id).all()
