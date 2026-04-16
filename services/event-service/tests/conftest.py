"""
Pytest configuration for Event Service tests.
"""
import pytest
import os
from datetime import datetime, timedelta, timezone

import jwt

# Set test environment variables
os.environ["EVENT_ADAPTER"] = "memory"
os.environ["DEBUG"] = "true"
os.environ.setdefault("SOORMA_AUTH_JWT_SECRET", "dev-identity-signing-key")


@pytest.fixture(scope="session")
def event_loop_policy():
    """Use default event loop policy."""
    import asyncio
    return asyncio.DefaultEventLoopPolicy()


@pytest.fixture
def tenancy_headers():
    """Default authenticated headers used for protected event-service routes."""
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": "event-test-user",
            "platform_tenant_id": "spt_test",
            "service_tenant_id": "st_test-tenant",
            "service_user_id": "su_test-user",
            "principal_id": "event-test-user",
            "principal_type": "service",
            "roles": ["service"],
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(hours=1)).timestamp()),
        },
        os.environ["SOORMA_AUTH_JWT_SECRET"],
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


def build_auth_headers(
    platform_tenant_id: str = "spt_test",
    service_tenant_id: str = "st_test-tenant",
    service_user_id: str = "su_test-user",
    principal_id: str = "event-test-user",
) -> dict[str, str]:
    """Build JWT bearer headers for event-service tests."""
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": principal_id,
            "platform_tenant_id": platform_tenant_id,
            "service_tenant_id": service_tenant_id,
            "service_user_id": service_user_id,
            "principal_id": principal_id,
            "principal_type": "service",
            "roles": ["service"],
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(hours=1)).timestamp()),
        },
        os.environ["SOORMA_AUTH_JWT_SECRET"],
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}
