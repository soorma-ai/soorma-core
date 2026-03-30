"""Shared identity helpers for CRUD predicates."""


def require_platform_tenant_id(platform_tenant_id: str) -> None:
    """Fail closed when platform tenant context is missing."""
    assert platform_tenant_id, "platform_tenant_id is required"


def scoped_identity_filters(
    model,
    platform_tenant_id: str,
    service_tenant_id: str,
    service_user_id: str,
):
    """Build full identity tuple filters for tenant and user scoped rows."""
    return (
        model.platform_tenant_id == platform_tenant_id,
        model.service_tenant_id == service_tenant_id,
        model.service_user_id == service_user_id,
    )
