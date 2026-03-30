"""
Tests for dependency functions: get_platform_tenant_id, get_service_tenant_id,
get_service_user_id, create_get_tenanted_db, set_config_for_session.

RED phase: all tests assert real expected behavior.
They MUST fail with NotImplementedError until implementations are complete.
"""
import pytest
from unittest.mock import AsyncMock, call, patch
from sqlalchemy import text
from fastapi import HTTPException

from soorma_service_common.dependencies import (
    create_require_user_context_dependency,
    create_get_tenanted_db,
    get_platform_tenant_id,
    get_service_tenant_id,
    get_service_user_id,
    require_user_context,
    set_config_for_session,
)
from soorma_service_common.tenant_context import TenantContext


class TestGetPlatformTenantId:
    """get_platform_tenant_id reads request.state.platform_tenant_id."""

    def test_returns_platform_tenant_id_from_state(self, make_mock_request):
        """Returns the platform_tenant_id stored on request.state."""
        req = make_mock_request(platform_tenant_id="spt_acme")
        result = get_platform_tenant_id(req)
        assert result == "spt_acme"

    def test_returns_string_type(self, make_mock_request):
        """Return value is always a str."""
        req = make_mock_request(platform_tenant_id="spt_xyz")
        result = get_platform_tenant_id(req)
        assert isinstance(result, str)


class TestGetServiceTenantId:
    """get_service_tenant_id reads request.state.service_tenant_id."""

    def test_returns_service_tenant_id_when_set(self, make_mock_request):
        """Returns service_tenant_id when present in request.state."""
        req = make_mock_request(service_tenant_id="tenant-org-1")
        result = get_service_tenant_id(req)
        assert result == "tenant-org-1"

    def test_returns_none_when_not_set(self, make_mock_request):
        """Returns None when service_tenant_id is None on request.state."""
        req = make_mock_request(service_tenant_id=None)
        result = get_service_tenant_id(req)
        assert result is None


class TestGetServiceUserId:
    """get_service_user_id reads request.state.service_user_id."""

    def test_returns_service_user_id_when_set(self, make_mock_request):
        """Returns service_user_id when present in request.state."""
        req = make_mock_request(service_user_id="user-42")
        result = get_service_user_id(req)
        assert result == "user-42"

    def test_returns_none_when_not_set(self, make_mock_request):
        """Returns None when service_user_id is None on request.state."""
        req = make_mock_request(service_user_id=None)
        result = get_service_user_id(req)
        assert result is None


class TestCreateGetTenantedDb:
    """create_get_tenanted_db factory + the returned get_tenanted_db dependency."""

    def test_factory_returns_callable(self):
        """create_get_tenanted_db returns a callable."""
        async def mock_get_db():
            yield AsyncMock()

        result = create_get_tenanted_db(mock_get_db)
        assert callable(result)

    @pytest.mark.asyncio
    async def test_get_tenanted_db_calls_set_config_three_times(
        self, make_mock_request, mock_async_session
    ):
        """get_tenanted_db executes set_config exactly 3 times on the session."""
        async def mock_get_db():
            yield mock_async_session

        get_tenanted_db = create_get_tenanted_db(mock_get_db)
        req = make_mock_request(
            platform_tenant_id="spt_acme",
            service_tenant_id="tenant-1",
            service_user_id="user-99",
        )

        # Call directly (bypassing FastAPI DI — mock_async_session passed as positional arg)
        collected = []
        async for session in get_tenanted_db(req, mock_async_session):
            collected.append(session)

        assert mock_async_session.execute.await_count == 3

    @pytest.mark.asyncio
    async def test_get_tenanted_db_sets_platform_tenant_id(
        self, make_mock_request, mock_async_session
    ):
        """get_tenanted_db calls set_config with app.platform_tenant_id."""
        async def mock_get_db():
            yield mock_async_session

        get_tenanted_db = create_get_tenanted_db(mock_get_db)
        req = make_mock_request(
            platform_tenant_id="spt_acme",
            service_tenant_id=None,
            service_user_id=None,
        )

        async for _ in get_tenanted_db(req, mock_async_session):
            pass

        # At least one execute call should have app.platform_tenant_id as the key
        call_args_list = mock_async_session.execute.call_args_list
        keys_used = []
        for c in call_args_list:
            # args[1] or kwargs['params'] holds the parameter dict
            params = c.args[1] if len(c.args) > 1 else c.kwargs.get("params", {})
            keys_used.append(params.get("key", ""))
        assert "app.platform_tenant_id" in keys_used

    @pytest.mark.asyncio
    async def test_get_tenanted_db_converts_none_to_empty_string(
        self, make_mock_request, mock_async_session
    ):
        """get_tenanted_db converts None service_tenant_id and service_user_id to ''."""
        async def mock_get_db():
            yield mock_async_session

        get_tenanted_db = create_get_tenanted_db(mock_get_db)
        req = make_mock_request(
            platform_tenant_id="spt_acme",
            service_tenant_id=None,
            service_user_id=None,
        )

        async for _ in get_tenanted_db(req, mock_async_session):
            pass

        call_args_list = mock_async_session.execute.call_args_list
        values_used = []
        for c in call_args_list:
            params = c.args[1] if len(c.args) > 1 else c.kwargs.get("params", {})
            values_used.append(params.get("value", "SENTINEL"))
        # None values must be converted to '' — NOT "None"
        assert "None" not in values_used
        assert "" in values_used  # service_tenant_id=None → ''

    @pytest.mark.asyncio
    async def test_get_tenanted_db_yields_the_session(
        self, make_mock_request, mock_async_session
    ):
        """get_tenanted_db yields the same DB session passed in."""
        async def mock_get_db():
            yield mock_async_session

        get_tenanted_db = create_get_tenanted_db(mock_get_db)
        req = make_mock_request()

        yielded = []
        async for session in get_tenanted_db(req, mock_async_session):
            yielded.append(session)

        assert len(yielded) == 1
        assert yielded[0] is mock_async_session

    @pytest.mark.asyncio
    async def test_set_config_uses_transaction_scope(
        self, make_mock_request, mock_async_session
    ):
        """set_config must use is_local=true (transaction-scoped, not session-scoped)."""
        async def mock_get_db():
            yield mock_async_session

        get_tenanted_db = create_get_tenanted_db(mock_get_db)
        req = make_mock_request()

        async for _ in get_tenanted_db(req, mock_async_session):
            pass

        # The SQL passed to execute must contain 'true' (not 'false')
        for c in mock_async_session.execute.call_args_list:
            sql_arg = c.args[0] if c.args else None
            assert sql_arg is not None, "execute called with no SQL argument"
            sql_str = str(sql_arg)
            assert "true" in sql_str.lower(), (
                f"set_config must use is_local=true for transaction scope. Got: {sql_str}"
            )


class TestSetConfigForSession:
    """set_config_for_session activates RLS on any AsyncSession (NATS path)."""

    @pytest.mark.asyncio
    async def test_calls_execute_three_times(self, mock_async_session):
        """set_config_for_session calls execute exactly 3 times."""
        await set_config_for_session(
            mock_async_session,
            platform_tenant_id="spt_acme",
            service_tenant_id="tenant-1",
            service_user_id="user-1",
        )
        assert mock_async_session.execute.await_count == 3

    @pytest.mark.asyncio
    async def test_converts_none_service_tenant_to_empty_string(self, mock_async_session):
        """service_tenant_id=None is converted to '' before calling set_config."""
        await set_config_for_session(
            mock_async_session,
            platform_tenant_id="spt_acme",
            service_tenant_id=None,
            service_user_id=None,
        )

        values_used = []
        for c in mock_async_session.execute.call_args_list:
            params = c.args[1] if len(c.args) > 1 else c.kwargs.get("params", {})
            values_used.append(params.get("value", "SENTINEL"))

        assert "None" not in values_used

    @pytest.mark.asyncio
    async def test_sets_all_three_session_variables(self, mock_async_session):
        """set_config_for_session sets app.platform_tenant_id, app.service_tenant_id, app.service_user_id."""
        await set_config_for_session(
            mock_async_session,
            platform_tenant_id="spt_acme",
            service_tenant_id="tenant-A",
            service_user_id="user-B",
        )

        keys_used = []
        for c in mock_async_session.execute.call_args_list:
            params = c.args[1] if len(c.args) > 1 else c.kwargs.get("params", {})
            keys_used.append(params.get("key", ""))

        assert "app.platform_tenant_id" in keys_used
        assert "app.service_tenant_id" in keys_used
        assert "app.service_user_id" in keys_used


class TestRequireUserContext:
    """require_user_context validates service tenant and user dimensions."""

    def test_returns_same_context_on_success(self):
        """Valid context passes through unchanged."""
        context = TenantContext(
            platform_tenant_id="spt_acme",
            service_tenant_id="tenant-1",
            service_user_id="user-1",
            db=AsyncMock(),
        )

        result = require_user_context(context)
        assert result is context

    def test_raises_400_when_service_tenant_missing(self):
        """Missing service tenant fails fast with generic 400 message."""
        context = TenantContext(
            platform_tenant_id="spt_acme",
            service_tenant_id=None,
            service_user_id="user-1",
            db=AsyncMock(),
        )

        with pytest.raises(HTTPException) as err:
            require_user_context(context)

        assert err.value.status_code == 400
        assert err.value.detail == "Missing required tenant identity context"

    def test_raises_400_when_service_user_missing(self):
        """Missing service user fails fast with generic 400 message."""
        context = TenantContext(
            platform_tenant_id="spt_acme",
            service_tenant_id="tenant-1",
            service_user_id=None,
            db=AsyncMock(),
        )

        with pytest.raises(HTTPException) as err:
            require_user_context(context)

        assert err.value.status_code == 400
        assert err.value.detail == "Missing required user identity context"

    def test_raises_400_when_service_tenant_whitespace(self):
        """Whitespace-only service tenant is invalid."""
        context = TenantContext(
            platform_tenant_id="spt_acme",
            service_tenant_id="   ",
            service_user_id="user-1",
            db=AsyncMock(),
        )

        with pytest.raises(HTTPException) as err:
            require_user_context(context)

        assert err.value.status_code == 400
        assert err.value.detail == "Missing required tenant identity context"

    def test_raises_400_when_service_user_whitespace(self):
        """Whitespace-only service user is invalid."""
        context = TenantContext(
            platform_tenant_id="spt_acme",
            service_tenant_id="tenant-1",
            service_user_id="\t\n",
            db=AsyncMock(),
        )

        with pytest.raises(HTTPException) as err:
            require_user_context(context)

        assert err.value.status_code == 400
        assert err.value.detail == "Missing required user identity context"

    def test_logs_correlation_and_request_id_when_provided(self):
        """Validation warning includes correlation_id/request_id when provided."""
        context = TenantContext(
            platform_tenant_id="spt_acme",
            service_tenant_id=None,
            service_user_id="user-1",
            db=AsyncMock(),
        )

        with patch("soorma_service_common.dependencies.LOGGER.warning") as warning_mock:
            with pytest.raises(HTTPException):
                require_user_context(
                    context,
                    correlation_id="corr-123",
                    request_id="req-456",
                )

        warning_mock.assert_called_once()
        kwargs = warning_mock.call_args.kwargs
        assert kwargs["extra"]["correlation_id"] == "corr-123"
        assert kwargs["extra"]["request_id"] == "req-456"


class TestCreateRequireUserContextDependency:
    """Factory tests for centralized user-context dependency adapter."""

    def test_factory_returns_callable(self):
        """Factory should return a callable FastAPI dependency."""

        def _mock_get_tenant_context():
            return None

        dependency = create_require_user_context_dependency(_mock_get_tenant_context)
        assert callable(dependency)

    def test_dependency_reads_headers_and_passes_ids_to_validation(self):
        """Adapter must extract request headers and delegate IDs to validator."""
        context = TenantContext(
            platform_tenant_id="spt_acme",
            service_tenant_id=None,
            service_user_id="user-1",
            db=AsyncMock(),
        )

        def _mock_get_tenant_context():
            return context

        dependency = create_require_user_context_dependency(_mock_get_tenant_context)

        request = AsyncMock()
        request.headers = {
            "X-Correlation-ID": "corr-789",
            "X-Request-ID": "req-101",
        }

        with patch("soorma_service_common.dependencies.LOGGER.warning") as warning_mock:
            with pytest.raises(HTTPException):
                dependency(request=request, context=context)

        warning_mock.assert_called_once()
        kwargs = warning_mock.call_args.kwargs
        assert kwargs["extra"]["correlation_id"] == "corr-789"
        assert kwargs["extra"]["request_id"] == "req-101"
