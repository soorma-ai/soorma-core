"""
Shared test fixtures for soorma-service-common tests.
"""
from typing import Optional
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from soorma_service_common.middleware import TenancyMiddleware


@pytest.fixture
def mock_async_session() -> AsyncMock:
    """Mock AsyncSession that tracks execute calls."""
    session = AsyncMock()
    return session


@pytest.fixture
def make_mock_request():
    """
    Factory fixture: create a mock Request with pre-populated request.state identity.

    Usage:
        req = make_mock_request(
            platform_tenant_id="spt_abc",
            service_tenant_id="tenant-1",
            service_user_id="user-1",
        )
    """

    def _make(
        platform_tenant_id: str = "spt_default",
        service_tenant_id: Optional[str] = None,
        service_user_id: Optional[str] = None,
    ) -> MagicMock:
        req = MagicMock(spec=Request)
        req.state = MagicMock()
        req.state.platform_tenant_id = platform_tenant_id
        req.state.service_tenant_id = service_tenant_id
        req.state.service_user_id = service_user_id
        return req

    return _make


@pytest.fixture
def make_test_app():
    """
    Factory fixture: create a FastAPI test app with TenancyMiddleware and a
    /test endpoint that returns request.state identity values as JSON.

    Usage:
        app = make_test_app()
        client = TestClient(app, raise_server_exceptions=False)
    """

    def _make() -> FastAPI:
        app = FastAPI()
        app.add_middleware(TenancyMiddleware)

        @app.get("/test")
        async def identity_endpoint(request: Request):
            return {
                "platform_tenant_id": request.state.platform_tenant_id,
                "service_tenant_id": request.state.service_tenant_id,
                "service_user_id": request.state.service_user_id,
            }

        @app.get("/health")
        async def health_endpoint():
            return {"status": "ok"}

        @app.get("/docs-check")
        async def docs_check(request: Request):
            # used to test non-bypass paths
            return {"path": request.url.path}

        return app

    return _make
