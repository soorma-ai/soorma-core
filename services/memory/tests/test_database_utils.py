"""Tests for database utilities.

Note: ensure_tenant_exists, ensure_user_exists, and set_session_context were
removed in the multi-tenancy migration (migration 008). Tenant/user context is
now handled by PostgreSQL RLS and TenancyMiddleware from soorma_service_common.
"""

import pytest


class TestDatabaseUtils:
    """Verify removed database utility functions are no longer importable."""

    def test_ensure_tenant_exists_removed(self):
        """ensure_tenant_exists should no longer exist in core.database."""
        import importlib
        module = importlib.import_module("memory_service.core.database")
        assert not hasattr(module, "ensure_tenant_exists"), (
            "ensure_tenant_exists should have been removed in migration 008"
        )

    def test_ensure_user_exists_removed(self):
        """ensure_user_exists should no longer exist in core.database."""
        import importlib
        module = importlib.import_module("memory_service.core.database")
        assert not hasattr(module, "ensure_user_exists"), (
            "ensure_user_exists should have been removed in migration 008"
        )

    def test_set_session_context_removed(self):
        """set_session_context should no longer exist in core.database."""
        import importlib
        module = importlib.import_module("memory_service.core.database")
        assert not hasattr(module, "set_session_context"), (
            "set_session_context should have been removed in migration 008"
        )

    def test_get_db_still_exists(self):
        """get_db (bare session factory) must still exist for admin endpoints."""
        from memory_service.core.database import get_db
        assert get_db is not None
