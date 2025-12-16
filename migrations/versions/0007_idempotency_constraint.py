"""add unique constraint for idempotency

Revision ID: 0007
Revises: 0006
Create Date: 2025-12-14
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # First, clean up duplicate jobs - keep only the most recent one per idempotency key
    # This handles existing data before applying the constraint
    connection = op.get_bind()
    
    # First, delete job_runs for duplicate jobs (keep runs for the most recent job)
    connection.execute(sa.text("""
        DELETE FROM job_runs jr1
        USING jobs j1, jobs j2
        WHERE jr1.job_id = j1.id
        AND j1.id < j2.id
        AND j1.organization_id = j2.organization_id
        AND j1.idempotency_key = j2.idempotency_key
        AND j1.type = j2.type
        AND j1.idempotency_key IS NOT NULL
    """))
    
    # Then, remove duplicate jobs, keeping only the most recent one
    connection.execute(sa.text("""
        DELETE FROM jobs j1
        USING jobs j2
        WHERE j1.id < j2.id
        AND j1.organization_id = j2.organization_id
        AND j1.idempotency_key = j2.idempotency_key
        AND j1.type = j2.type
        AND j1.idempotency_key IS NOT NULL
    """))
    
    # Add unique constraint on (organization_id, idempotency_key, type) where idempotency_key is not null
    # This prevents duplicate jobs with the same idempotency key within an organization
    op.create_index(
        "ix_jobs_idempotency_org_type",
        "jobs",
        ["organization_id", "idempotency_key", "type"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_jobs_idempotency_org_type", table_name="jobs")

