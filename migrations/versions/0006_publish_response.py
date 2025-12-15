"""publish response storage

Revision ID: 0006
Revises: 0005
Create Date: 2025-12-14
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("video_assets", sa.Column("publish_response", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("video_assets", "publish_response")
