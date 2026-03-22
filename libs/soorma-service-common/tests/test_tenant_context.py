"""
Tests for TenantContext and create_get_tenant_context factory.

RED phase: all tests assert real expected behavior.
They MUST fail with NotImplementedError until implementations are complete.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from soorma_service_common.tenant_context import TenantContext, create_get_tenant_context


class TestTenantContextDataclass:
    """TenantContext is a dataclass with four fields."""

    def test_can_be_instantiated_with_all_fields(self, mock_async_session):
        """TenantContext accepts all four fields at construction time."""
        ctx = TenantContext(
            platform_tenant_id="spt_acme",
            service_tenant_id="tenant-1",
            service_user_id="user-42",
            db=mock_async_session,
        )
        assert ctx.platform_tenant_id == "spt_acme"
        assert ctx.service_tenant_id == "tenant-1"
        assert ctx.service_user_id == "user-42"
        assert ctx.db is mock_async_session

    def test_optional_fields_accept_none(self, mock_async_session):
        """service_tenant_id and service_user_id accept None."""
        ctx = TenantContext(
            platform_tenant_id="spt_acme",
            service_tenant_id=None,
            service_user_id=None,
            db=mock_async_session,
        )
        assert ctx.service_tenant_id is None
        assert ctx.service_user_id is None


class TestCreateGetTenantContext:
    """create_get_tenant_context factory + the returned get_tenant_context dependency."""

    def test_factory_returns_callable(self, mock_async_session):
        """create_get_tenant_context returns a callable."""
        async def mock_get_tenanted_db():
            yield mock_async_session

        result = create_get_tenant_context(mock_get_tenanted_db)
        assert callable(result)

    @pytest.mark.asyncio
    async def test_returns_tenant_context_instance(
        self, make_mock_request, mock_async_session
    ):
        """get_tenant_context returns a TenantContext instance."""
        async def mock_get_tenanted_db():
            yield mock_async_session

        get_tenant_context = create_get_tenant_context(mock_get_tenanted_db)
        req = make_mock_request(
            platform_tenant_id="spt_acme",
            service_tenant_id="tenant-1",
            service_user_id="user-42",
        )

        result = await get_tenant_context(req, mock_async_session)
        assert isinstance(result, TenantContext)

    @pytest.mark.asyncio
    async def test_tenant_context_carries_platform_tenant_id(
        self, make_mock_request, mock_async_session
    ):
        """TenantContext.platform_tenant_id is read from request.state."""
        async def mock_get_tenanted_db():
            yield mock_async_session

        get_tenant_context = create_get_tenant_context(mock_get_tenanted_db)
        req = make_mock_request(platform_tenant_id="spt_acme")

        ctx = await get_tenant_context(req, mock_async_session)
        assert ctx.platform_tenant_id == "spt_acme"

    @pytest.mark.asyncio
    async def test_tenant_context_carries_service_tenant_id(
        self, make_mock_request, mock_async_session
    ):
        """TenantContext.service_tenant_id is read from request.state."""
        async def mock_get_tenanted_db():
            yield mock_async_session

        get_tenant_context = create_get_tenant_context(mock_get_tenanted_db)
        req = make_mock_request(service_tenant_id="tenant-org-1")

        ctx = await get_tenant_context(req, mock_async_session)
        assert ctx.service_tenant_id == "tenant-org-1"

    @pytest.mark.asyncio
    async def test_tenant_context_carries_none_when_service_tenant_absent(
        self, make_mock_request, mock_async_session
    ):
        """TenantContext.service_tenant_id is None when not set in request.state."""
        async def mock_get_tenanted_db():
            yield mock_async_session

        get_tenant_context = create_get_tenant_context(mock_get_tenanted_db)
        req = make_mock_request(service_tenant_id=None)

        ctx = await get_tenant_context(req, mock_async_session)
        assert ctx.service_tenant_id is None

    @pytest.mark.asyncio
    async def test_tenant_context_db_is_the_tenanted_session(
        self, make_mock_request, mock_async_session
    ):
        """TenantContext.db is the exact session passed in (already RLS-activated by get_tenanted_db)."""
        async def mock_get_tenanted_db():
            yield mock_async_session

        get_tenant_context = create_get_tenant_context(mock_get_tenanted_db)
        req = make_mock_request()

        ctx = await get_tenant_context(req, mock_async_session)
        assert ctx.db is mock_async_session
