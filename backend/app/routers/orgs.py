from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from .. import models, schemas
from ..auth import get_current_user, get_db

router = APIRouter()


@router.post("/", response_model=schemas.OrganizationOut)
def create_org(payload: schemas.OrganizationCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    org = models.Organization(name=payload.name)
    db.add(org)
    db.flush()
    membership = models.Membership(user_id=user.id, organization_id=org.id, role="owner")
    db.add(membership)
    db.commit()
    db.refresh(org)
    return org


@router.get("/", response_model=list[schemas.OrganizationOut])
def list_orgs(db: Session = Depends(get_db), user=Depends(get_current_user)):
    org_ids = [
        membership.organization_id
        for membership in db.query(models.Membership).filter(models.Membership.user_id == user.id).all()
    ]
    return db.query(models.Organization).filter(models.Organization.id.in_(org_ids)).all()
