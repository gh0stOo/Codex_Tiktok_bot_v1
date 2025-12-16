"""add video generation fields to projects

Revision ID: 0010_video_generation_fields
Revises: 0009_plan_visual_fields
Create Date: 2024-12-17 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0010'
down_revision = '0009'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('projects', sa.Column('video_generation_provider', sa.String(50), nullable=True))
    op.add_column('projects', sa.Column('video_generation_model_id', sa.String(255), nullable=True))
    op.add_column('projects', sa.Column('video_generation_credential_id', sa.String(36), nullable=True))
    op.create_foreign_key(
        'fk_projects_video_generation_credential_id',
        'projects', 'credentials',
        ['video_generation_credential_id'], ['id']
    )


def downgrade():
    op.drop_constraint('fk_projects_video_generation_credential_id', 'projects', type_='foreignkey')
    op.drop_column('projects', 'video_generation_credential_id')
    op.drop_column('projects', 'video_generation_model_id')
    op.drop_column('projects', 'video_generation_provider')

