"""Initial identity schema.

Revision ID: 001_initial_identity_schema
Revises:
Create Date: 2026-04-05
"""

from alembic import op
import sqlalchemy as sa


revision = "001_initial_identity_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create identity domain tables."""
    op.create_table(
        "platform_tenant_identity_domains",
        sa.Column("tenant_domain_id", sa.String(length=64), nullable=False),
        sa.Column("platform_tenant_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("created_by", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("tenant_domain_id"),
    )
    op.create_index(
        "ix_platform_tenant_identity_domains_platform_tenant_id",
        "platform_tenant_identity_domains",
        ["platform_tenant_id"],
    )

    op.create_table(
        "principals",
        sa.Column("principal_id", sa.String(length=64), nullable=False),
        sa.Column("tenant_domain_id", sa.String(length=64), nullable=False),
        sa.Column("principal_type", sa.String(length=32), nullable=False),
        sa.Column("lifecycle_state", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("external_ref", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["tenant_domain_id"],
            ["platform_tenant_identity_domains.tenant_domain_id"],
        ),
        sa.PrimaryKeyConstraint("principal_id"),
    )
    op.create_index("ix_principals_tenant_domain_id", "principals", ["tenant_domain_id"])

    op.create_table(
        "role_assignments",
        sa.Column("assignment_id", sa.String(length=64), nullable=False),
        sa.Column("principal_id", sa.String(length=64), nullable=False),
        sa.Column("role_name", sa.String(length=64), nullable=False),
        sa.Column("role_scope", sa.String(length=32), nullable=False, server_default="platform_baseline"),
        sa.Column("granted_by", sa.String(length=64), nullable=False),
        sa.Column("granted_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["principal_id"], ["principals.principal_id"]),
        sa.PrimaryKeyConstraint("assignment_id"),
    )
    op.create_index("ix_role_assignments_principal_id", "role_assignments", ["principal_id"])

    op.create_table(
        "delegated_issuers",
        sa.Column("delegated_issuer_id", sa.String(length=64), nullable=False),
        sa.Column("tenant_domain_id", sa.String(length=64), nullable=False),
        sa.Column("issuer_id", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("jwk_set_ref_or_material", sa.Text(), nullable=False),
        sa.Column("audience_policy_ref", sa.String(length=128), nullable=False),
        sa.Column("claim_mapping_policy_ref", sa.String(length=128), nullable=False),
        sa.Column("created_by", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["tenant_domain_id"],
            ["platform_tenant_identity_domains.tenant_domain_id"],
        ),
        sa.PrimaryKeyConstraint("delegated_issuer_id"),
    )
    op.create_index("ix_delegated_issuers_tenant_domain_id", "delegated_issuers", ["tenant_domain_id"])
    op.create_index("ix_delegated_issuers_issuer_id", "delegated_issuers", ["issuer_id"])

    op.create_table(
        "claim_mapping_policies",
        sa.Column("mapping_policy_id", sa.String(length=64), nullable=False),
        sa.Column("tenant_domain_id", sa.String(length=64), nullable=False),
        sa.Column("policy_version", sa.String(length=32), nullable=False, server_default="1"),
        sa.Column("mode", sa.String(length=32), nullable=False, server_default="reject_on_collision"),
        sa.Column("namespace_rules", sa.Text(), nullable=True),
        sa.Column("precedence_rules", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["tenant_domain_id"],
            ["platform_tenant_identity_domains.tenant_domain_id"],
        ),
        sa.PrimaryKeyConstraint("mapping_policy_id"),
    )
    op.create_index(
        "ix_claim_mapping_policies_tenant_domain_id",
        "claim_mapping_policies",
        ["tenant_domain_id"],
    )

    op.create_table(
        "external_identity_bindings",
        sa.Column("binding_id", sa.String(length=64), nullable=False),
        sa.Column("tenant_domain_id", sa.String(length=64), nullable=False),
        sa.Column("source_issuer_id", sa.String(length=128), nullable=False),
        sa.Column("external_identity_key", sa.String(length=256), nullable=False),
        sa.Column("canonical_identity_key", sa.String(length=256), nullable=False),
        sa.Column("principal_id", sa.String(length=64), nullable=False),
        sa.Column("verification_state", sa.String(length=32), nullable=False, server_default="verified"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_domain_id"], ["platform_tenant_identity_domains.tenant_domain_id"]),
        sa.ForeignKeyConstraint(["principal_id"], ["principals.principal_id"]),
        sa.PrimaryKeyConstraint("binding_id"),
    )
    op.create_index(
        "ix_external_identity_bindings_tenant_domain_id",
        "external_identity_bindings",
        ["tenant_domain_id"],
    )
    op.create_index(
        "ix_external_identity_bindings_source_issuer_id",
        "external_identity_bindings",
        ["source_issuer_id"],
    )
    op.create_index(
        "ix_external_identity_bindings_external_identity_key",
        "external_identity_bindings",
        ["external_identity_key"],
    )
    op.create_index(
        "ix_external_identity_bindings_canonical_identity_key",
        "external_identity_bindings",
        ["canonical_identity_key"],
    )
    op.create_index(
        "ix_external_identity_bindings_principal_id",
        "external_identity_bindings",
        ["principal_id"],
    )

    op.create_table(
        "token_issuance_records",
        sa.Column("issuance_id", sa.String(length=64), nullable=False),
        sa.Column("tenant_domain_id", sa.String(length=64), nullable=False),
        sa.Column("principal_id", sa.String(length=64), nullable=False),
        sa.Column("issuance_type", sa.String(length=32), nullable=False, server_default="platform"),
        sa.Column("decision", sa.String(length=32), nullable=False, server_default="issued"),
        sa.Column("decision_reason_code", sa.String(length=64), nullable=False, server_default="ok"),
        sa.Column("issued_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_domain_id"], ["platform_tenant_identity_domains.tenant_domain_id"]),
        sa.ForeignKeyConstraint(["principal_id"], ["principals.principal_id"]),
        sa.PrimaryKeyConstraint("issuance_id"),
    )
    op.create_index("ix_token_issuance_records_tenant_domain_id", "token_issuance_records", ["tenant_domain_id"])
    op.create_index("ix_token_issuance_records_principal_id", "token_issuance_records", ["principal_id"])

    op.create_table(
        "identity_audit_events",
        sa.Column("event_id", sa.String(length=64), nullable=False),
        sa.Column("tenant_domain_id", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("actor", sa.String(length=128), nullable=False),
        sa.Column("correlation_id", sa.String(length=128), nullable=False),
        sa.Column("payload_summary", sa.Text(), nullable=False),
        sa.Column("critical", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("emitted_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index("ix_identity_audit_events_tenant_domain_id", "identity_audit_events", ["tenant_domain_id"])
    op.create_index("ix_identity_audit_events_event_type", "identity_audit_events", ["event_type"])
    op.create_index("ix_identity_audit_events_correlation_id", "identity_audit_events", ["correlation_id"])


def downgrade() -> None:
    """Drop identity domain tables."""
    op.drop_index("ix_identity_audit_events_correlation_id", table_name="identity_audit_events")
    op.drop_index("ix_identity_audit_events_event_type", table_name="identity_audit_events")
    op.drop_index("ix_identity_audit_events_tenant_domain_id", table_name="identity_audit_events")
    op.drop_table("identity_audit_events")

    op.drop_index("ix_token_issuance_records_principal_id", table_name="token_issuance_records")
    op.drop_index("ix_token_issuance_records_tenant_domain_id", table_name="token_issuance_records")
    op.drop_table("token_issuance_records")

    op.drop_index("ix_external_identity_bindings_principal_id", table_name="external_identity_bindings")
    op.drop_index("ix_external_identity_bindings_canonical_identity_key", table_name="external_identity_bindings")
    op.drop_index("ix_external_identity_bindings_external_identity_key", table_name="external_identity_bindings")
    op.drop_index("ix_external_identity_bindings_source_issuer_id", table_name="external_identity_bindings")
    op.drop_index("ix_external_identity_bindings_tenant_domain_id", table_name="external_identity_bindings")
    op.drop_table("external_identity_bindings")

    op.drop_index("ix_claim_mapping_policies_tenant_domain_id", table_name="claim_mapping_policies")
    op.drop_table("claim_mapping_policies")

    op.drop_index("ix_delegated_issuers_issuer_id", table_name="delegated_issuers")
    op.drop_index("ix_delegated_issuers_tenant_domain_id", table_name="delegated_issuers")
    op.drop_table("delegated_issuers")

    op.drop_index("ix_role_assignments_principal_id", table_name="role_assignments")
    op.drop_table("role_assignments")

    op.drop_index("ix_principals_tenant_domain_id", table_name="principals")
    op.drop_table("principals")

    op.drop_index(
        "ix_platform_tenant_identity_domains_platform_tenant_id",
        table_name="platform_tenant_identity_domains",
    )
    op.drop_table("platform_tenant_identity_domains")
