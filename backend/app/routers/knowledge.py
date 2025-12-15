from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from .. import models, schemas
from ..auth import get_current_user, get_db
from ..authorization import assert_org_member

router = APIRouter()


@router.post("/{org_id}", response_model=schemas.KnowledgeDocOut)
def add_doc(org_id: str, payload: schemas.KnowledgeDocOut, db: Session = Depends(get_db), user=Depends(get_current_user)):
    assert_org_member(db, user, org_id, roles=["owner", "admin", "editor"])
    doc = models.KnowledgeDoc(organization_id=org_id, title=payload.title, content=payload.content)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@router.get("/{org_id}", response_model=list[schemas.KnowledgeDocOut])
def list_docs(org_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    assert_org_member(db, user, org_id)
    return db.query(models.KnowledgeDoc).filter(models.KnowledgeDoc.organization_id == org_id).all()
