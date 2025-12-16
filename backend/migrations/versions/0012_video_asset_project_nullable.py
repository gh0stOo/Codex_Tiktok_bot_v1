"""make video_assets.project_id nullable

Revision ID: 0012_video_asset_project_nullable
Revises: 0011_video_asset_translation_fields
Create Date: 2024-12-17 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0012_video_asset_project_nullable'
down_revision = '0011_video_asset_translation_fields'
branch_labels = None
depends_on = None


def upgrade():
    # Mache project_id nullable für org-level Assets (YouTube Transcription/Translation)
    op.alter_column('video_assets', 'project_id',
                    existing_type=sa.String(36),
                    nullable=True)


def downgrade():
    # Setze project_id wieder auf NOT NULL (kann Fehler verursachen wenn NULL-Werte existieren)
    op.alter_column('video_assets', 'project_id',
                    existing_type=sa.String(36),
                    nullable=False)

