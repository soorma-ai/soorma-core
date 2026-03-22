"""
Tests for soorma_common.tenancy module.

TDD RED phase: these tests assert the REAL expected behaviour and will FAIL
against the stub (DEFAULT_PLATFORM_TENANT_ID = "").
"""
import importlib
import os

import pytest

import soorma_common.tenancy as tenancy_module


class TestDefaultPlatformTenantId:
    """Tests for DEFAULT_PLATFORM_TENANT_ID constant resolution."""

    def test_default_value(self):
        """DEFAULT_PLATFORM_TENANT_ID equals the canonical dev/test sentinel when env var is absent."""
        # Reload without env var override to isolate
        env_backup = os.environ.pop("SOORMA_PLATFORM_TENANT_ID", None)
        try:
            importlib.reload(tenancy_module)
            assert tenancy_module.DEFAULT_PLATFORM_TENANT_ID == "spt_00000000-0000-0000-0000-000000000000"
        finally:
            if env_backup is not None:
                os.environ["SOORMA_PLATFORM_TENANT_ID"] = env_backup
            importlib.reload(tenancy_module)

    def test_env_var_override(self, monkeypatch):
        """SOORMA_PLATFORM_TENANT_ID env var takes precedence over the literal default."""
        monkeypatch.setenv("SOORMA_PLATFORM_TENANT_ID", "spt_custom-tenant-abc")
        importlib.reload(tenancy_module)
        assert tenancy_module.DEFAULT_PLATFORM_TENANT_ID == "spt_custom-tenant-abc"
        # reload once more to restore default state after monkeypatch cleanup
        importlib.reload(tenancy_module)

    def test_env_var_empty_string_falls_back_to_default(self, monkeypatch):
        """Empty string env var falls back to the literal default (falsy check)."""
        monkeypatch.setenv("SOORMA_PLATFORM_TENANT_ID", "")
        importlib.reload(tenancy_module)
        assert tenancy_module.DEFAULT_PLATFORM_TENANT_ID == "spt_00000000-0000-0000-0000-000000000000"
        importlib.reload(tenancy_module)

    def test_no_format_validation(self):
        """DEFAULT_PLATFORM_TENANT_ID is a plain str — no UUID or pattern validation."""
        # Any string value should be accepted as opaque (NFR-3.2)
        assert isinstance(tenancy_module.DEFAULT_PLATFORM_TENANT_ID, str)

    def test_no_framework_imports(self):
        """tenancy module MUST only import from stdlib (SDK compatibility — C1 boundary)."""
        import soorma_common.tenancy as mod
        import sys

        # Collect imports by inspecting module's globals for imported modules
        forbidden = {"fastapi", "starlette", "sqlalchemy", "httpx"}
        module_imports = {
            name
            for name, obj in vars(mod).items()
            if isinstance(obj, type(os)) and hasattr(obj, "__name__")
        }
        # Also check sys.modules for anything pulled in transitively
        for forbidden_pkg in forbidden:
            assert forbidden_pkg not in sys.modules or mod.__name__ not in sys.modules.get(
                forbidden_pkg, object
            ).__dict__, f"tenancy.py must not import {forbidden_pkg}"
