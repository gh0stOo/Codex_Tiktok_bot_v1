"""add content fields to plans

Revision ID: 0008_plan_content_fields
Revises: 0007_idempotency_constraint
Create Date: 2024-12-16 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0008_plan_content_fields'
down_revision = '0007_idempotency_constraint'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('plans', sa.Column('category', sa.String(100), nullable=True))
    op.add_column('plans', sa.Column('topic', sa.String(500), nullable=True))
    op.add_column('plans', sa.Column('script_content', sa.Text(), nullable=True))
    op.add_column('plans', sa.Column('hook', sa.String(500), nullable=True))
    op.add_column('plans', sa.Column('title', sa.String(255), nullable=True))
    op.add_column('plans', sa.Column('cta', sa.String(255), nullable=True))


def downgrade():
    op.drop_column('plans', 'cta')
    op.drop_column('plans', 'title')
    op.drop_column('plans', 'hook')
    op.drop_column('plans', 'script_content')
    op.drop_column('plans', 'topic')
    op.drop_column('plans', 'category')

