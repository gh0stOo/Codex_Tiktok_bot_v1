"""
Idempotency-Service für Task-Erstellung.
Verhindert doppelte Task-Ausführung.
"""
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from .. import models


class IdempotencyService:
    """Service für Idempotency-Checks."""

    @staticmethod
    def check_and_create_job(
        db: Session,
        organization_id: str,
        project_id: str | None,  # Optional für org-level Jobs
        job_type: str,
        idempotency_key: str,
        payload: str | None = None,
        ttl_minutes: int = 60,
    ) -> tuple[models.Job | None, bool]:
        """
        Prüft ob Job mit Idempotency-Key bereits existiert und erstellt neuen falls nicht.
        Returns:
            (existing_job_or_new_job, is_new)
        """
        # Prüfe ob Job mit gleichem Key existiert und noch aktiv ist
        existing = (
            db.query(models.Job)
            .filter(
                models.Job.organization_id == organization_id,
                models.Job.idempotency_key == idempotency_key,
                models.Job.type == job_type,
            )
            .order_by(models.Job.created_at.desc())
            .first()
        )

        if existing:
            # Prüfe ob Job noch innerhalb TTL ist
            age = datetime.utcnow() - existing.created_at
            if age < timedelta(minutes=ttl_minutes):
                # Job existiert bereits und ist noch gültig
                if existing.status in ("pending", "in_progress"):
                    return existing, False
                # Wenn completed, prüfe ob wir es wiederholen können
                if existing.status == "completed":
                    # Für completed Jobs: erlaube Re-Run nur wenn explizit gewünscht
                    return existing, False

        # Erstelle neuen Job
        new_job = models.Job(
            organization_id=organization_id,
            project_id=project_id,
            type=job_type,
            status="pending",
            idempotency_key=idempotency_key,
            payload=payload,
        )
        db.add(new_job)
        db.commit()
        db.refresh(new_job)
        return new_job, True

    @staticmethod
    def is_duplicate(db: Session, organization_id: str, idempotency_key: str, job_type: str) -> bool:
        """Prüft ob Job mit Key bereits existiert."""
        existing = (
            db.query(models.Job)
            .filter(
                models.Job.organization_id == organization_id,
                models.Job.idempotency_key == idempotency_key,
                models.Job.type == job_type,
                models.Job.status.in_(["pending", "in_progress"]),
            )
            .first()
        )
        return existing is not None

