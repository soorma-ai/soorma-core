"""Add persisted tenant admin credentials.

Revision ID: 0002_tenant_admin_credentials
Revises: 001_initial_identity_schema
Create Date: 2026-04-18
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_tenant_admin_credentials"
down_revision = "001_initial_identity_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create tenant admin credentials table."""
    op.create_table(
        "tenant_admin_credentials",
        sa.Column("credential_id", sa.String(length=64), nullable=False),
        sa.Column("platform_tenant_id", sa.String(length=64), nullable=False),
        sa.Column("secret_hash", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column("rotated_from_credential_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("credential_id"),
    )
    op.create_index(
        "ix_tenant_admin_credentials_platform_tenant_id",
        "tenant_admin_credentials",
        ["platform_tenant_id"],
    )
    op.create_index(
        "ix_tenant_admin_credentials_status",
        "tenant_admin_credentials",
        ["status"],
    )


def downgrade() -> None:
    """Drop tenant admin credentials table."""
    op.drop_index("ix_tenant_admin_credentials_status", table_name="tenant_admin_credentials")
    op.drop_index(
        "ix_tenant_admin_credentials_platform_tenant_id",
        table_name="tenant_admin_credentials",
    )
    op.drop_table("tenant_admin_credentials")
