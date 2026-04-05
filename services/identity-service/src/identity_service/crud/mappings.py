"""Mapping and binding repository."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from identity_service.models.domain import ExternalIdentityBinding


class MappingRepository:
    """External identity mapping persistence repository."""

    async def evaluate_collision(self, db: AsyncSession, payload: dict[str, object]) -> dict[str, object]:
        """Evaluate collision against persisted bindings and persist if allowed."""
        tenant_domain_id = str(payload["tenant_domain_id"])
        source_issuer_id = str(payload["source_issuer_id"])
        external_identity_key = str(payload["external_identity_key"])
        canonical_identity_key = str(payload["canonical_identity_key"])
        principal_id = str(payload["principal_id"])
        override_requested = bool(payload.get("override_requested", False))

        existing_stmt = select(ExternalIdentityBinding).where(
            ExternalIdentityBinding.tenant_domain_id == tenant_domain_id,
            ExternalIdentityBinding.source_issuer_id == source_issuer_id,
            ExternalIdentityBinding.external_identity_key == external_identity_key,
        )
        existing_row = (await db.execute(existing_stmt)).scalars().first()

        if existing_row is None:
            db.add(
                ExternalIdentityBinding(
                    binding_id=str(uuid4()),
                    tenant_domain_id=tenant_domain_id,
                    source_issuer_id=source_issuer_id,
                    external_identity_key=external_identity_key,
                    canonical_identity_key=canonical_identity_key,
                    principal_id=principal_id,
                    verification_state="verified",
                    created_at=datetime.now(timezone.utc).replace(tzinfo=None),
                    updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
                )
            )
            await db.commit()
            return {"decision": "allow", "reason_code": "new_binding_created"}

        if (
            existing_row.principal_id == principal_id
            and existing_row.canonical_identity_key == canonical_identity_key
        ):
            return {"decision": "allow", "reason_code": "binding_unchanged"}

        if not override_requested:
            return {"decision": "deny", "reason_code": "collision_no_override"}

        existing_row.principal_id = principal_id
        existing_row.canonical_identity_key = canonical_identity_key
        existing_row.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await db.commit()
        return {"decision": "allow", "reason_code": "override_accepted"}


mapping_repository = MappingRepository()
