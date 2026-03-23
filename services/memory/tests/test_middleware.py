"""Tests for tenancy middleware integration (BR-U4-09).

Local middleware.py is deleted. TenancyMiddleware is imported from soorma_service_common.
These tests verify the import and integration contract.
"""

import pytest
from unittest.mock import Mock, MagicMock
from memory_service.core.dependencies import get_tenant_context, get_tenanted_db


class TestTenancyMiddlewareIntegration:
    """Verify soorma_service_common TenancyMiddleware is used (not local middleware)."""

    def test_tenancy_middleware_importable_from_soorma_service_common(self):
        """TenancyMiddleware must come from soorma_service_common, not local code."""
        from soorma_service_common import TenancyMiddleware
        assert TenancyMiddleware is not None

    def test_local_middleware_module_does_not_exist(self):
        """No local middleware module should exist (BR-U4-09)."""
        import importlib
        try:
            importlib.import_module("memory_service.core.middleware")
            raise AssertionError("Local middleware module should not exist")
        except ImportError:
            pass  # Expected

    def test_get_tenant_context_importable_from_dependencies(self):
        """get_tenant_context re-exported from soorma_service_common via dependencies."""
        assert get_tenant_context is not None

    def test_get_tenanted_db_importable_from_dependencies(self):
        """get_tenanted_db created from soorma_service_common factory via dependencies."""
        assert get_tenanted_db is not None

    def test_main_app_uses_tenancy_middleware(self):
        """memory_service main app registers TenancyMiddleware from soorma_service_common."""
        from memory_service.main import app
        from soorma_service_common import TenancyMiddleware

        middleware_types = [m.cls for m in app.user_middleware if hasattr(m, 'cls')]
        assert TenancyMiddleware in middleware_types


    @pytest.mark.skip("References removed get_user_id helper — stale test")
    def test_get_user_id_returns_none(self):
        """Test user ID returns None in v0.5.0 (comes from query params)."""
        request = Mock(spec=Request)
        request.state = Mock(spec=[])
        
        user_id = get_user_id(request)
        assert user_id is None

    @pytest.mark.skip("References removed get_user_id helper — stale test")
    def test_get_user_id_with_state_value(self):
        """Test user ID returns value if set in state (backward compatibility)."""
        request = Mock(spec=Request)
        request.state.user_id = "test-user-id"
        
        user_id = get_user_id(request)
        assert user_id == "test-user-id"
