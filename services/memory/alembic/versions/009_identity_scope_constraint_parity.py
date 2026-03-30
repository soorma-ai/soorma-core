"""Align identity-scoped constraints and indexes with runtime conflict targets.

Revision ID: 009_scope_constraint_parity
Revises: 008
Create Date: 2026-03-30

This migration resolves runtime/schema mismatches introduced during unit-2 by
aligning database constraints/indexes with identity-scoped ON CONFLICT targets.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "009_scope_constraint_parity"
down_revision = "008"
branch_labels = None
depends_on = None


def _replace_unique_constraint(table: str, name: str, columns_sql: str) -> None:
    """Replace a unique constraint with deterministic drop/create behavior."""
    conn = op.get_bind()
    conn.execute(sa.text(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {name}"))
    conn.execute(sa.text(
        f"ALTER TABLE {table} ADD CONSTRAINT {name} UNIQUE ({columns_sql})"
    ))


def upgrade() -> None:
    """Apply identity-scoped constraint/index parity updates."""
    conn = op.get_bind()

    # working_memory: match ON CONFLICT target
    conn.execute(sa.text("ALTER TABLE working_memory DROP CONSTRAINT IF EXISTS plan_key_unique"))
    _replace_unique_constraint(
        "working_memory",
        "working_memory_scope_unique",
        "platform_tenant_id, service_tenant_id, service_user_id, plan_id, key",
    )

    # task_context and plan_context: match ON CONFLICT targets
    _replace_unique_constraint(
        "task_context",
        "task_context_unique",
        "platform_tenant_id, service_tenant_id, service_user_id, task_id",
    )
    _replace_unique_constraint(
        "plan_context",
        "plan_context_unique",
        "platform_tenant_id, service_tenant_id, service_user_id, plan_id",
    )

    # plans/sessions: match application-level identity scoping
    _replace_unique_constraint(
        "plans",
        "plan_unique",
        "platform_tenant_id, service_tenant_id, service_user_id, plan_id",
    )
    _replace_unique_constraint(
        "sessions",
        "sessions_unique",
        "platform_tenant_id, service_tenant_id, service_user_id, session_id",
    )

    # semantic private upsert indexes: include service_tenant_id to match runtime
    conn.execute(sa.text("DROP INDEX IF EXISTS semantic_memory_user_external_id_private_idx"))
    conn.execute(sa.text("DROP INDEX IF EXISTS semantic_memory_user_content_hash_private_idx"))

    conn.execute(sa.text(
        "CREATE UNIQUE INDEX semantic_memory_user_external_id_private_idx "
        "ON semantic_memory (platform_tenant_id, service_tenant_id, service_user_id, external_id) "
        "WHERE external_id IS NOT NULL AND is_public = FALSE"
    ))
    conn.execute(sa.text(
        "CREATE UNIQUE INDEX semantic_memory_user_content_hash_private_idx "
        "ON semantic_memory (platform_tenant_id, service_tenant_id, service_user_id, content_hash) "
        "WHERE is_public = FALSE"
    ))


def downgrade() -> None:
    """Revert to pre-unit-3 identity constraint/index behavior."""
    conn = op.get_bind()

    # working_memory: restore old two-column uniqueness
    conn.execute(sa.text("ALTER TABLE working_memory DROP CONSTRAINT IF EXISTS working_memory_scope_unique"))
    _replace_unique_constraint("working_memory", "plan_key_unique", "plan_id, key")

    # task_context and plan_context: restore 008 behavior
    _replace_unique_constraint(
        "task_context",
        "task_context_unique",
        "platform_tenant_id, task_id",
    )
    _replace_unique_constraint(
        "plan_context",
        "plan_context_unique",
        "platform_tenant_id, plan_id",
    )

    # plans/sessions: restore 008 behavior
    _replace_unique_constraint(
        "plans",
        "plan_unique",
        "platform_tenant_id, plan_id",
    )
    _replace_unique_constraint(
        "sessions",
        "sessions_unique",
        "platform_tenant_id, session_id",
    )

    # semantic private upsert indexes: revert service_tenant_id inclusion
    conn.execute(sa.text("DROP INDEX IF EXISTS semantic_memory_user_external_id_private_idx"))
    conn.execute(sa.text("DROP INDEX IF EXISTS semantic_memory_user_content_hash_private_idx"))

    conn.execute(sa.text(
        "CREATE UNIQUE INDEX semantic_memory_user_external_id_private_idx "
        "ON semantic_memory (platform_tenant_id, service_user_id, external_id) "
        "WHERE external_id IS NOT NULL AND is_public = FALSE"
    ))
    conn.execute(sa.text(
        "CREATE UNIQUE INDEX semantic_memory_user_content_hash_private_idx "
        "ON semantic_memory (platform_tenant_id, service_user_id, content_hash) "
        "WHERE is_public = FALSE"
    ))
