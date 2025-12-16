"""add visual fields to plans

Revision ID: 0009_plan_visual_fields
Revises: 0008_plan_content_fields
Create Date: 2024-12-16 15:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0009_plan_visual_fields'
down_revision = '0008_plan_content_fields'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('plans', sa.Column('visual_prompt', sa.Text(), nullable=True))
    op.add_column('plans', sa.Column('lighting', sa.String(100), nullable=True))
    op.add_column('plans', sa.Column('composition', sa.String(200), nullable=True))
    op.add_column('plans', sa.Column('camera_angles', sa.String(200), nullable=True))
    op.add_column('plans', sa.Column('visual_style', sa.String(100), nullable=True))


def downgrade():
    op.drop_column('plans', 'visual_style')
    op.drop_column('plans', 'camera_angles')
    op.drop_column('plans', 'composition')
    op.drop_column('plans', 'lighting')
    op.drop_column('plans', 'visual_prompt')

