"""FastAPI dependencies for tracker tenancy and request context."""

from soorma_service_common import (
    TenantContext,
    create_get_tenant_context,
    create_get_tenanted_db,
)
from tracker_service.core.db import get_db

# Bind tracker get_db to tenancy-aware DB dependency.
get_tenanted_db = create_get_tenanted_db(get_db)

# Provide bundled identity + tenanted db context for route handlers.
get_tenant_context = create_get_tenant_context(get_tenanted_db)

__all__ = ["TenantContext", "get_tenant_context", "get_tenanted_db"]
