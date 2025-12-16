"""add translation fields to video_assets

Revision ID: 0011_video_asset_translation_fields
Revises: 0010_video_generation_fields
Create Date: 2024-12-17 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0011_video_asset_translation_fields'
down_revision = '0010_video_generation_fields'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('video_assets', sa.Column('original_language', sa.String(10), nullable=True))
    op.add_column('video_assets', sa.Column('translated_language', sa.String(10), nullable=True))
    op.add_column('video_assets', sa.Column('voice_clone_model_id', sa.String(255), nullable=True))
    op.add_column('video_assets', sa.Column('translation_provider', sa.String(50), nullable=True))


def downgrade():
    op.drop_column('video_assets', 'translation_provider')
    op.drop_column('video_assets', 'voice_clone_model_id')
    op.drop_column('video_assets', 'translated_language')
    op.drop_column('video_assets', 'original_language')

