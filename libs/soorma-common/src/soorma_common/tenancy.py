"""
Platform tenancy constants for Soorma.

Provides the default platform tenant ID used throughout soorma-core for
development and testing. Override via the SOORMA_PLATFORM_TENANT_ID env var.
"""

import os

# WARNING: For development/testing only.
# MUST NOT be used in production once the Identity Service is implemented.
# At that point, all platform_tenant_id values must come from authenticated
# Identity Service tokens — never from this constant.
DEFAULT_PLATFORM_TENANT_ID: str = (
    os.environ.get("SOORMA_PLATFORM_TENANT_ID") or "spt_00000000-0000-0000-0000-000000000000"
)
