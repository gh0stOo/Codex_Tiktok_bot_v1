"""add organization scope to plans and video assets

Revision ID: 0003
Revises: 0002
Create Date: 2025-12-14
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("plans", sa.Column("organization_id", sa.String(length=36), sa.ForeignKey("organizations.id"), nullable=True))
    op.add_column(
        "video_assets",
        sa.Column("organization_id", sa.String(length=36), sa.ForeignKey("organizations.id"), nullable=True),
    )

    # backfill based on project link
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            UPDATE plans p
            SET organization_id = proj.organization_id
            FROM projects proj
            WHERE p.project_id = proj.id AND p.organization_id IS NULL
            """
        )
    )
    conn.execute(
        sa.text(
            """
            UPDATE video_assets va
            SET organization_id = proj.organization_id
            FROM projects proj
            WHERE va.project_id = proj.id AND va.organization_id IS NULL
            """
        )
    )

    op.alter_column("plans", "organization_id", nullable=False)
    op.alter_column("video_assets", "organization_id", nullable=False)


def downgrade() -> None:
    op.drop_column("video_assets", "organization_id")
    op.drop_column("plans", "organization_id")
