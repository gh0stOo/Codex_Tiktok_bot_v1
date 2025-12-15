"""job run tracking and metrics scope

Revision ID: 0004
Revises: 0003
Create Date: 2025-12-14
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("metrics", sa.Column("open_id", sa.String(length=255), nullable=True))
    op.create_table(
        "job_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("job_id", sa.String(length=36), sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("job_runs")
    op.drop_column("metrics", "open_id")
