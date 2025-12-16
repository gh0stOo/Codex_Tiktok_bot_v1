"""project video settings

Revision ID: 0008
Revises: 0007
Create Date: 2025-01-XX
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("video_provider", sa.String(50), nullable=True))
    op.add_column("projects", sa.Column("video_model_id", sa.String(255), nullable=True))
    op.add_column("projects", sa.Column("video_credential_id", sa.String(36), nullable=True))
    op.create_foreign_key(
        "fk_projects_video_credential",
        "projects",
        "credentials",
        ["video_credential_id"],
        ["id"],
        ondelete="SET NULL"
    )


def downgrade() -> None:
    op.drop_constraint("fk_projects_video_credential", "projects", type_="foreignkey")
    op.drop_column("projects", "video_credential_id")
    op.drop_column("projects", "video_model_id")
    op.drop_column("projects", "video_provider")

