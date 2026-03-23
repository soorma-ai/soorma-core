"""Tracker three-dimensional tenancy migration.

Revision ID: f7a1c2b9d1e0
Revises: abc123def456
Create Date: 2026-03-23 07:12:00.000000+00:00

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f7a1c2b9d1e0"
down_revision = "abc123def456"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # plan_progress: rename legacy columns and add platform dimension
    op.alter_column("plan_progress", "tenant_id", new_column_name="service_tenant_id")
    op.alter_column("plan_progress", "user_id", new_column_name="service_user_id")
    op.add_column(
        "plan_progress",
        sa.Column("platform_tenant_id", sa.String(length=64), nullable=True),
    )

    op.execute("UPDATE plan_progress SET platform_tenant_id = service_tenant_id WHERE platform_tenant_id IS NULL")

    op.alter_column("plan_progress", "platform_tenant_id", nullable=False)
    op.alter_column("plan_progress", "service_tenant_id", type_=sa.String(length=64), nullable=False)
    op.alter_column("plan_progress", "service_user_id", type_=sa.String(length=64), nullable=False)

    # action_progress: rename legacy columns and add platform dimension
    op.alter_column("action_progress", "tenant_id", new_column_name="service_tenant_id")
    op.alter_column("action_progress", "user_id", new_column_name="service_user_id")
    op.add_column(
        "action_progress",
        sa.Column("platform_tenant_id", sa.String(length=64), nullable=True),
    )

    op.execute("UPDATE action_progress SET platform_tenant_id = service_tenant_id WHERE platform_tenant_id IS NULL")

    op.alter_column("action_progress", "platform_tenant_id", nullable=False)
    op.alter_column("action_progress", "service_tenant_id", type_=sa.String(length=64), nullable=False)
    op.alter_column("action_progress", "service_user_id", type_=sa.String(length=64), nullable=False)

    # Replace legacy constraints — drop FK first (it depends on uq_plan_id index)
    op.drop_constraint("action_progress_plan_id_fkey", "action_progress", type_="foreignkey")
    op.drop_constraint("uq_plan_id", "plan_progress", type_="unique")
    op.drop_constraint("uq_action_tenant_action", "action_progress", type_="unique")

    op.create_unique_constraint(
        "uq_plan_scope_plan",
        "plan_progress",
        ["platform_tenant_id", "service_tenant_id", "plan_id"],
    )
    op.create_unique_constraint(
        "uq_action_scope_action",
        "action_progress",
        ["platform_tenant_id", "service_tenant_id", "action_id"],
    )
    op.create_foreign_key(
        "fk_action_plan_scope",
        "action_progress",
        "plan_progress",
        ["platform_tenant_id", "service_tenant_id", "plan_id"],
        ["platform_tenant_id", "service_tenant_id", "plan_id"],
        ondelete="CASCADE",
    )

    # Replace legacy indexes with scope-aware indexes
    op.drop_index("idx_plan_tenant_plan", table_name="plan_progress")
    op.drop_index("ix_plan_progress_tenant_id", table_name="plan_progress")
    op.drop_index("ix_plan_progress_plan_id", table_name="plan_progress")

    op.drop_index("idx_action_tenant_action", table_name="action_progress")
    op.drop_index("ix_action_progress_tenant_id", table_name="action_progress")

    op.create_index(
        "idx_plan_scope_plan",
        "plan_progress",
        ["platform_tenant_id", "service_tenant_id", "plan_id"],
    )
    op.create_index("ix_plan_progress_platform_tenant_id", "plan_progress", ["platform_tenant_id"])
    op.create_index("ix_plan_progress_service_tenant_id", "plan_progress", ["service_tenant_id"])

    op.create_index(
        "idx_action_scope_action",
        "action_progress",
        ["platform_tenant_id", "service_tenant_id", "action_id"],
    )
    op.create_index("ix_action_progress_platform_tenant_id", "action_progress", ["platform_tenant_id"])
    op.create_index("ix_action_progress_service_tenant_id", "action_progress", ["service_tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_action_progress_service_tenant_id", table_name="action_progress")
    op.drop_index("ix_action_progress_platform_tenant_id", table_name="action_progress")
    op.drop_index("idx_action_scope_action", table_name="action_progress")

    op.drop_index("ix_plan_progress_service_tenant_id", table_name="plan_progress")
    op.drop_index("ix_plan_progress_platform_tenant_id", table_name="plan_progress")
    op.drop_index("idx_plan_scope_plan", table_name="plan_progress")

    op.create_index("ix_action_progress_tenant_id", "action_progress", ["service_tenant_id"])
    op.create_index("idx_action_tenant_action", "action_progress", ["service_tenant_id", "action_id"])

    op.create_index("ix_plan_progress_plan_id", "plan_progress", ["plan_id"])
    op.create_index("ix_plan_progress_tenant_id", "plan_progress", ["service_tenant_id"])
    op.create_index("idx_plan_tenant_plan", "plan_progress", ["service_tenant_id", "plan_id"])

    op.drop_constraint("fk_action_plan_scope", "action_progress", type_="foreignkey")
    op.drop_constraint("uq_action_scope_action", "action_progress", type_="unique")
    op.drop_constraint("uq_plan_scope_plan", "plan_progress", type_="unique")

    op.create_foreign_key(
        "action_progress_plan_id_fkey",
        "action_progress",
        "plan_progress",
        ["plan_id"],
        ["plan_id"],
        ondelete="CASCADE",
    )
    op.create_unique_constraint(
        "uq_action_tenant_action",
        "action_progress",
        ["service_tenant_id", "action_id"],
    )
    op.create_unique_constraint("uq_plan_id", "plan_progress", ["plan_id"])

    op.drop_column("action_progress", "platform_tenant_id")
    op.alter_column("action_progress", "service_user_id", type_=sa.String(length=255), nullable=False)
    op.alter_column("action_progress", "service_tenant_id", type_=sa.String(length=255), nullable=False)
    op.alter_column("action_progress", "service_user_id", new_column_name="user_id")
    op.alter_column("action_progress", "service_tenant_id", new_column_name="tenant_id")

    op.drop_column("plan_progress", "platform_tenant_id")
    op.alter_column("plan_progress", "service_user_id", type_=sa.String(length=255), nullable=False)
    op.alter_column("plan_progress", "service_tenant_id", type_=sa.String(length=255), nullable=False)
    op.alter_column("plan_progress", "service_user_id", new_column_name="user_id")
    op.alter_column("plan_progress", "service_tenant_id", new_column_name="tenant_id")
