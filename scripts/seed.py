import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "backend"))

from app.db import SessionLocal  # type: ignore
from app import models  # type: ignore
from app.auth import hash_password  # type: ignore
from app.config import get_settings  # type: ignore
from app.security import encrypt_secret  # type: ignore
from datetime import date, timedelta


def main():
    settings = get_settings()
    db = SessionLocal()
    demo_user = db.query(models.User).filter(models.User.email == settings.demo_email).first()
    if not demo_user:
        demo_user = models.User(email=settings.demo_email, hashed_password=hash_password(settings.demo_password))
        db.add(demo_user)
    else:
        demo_user.email = settings.demo_email
        demo_user.hashed_password = hash_password(settings.demo_password)
    org = db.query(models.Organization).filter(models.Organization.name == "Demo Org").first()
    if not org:
        org = models.Organization(name="Demo Org", autopilot_enabled=True)
        db.add(org)
        db.flush()
    membership = (
        db.query(models.Membership)
        .filter(models.Membership.user_id == demo_user.id, models.Membership.organization_id == org.id)
        .first()
    )
    if not membership:
        db.add(models.Membership(user_id=demo_user.id, organization_id=org.id, role="owner"))
    project = db.query(models.Project).filter(models.Project.name == "Demo Project").first()
    if not project:
        project = models.Project(name="Demo Project", organization_id=org.id, autopilot_enabled=True)
        db.add(project)
    db.commit()
    # seed prompt + knowledge + credential
    if not db.query(models.PromptVersion).filter(models.PromptVersion.organization_id == org.id).first():
        db.add(models.PromptVersion(organization_id=org.id, name="default_script", version=1, body="You are a TikTok script writer."))
    if not db.query(models.KnowledgeDoc).filter(models.KnowledgeDoc.organization_id == org.id).first():
        db.add(models.KnowledgeDoc(organization_id=org.id, title="Brand Voice", content="Energetic, concise, CTA heavy."))
    # credentials are only seeded if env provides keys; otherwise skip to avoid mock secrets
    if settings.openrouter_api_key:
        enc = encrypt_secret(settings.openrouter_api_key, settings.fernet_secret)
        db.add(
            models.Credential(
                organization_id=org.id,
                provider="openrouter",
                name="openrouter",
                encrypted_secret=enc,
                version=1,
            )
        )
    db.commit()
    # generate plan slots
    start = date.today()
    for day in range(30):
        for slot in range(1, 4):
            existing = (
                db.query(models.Plan)
                .filter(models.Plan.project_id == project.id, models.Plan.slot_date == start + timedelta(days=day), models.Plan.slot_index == slot)
                .first()
            )
            if existing:
                continue
            db.add(models.Plan(project_id=project.id, slot_date=start + timedelta(days=day), slot_index=slot, status="scheduled"))
    db.commit()
    print("Seeded demo data")


if __name__ == "__main__":
    main()
