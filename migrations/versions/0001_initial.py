"""initial schema

Revision ID: 0001
Revises: 
Create Date: 2025-12-14
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("autopilot_enabled", sa.Boolean(), default=False),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "memberships",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("organization_id", sa.String(length=36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("role", sa.String(length=50), default="member"),
        sa.UniqueConstraint("user_id", "organization_id"),
    )
    op.create_table(
        "projects",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("organization_id", sa.String(length=36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("autopilot_enabled", sa.Boolean(), default=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "plans",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("project_id", sa.String(length=36), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("slot_date", sa.Date(), nullable=False),
        sa.Column("slot_index", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=50), default="scheduled"),
        sa.Column("approved", sa.Boolean(), default=False),
        sa.Column("locked", sa.Boolean(), default=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "usage_ledger",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("organization_id", sa.String(length=36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("metric", sa.String(length=100), nullable=False),
        sa.Column("amount", sa.Integer(), default=0),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "credentials",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("organization_id", sa.String(length=36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("encrypted_secret", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("version", sa.Integer(), default=1),
    )
    op.create_table(
        "knowledge_docs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("organization_id", sa.String(length=36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "prompt_versions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("organization_id", sa.String(length=36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("name", "version", "organization_id"),
    )
    op.create_table(
        "video_assets",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("project_id", sa.String(length=36), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("plan_id", sa.String(length=36), sa.ForeignKey("plans.id")),
        sa.Column("status", sa.String(length=50), default="generated"),
        sa.Column("video_path", sa.String(length=500)),
        sa.Column("thumbnail_path", sa.String(length=500)),
        sa.Column("transcript", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "jobs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("organization_id", sa.String(length=36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("project_id", sa.String(length=36), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("type", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=50), default="pending"),
        sa.Column("payload", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "metrics",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("organization_id", sa.String(length=36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("project_id", sa.String(length=36), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("plan_id", sa.String(length=36), sa.ForeignKey("plans.id")),
        sa.Column("metric", sa.String(length=100), nullable=False),
        sa.Column("value", sa.Integer(), default=0),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "social_accounts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("organization_id", sa.String(length=36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("platform", sa.String(length=50), nullable=False),
        sa.Column("handle", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "oauth_tokens",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("social_account_id", sa.String(length=36), sa.ForeignKey("social_accounts.id"), nullable=False),
        sa.Column("access_token", sa.Text(), nullable=False),
        sa.Column("refresh_token", sa.Text()),
        sa.Column("expires_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("oauth_tokens")
    op.drop_table("social_accounts")
    op.drop_table("metrics")
    op.drop_table("jobs")
    op.drop_table("video_assets")
    op.drop_table("prompt_versions")
    op.drop_table("knowledge_docs")
    op.drop_table("credentials")
    op.drop_table("usage_ledger")
    op.drop_table("plans")
    op.drop_table("projects")
    op.drop_table("memberships")
    op.drop_table("users")
    op.drop_table("organizations")
