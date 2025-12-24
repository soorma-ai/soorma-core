"""Tests for database utility functions (without requiring PostgreSQL)."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from memory_service.core.database import (
    ensure_tenant_exists,
    ensure_user_exists,
    set_session_context,
)


class TestLazyPopulation:
    """Test suite for lazy population logic."""

    @pytest.mark.asyncio
    async def test_ensure_tenant_exists_creates_tenant(self):
        """Test ensure_tenant_exists executes INSERT statement."""
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()
        
        tenant_id = "00000000-0000-0000-0000-000000000000"
        
        await ensure_tenant_exists(mock_session, tenant_id)
        
        # Verify SQL was executed
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()
        
        # Verify SQL contains tenant_id
        call_args = mock_session.execute.call_args[0][0]
        assert tenant_id in str(call_args)
        assert "INSERT INTO tenants" in str(call_args)
        assert "ON CONFLICT" in str(call_args)

    @pytest.mark.asyncio
    async def test_ensure_user_exists_creates_user_and_tenant(self):
        """Test ensure_user_exists creates both user and tenant."""
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()
        
        tenant_id = "00000000-0000-0000-0000-000000000000"
        user_id = "11111111-1111-1111-1111-111111111111"
        
        await ensure_user_exists(mock_session, tenant_id, user_id)
        
        # Should execute twice: tenant + user
        assert mock_session.execute.call_count == 2
        assert mock_session.commit.call_count == 2
        
        # First call should be tenant
        first_call = mock_session.execute.call_args_list[0][0][0]
        assert "INSERT INTO tenants" in str(first_call)
        
        # Second call should be user
        second_call = mock_session.execute.call_args_list[1][0][0]
        assert "INSERT INTO users" in str(second_call)
        assert user_id in str(second_call)

    @pytest.mark.asyncio
    async def test_set_session_context_calls_ensure_user(self):
        """Test set_session_context ensures user exists before setting variables."""
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()
        
        tenant_id = "00000000-0000-0000-0000-000000000000"
        user_id = "11111111-1111-1111-1111-111111111111"
        
        await set_session_context(mock_session, tenant_id, user_id)
        
        # Should call: 
        # 1. INSERT tenant
        # 2. INSERT user
        # 3. SET app.current_tenant
        # 4. SET app.current_user
        assert mock_session.execute.call_count == 4
        
        # Verify SET statements use quoted parameter names
        calls = [str(call[0][0]) for call in mock_session.execute.call_args_list]
        set_calls = [c for c in calls if "SET" in c]
        
        assert len(set_calls) == 2
        assert '"app.current_tenant"' in set_calls[0]
        assert '"app.current_user"' in set_calls[1]

    @pytest.mark.asyncio
    async def test_session_context_handles_errors(self):
        """Test set_session_context propagates errors."""
        mock_session = AsyncMock()
        mock_session.execute.side_effect = Exception("Database error")
        
        with pytest.raises(Exception, match="Database error"):
            await set_session_context(
                mock_session,
                "00000000-0000-0000-0000-000000000000",
                "11111111-1111-1111-1111-111111111111"
            )


class TestSessionVariableQuoting:
    """Test proper quoting of PostgreSQL session variables."""

    @pytest.mark.asyncio
    async def test_current_user_is_quoted(self):
        """Test that app.current_user is properly quoted (reserved keyword)."""
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()
        
        await set_session_context(
            mock_session,
            "00000000-0000-0000-0000-000000000000",
            "11111111-1111-1111-1111-111111111111"
        )
        
        # Find the SET app.current_user call
        calls = mock_session.execute.call_args_list
        set_user_call = None
        
        for call in calls:
            sql = str(call[0][0])
            if "current_user" in sql and "SET" in sql:
                set_user_call = sql
                break
        
        assert set_user_call is not None
        # Must be quoted to avoid PostgreSQL reserved keyword conflict
        assert '"app.current_user"' in set_user_call
        assert 'SET "app.current_user"' in set_user_call

    @pytest.mark.asyncio
    async def test_current_tenant_is_quoted(self):
        """Test that app.current_tenant is properly quoted for consistency."""
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()
        
        await set_session_context(
            mock_session,
            "00000000-0000-0000-0000-000000000000",
            "11111111-1111-1111-1111-111111111111"
        )
        
        # Find the SET app.current_tenant call
        calls = mock_session.execute.call_args_list
        set_tenant_call = None
        
        for call in calls:
            sql = str(call[0][0])
            if "current_tenant" in sql and "SET" in sql:
                set_tenant_call = sql
                break
        
        assert set_tenant_call is not None
        assert '"app.current_tenant"' in set_tenant_call


class TestUUIDFormatting:
    """Test UUID handling in SQL statements."""

    @pytest.mark.asyncio
    async def test_tenant_id_cast_to_uuid(self):
        """Test tenant_id is properly cast to UUID type."""
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()
        
        tenant_id = "00000000-0000-0000-0000-000000000000"
        
        await ensure_tenant_exists(mock_session, tenant_id)
        
        call_sql = str(mock_session.execute.call_args[0][0])
        # Should cast to UUID
        assert "::UUID" in call_sql or "UUID" in call_sql

    @pytest.mark.asyncio
    async def test_user_id_cast_to_uuid(self):
        """Test user_id is properly cast to UUID type."""
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()
        
        tenant_id = "00000000-0000-0000-0000-000000000000"
        user_id = "11111111-1111-1111-1111-111111111111"
        
        await ensure_user_exists(mock_session, tenant_id, user_id)
        
        # Check the user INSERT call (second call)
        user_call = str(mock_session.execute.call_args_list[1][0][0])
        assert "::UUID" in user_call or "UUID" in user_call
