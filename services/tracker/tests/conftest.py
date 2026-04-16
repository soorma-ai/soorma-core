"""Pytest configuration and fixtures for tracker service tests."""

import os
import pytest
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Request
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from tracker_service.models.db import Base
from tracker_service.core.db import get_db
from tracker_service.core.dependencies import get_tenant_context, TenantContext
from tracker_service.main import app


# Test database URL (in-memory SQLite for fast tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
os.environ.setdefault("SOORMA_AUTH_JWT_SECRET", "dev-identity-signing-key")


def build_auth_headers(
    platform_tenant_id: str = "spt_test-tenant",
    service_tenant_id: str = "st_test-tenant",
    service_user_id: str = "su_test-user",
    principal_id: str = "tracker-test-user",
    include_service_tenant_header: bool = True,
    include_user_header: bool = True,
) -> dict[str, str]:
    """Build JWT bearer headers plus compatibility alias headers for tracker tests."""
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
        "dev-identity-signing-key",
        algorithm="HS256",
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": platform_tenant_id,
    }
    if include_service_tenant_header:
        headers["X-Service-Tenant-ID"] = service_tenant_id
    if include_user_header:
        headers["X-User-ID"] = service_user_id
    return headers


@pytest.fixture(scope="function")
async def db_engine():
    """Create async database engine for testing."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(db_engine):
    """Create async database session for testing."""
    async_session_maker = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session_maker() as session:
        yield session


@pytest.fixture(scope="function")
def override_get_db(db_session):
    """Override tracker DB and tenant context dependencies in FastAPI app."""

    async def _get_test_db():
        yield db_session

    async def _get_test_tenant_context(request: Request):
        yield TenantContext(
            platform_tenant_id=request.headers.get("X-Tenant-ID") or "spt_test-default",
            service_tenant_id=request.headers.get("X-Service-Tenant-ID"),
            service_user_id=request.headers.get("X-User-ID"),
            db=db_session,
        )
    
    app.dependency_overrides[get_db] = _get_test_db
    app.dependency_overrides[get_tenant_context] = _get_test_tenant_context
    yield
    app.dependency_overrides.clear()
