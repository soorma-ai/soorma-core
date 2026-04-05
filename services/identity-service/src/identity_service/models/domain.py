"""SQLAlchemy domain models for identity core entities."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from identity_service.core.db import Base


class PlatformTenantIdentityDomain(Base):
    __tablename__ = "platform_tenant_identity_domains"

    tenant_domain_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    platform_tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), default="active")
    created_by: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Principal(Base):
    __tablename__ = "principals"

    principal_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_domain_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("platform_tenant_identity_domains.tenant_domain_id"),
        index=True,
    )
    principal_type: Mapped[str] = mapped_column(String(32))
    lifecycle_state: Mapped[str] = mapped_column(String(32), default="active")
    external_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class RoleAssignment(Base):
    __tablename__ = "role_assignments"

    assignment_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    principal_id: Mapped[str] = mapped_column(String(64), ForeignKey("principals.principal_id"), index=True)
    role_name: Mapped[str] = mapped_column(String(64))
    role_scope: Mapped[str] = mapped_column(String(32), default="platform_baseline")
    granted_by: Mapped[str] = mapped_column(String(64))
    granted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DelegatedIssuer(Base):
    __tablename__ = "delegated_issuers"

    delegated_issuer_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_domain_id: Mapped[str] = mapped_column(String(64), ForeignKey("platform_tenant_identity_domains.tenant_domain_id"), index=True)
    issuer_id: Mapped[str] = mapped_column(String(128), index=True)
    status: Mapped[str] = mapped_column(String(32), default="active")
    jwk_set_ref_or_material: Mapped[str] = mapped_column(Text)
    audience_policy_ref: Mapped[str] = mapped_column(String(128))
    claim_mapping_policy_ref: Mapped[str] = mapped_column(String(128))
    created_by: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ClaimMappingPolicy(Base):
    __tablename__ = "claim_mapping_policies"

    mapping_policy_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_domain_id: Mapped[str] = mapped_column(String(64), ForeignKey("platform_tenant_identity_domains.tenant_domain_id"), index=True)
    policy_version: Mapped[str] = mapped_column(String(32), default="1")
    mode: Mapped[str] = mapped_column(String(32), default="reject_on_collision")
    namespace_rules: Mapped[str | None] = mapped_column(Text, nullable=True)
    precedence_rules: Mapped[str | None] = mapped_column(Text, nullable=True)


class ExternalIdentityBinding(Base):
    __tablename__ = "external_identity_bindings"

    binding_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_domain_id: Mapped[str] = mapped_column(String(64), ForeignKey("platform_tenant_identity_domains.tenant_domain_id"), index=True)
    source_issuer_id: Mapped[str] = mapped_column(String(128), index=True)
    external_identity_key: Mapped[str] = mapped_column(String(256), index=True)
    canonical_identity_key: Mapped[str] = mapped_column(String(256), index=True)
    principal_id: Mapped[str] = mapped_column(String(64), ForeignKey("principals.principal_id"), index=True)
    verification_state: Mapped[str] = mapped_column(String(32), default="verified")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TokenIssuanceRecord(Base):
    __tablename__ = "token_issuance_records"

    issuance_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_domain_id: Mapped[str] = mapped_column(String(64), ForeignKey("platform_tenant_identity_domains.tenant_domain_id"), index=True)
    principal_id: Mapped[str] = mapped_column(String(64), ForeignKey("principals.principal_id"), index=True)
    issuance_type: Mapped[str] = mapped_column(String(32), default="platform")
    decision: Mapped[str] = mapped_column(String(32), default="issued")
    decision_reason_code: Mapped[str] = mapped_column(String(64), default="ok")
    issued_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class IdentityAuditEvent(Base):
    __tablename__ = "identity_audit_events"

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_domain_id: Mapped[str] = mapped_column(String(64), index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    actor: Mapped[str] = mapped_column(String(128))
    correlation_id: Mapped[str] = mapped_column(String(128), index=True)
    payload_summary: Mapped[str] = mapped_column(Text)
    critical: Mapped[bool] = mapped_column(Boolean, default=False)
    emitted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
