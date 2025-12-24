"""Tests for middleware and tenancy logic."""

import pytest
from unittest.mock import Mock, AsyncMock
from fastapi import Request
from memory_service.core.middleware import (
    TenancyMiddleware,
    get_tenant_id,
    get_user_id,
)


class TestTenancyMiddleware:
    """Test suite for TenancyMiddleware."""

    @pytest.mark.asyncio
    async def test_middleware_sets_default_tenant(self):
        """Test middleware sets default tenant ID in single-tenant mode."""
        middleware = TenancyMiddleware(app=Mock())
        
        request = Mock(spec=Request)
        request.url.path = "/v1/memory/episodic"
        request.state = Mock()
        
        call_next = AsyncMock(return_value=Mock())
        
        await middleware.dispatch(request, call_next)
        
        # Verify tenant_id was set
        assert hasattr(request.state, 'tenant_id')
        assert request.state.tenant_id == "00000000-0000-0000-0000-000000000000"
        call_next.assert_called_once_with(request)

    @pytest.mark.asyncio
    async def test_middleware_skips_health_endpoint(self):
        """Test middleware skips processing for health check."""
        middleware = TenancyMiddleware(app=Mock())
        
        request = Mock(spec=Request)
        request.url.path = "/health"
        request.state = Mock()
        
        call_next = AsyncMock(return_value=Mock())
        
        await middleware.dispatch(request, call_next)
        
        # tenant_id should not be set for health check
        call_next.assert_called_once_with(request)

    @pytest.mark.asyncio
    async def test_middleware_skips_docs_endpoints(self):
        """Test middleware skips processing for documentation endpoints."""
        middleware = TenancyMiddleware(app=Mock())
        
        for path in ["/docs", "/openapi.json", "/redoc"]:
            request = Mock(spec=Request)
            request.url.path = path
            request.state = Mock()
            
            call_next = AsyncMock(return_value=Mock())
            
            await middleware.dispatch(request, call_next)
            call_next.assert_called_once_with(request)

    def test_get_tenant_id_from_state(self):
        """Test retrieving tenant ID from request state."""
        request = Mock(spec=Request)
        request.state.tenant_id = "test-tenant-id"
        
        tenant_id = get_tenant_id(request)
        assert tenant_id == "test-tenant-id"

    def test_get_tenant_id_default_fallback(self):
        """Test tenant ID falls back to default when not in state."""
        request = Mock(spec=Request)
        request.state = Mock(spec=[])  # Empty state
        
        tenant_id = get_tenant_id(request)
        assert tenant_id == "00000000-0000-0000-0000-000000000000"

    def test_get_user_id_returns_none(self):
        """Test user ID returns None in v0.5.0 (comes from query params)."""
        request = Mock(spec=Request)
        request.state = Mock(spec=[])
        
        user_id = get_user_id(request)
        assert user_id is None

    def test_get_user_id_with_state_value(self):
        """Test user ID returns value if set in state (backward compatibility)."""
        request = Mock(spec=Request)
        request.state.user_id = "test-user-id"
        
        user_id = get_user_id(request)
        assert user_id == "test-user-id"
