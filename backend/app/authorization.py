from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from . import models


def assert_org_member(db: Session, user: models.User, organization_id: str, roles: list[str] | None = None) -> models.Membership:
    membership = (
        db.query(models.Membership)
        .filter(models.Membership.organization_id == organization_id, models.Membership.user_id == user.id)
        .first()
    )
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of organization")
    if roles and membership.role not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    return membership


def assert_project_member(db: Session, user: models.User, project_id: str, roles: list[str] | None = None) -> models.Project:
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    assert_org_member(db, user, project.organization_id, roles)
    return project


def assert_plan_member(db: Session, user: models.User, plan_id: str, roles: list[str] | None = None) -> models.Plan:
    plan = db.query(models.Plan).filter(models.Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    project = assert_project_member(db, user, plan.project_id, roles)
    return plan
