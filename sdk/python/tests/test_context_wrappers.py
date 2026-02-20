"""
Tests for PlatformContext wrapper classes.

These tests cover the wrapper layer that agents interact with,
ensuring proper delegation, error handling, and lifecycle management.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

from soorma.context import MemoryClient, BusClient, RegistryClient, PlatformContext
from soorma.memory.client import MemoryClient as MemoryServiceClient
from soorma.registry.client import RegistryClient as RegistryServiceClient
from soorma.events import EventClient
from soorma.ai.event_toolkit import EventToolkit
from soorma_common.models import (
    SemanticMemoryResponse,
    EpisodicMemoryResponse,
    ProceduralMemoryResponse,
    WorkingMemoryResponse,
)


class TestPlatformContext:
    """Tests for PlatformContext initialization and toolkit integration."""
    
    def test_context_has_toolkit(self):
        """Test that PlatformContext includes EventToolkit."""
        context = PlatformContext()
        
        assert hasattr(context, 'toolkit')
        assert isinstance(context.toolkit, EventToolkit)
        assert context.toolkit.registry_url == context.registry.base_url
    
    def test_context_from_env_has_toolkit(self):
        """Test that from_env() includes EventToolkit."""
        context = PlatformContext.from_env()
        
        assert hasattr(context, 'toolkit')
        assert isinstance(context.toolkit, EventToolkit)
    
    def test_toolkit_shares_registry_client(self):
        """Test that toolkit reuses the context's registry client."""
        context = PlatformContext()
        
        # Toolkit should reference the same registry client
        assert context.toolkit._client is context.registry
        # Toolkit should not own the client (won't close it independently)
        assert context.toolkit._owns_client is False
    
    @pytest.mark.asyncio
    async def test_toolkit_no_async_with_needed(self):
        """Test that toolkit methods work directly without async with when using context."""
        context = PlatformContext()
        
        # Mock the registry client's get_events_by_topic method
        with patch.object(
            context.registry,
            'get_events_by_topic',
            new_callable=AsyncMock,
            return_value=[]
        ) as mock_method:
            # Should work WITHOUT async with when using context.toolkit
            from soorma_common.events import EventTopic
            events = await context.toolkit.discover_events(topic=EventTopic.ACTION_REQUESTS)
            
            assert events == []
            mock_method.assert_called_once_with("action-requests")


class TestMemoryClientWrapper:
    """Tests for the MemoryClient wrapper in context.py."""
    
    @pytest.mark.asyncio
    async def test_store_knowledge_with_service(self):
        """Test store_knowledge() delegates to service client."""
        # Setup
        mock_client = AsyncMock(spec=MemoryServiceClient)
        mock_response = SemanticMemoryResponse(
            id="sem-123",
            tenant_id="tenant-1",
            user_id="user-1",
            content="Test knowledge",
            external_id=None,
            is_public=False,
            metadata={"source": "test"},
            created_at="2025-12-23T10:00:00Z",
            updated_at="2025-12-23T10:00:00Z",
            score=None
        )
        mock_client.store_knowledge = AsyncMock(return_value=mock_response)
        
        wrapper = MemoryClient(base_url="http://memory:8002")
        wrapper._client = mock_client
        
        # Execute
        result = await wrapper.store_knowledge(
            content="Test knowledge",
            user_id="user-1",
            metadata={"source": "test"}
        )
        
        # Verify
        assert result == "sem-123"
        mock_client.store_knowledge.assert_called_once_with(
            "Test knowledge", user_id="user-1", metadata={"source": "test"}
        )
    
    @pytest.mark.asyncio
    async def test_search_knowledge_with_service(self):
        """Test search_knowledge() delegates to service client."""
        # Setup
        mock_client = AsyncMock(spec=MemoryServiceClient)
        mock_memory = SemanticMemoryResponse(
            id="mem-1",
            tenant_id="tenant-1",
            user_id="user-1",
            content="Test content",
            external_id=None,
            is_public=False,
            metadata={},
            created_at="2025-12-23T10:00:00Z",
            updated_at="2025-12-23T10:00:00Z",
            score=0.95
        )
        mock_client.search_knowledge = AsyncMock(return_value=[mock_memory])
        
        wrapper = MemoryClient(base_url="http://memory:8002")
        wrapper._client = mock_client
        
        # Execute
        results = await wrapper.search_knowledge(query="test query", user_id="user-1", limit=5)
        
        # Verify
        assert len(results) == 1
        assert results[0]["id"] == "mem-1"
        assert results[0]["content"] == "Test content"
        assert results[0]["score"] == 0.95
        mock_client.search_knowledge.assert_called_once_with("test query", user_id="user-1", limit=5)
    
    @pytest.mark.asyncio
    async def test_search_interactions_with_service(self):
        """Test search_interactions() delegates to service client."""
        # Setup
        mock_client = AsyncMock(spec=MemoryServiceClient)
        mock_episode = EpisodicMemoryResponse(
            id="ep-1",
            tenant_id="tenant-1",
            user_id="user-1",
            agent_id="agent-1",
            role="assistant",
            content="Relevant interaction",
            metadata={},
            created_at="2025-12-23T10:00:00Z",
            score=0.88
        )
        mock_client.search_interactions = AsyncMock(return_value=[mock_episode])
        
        wrapper = MemoryClient(base_url="http://memory:8002")
        wrapper._client = mock_client
        wrapper._use_local = False
        
        # Execute
        results = await wrapper.search_interactions(
            agent_id="agent-1",
            query="relevant",
            user_id="test-user",
            limit=5
        )
        
        # Verify
        assert len(results) == 1
        assert results[0]["id"] == "ep-1"
        assert results[0]["content"] == "Relevant interaction"
        assert results[0]["score"] == 0.88
        mock_client.search_interactions.assert_called_once_with(
            "agent-1", "relevant", "test-user", limit=5
        )
    
    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_close_with_client(self):
        """Test closing MemoryClient when client exists."""
        # Setup
        mock_memory_service = AsyncMock(spec=MemoryServiceClient)
        wrapper = MemoryClient(base_url="http://memory:8002")
        wrapper._client = mock_memory_service
        wrapper._use_local = False
        
        # Execute
        await wrapper.close()
        
        # Verify
        mock_memory_service.close.assert_called_once()
        assert wrapper._client is None
    
    @pytest.mark.asyncio
    async def test_close_without_client(self):
        """Test closing MemoryClient when no client exists."""
        # Setup
        wrapper = MemoryClient(base_url="http://memory:8002")
        wrapper._client = None
        wrapper._use_local = True
        
        # Execute - should not raise
        await wrapper.close()
        
        # Verify
        assert wrapper._client is None
    
    @pytest.mark.asyncio
    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_log_interaction_with_service(self):
        """Test log_interaction() delegates to service client."""
        # Setup
        mock_client = AsyncMock(spec=MemoryServiceClient)
        mock_client.log_interaction = AsyncMock(return_value="ep-123")
        
        wrapper = MemoryClient(base_url="http://memory:8002")
        wrapper._client = mock_client
        wrapper._use_local = False
        
        # Execute
        result = await wrapper.log_interaction(
            agent_id="agent-1",
            role="assistant",
            content="Completed research task",
            user_id="test-user",
            metadata={"task_id": "task-1"}
        )
        
        # Verify
        assert result is True
        # Verify positional arguments (not keyword args)
        mock_client.log_interaction.assert_called_once_with(
            "agent-1",
            "assistant",
            "Completed research task",
            "test-user",
            {"task_id": "task-1"}
        )
    
    @pytest.mark.asyncio
    async def test_get_recent_history_with_service(self):
        """Test get_recent_history() delegates to service client."""
        # Setup
        mock_client = AsyncMock(spec=MemoryServiceClient)
        mock_episode = EpisodicMemoryResponse(
            id="ep-1",
            tenant_id="tenant-1",
            user_id="user-1",
            agent_id="agent-1",
            role="assistant",
            content="Completed task",
            metadata={},
            created_at="2025-12-23T10:00:00Z",
            score=None
        )
        mock_client.get_recent_history = AsyncMock(return_value=[mock_episode])
        
        wrapper = MemoryClient(base_url="http://memory:8002")
        wrapper._client = mock_client
        wrapper._use_local = False
        
        # Execute
        results = await wrapper.get_recent_history(
            agent_id="agent-1",
            user_id="test-user",
            limit=10
        )
        
        # Verify
        assert len(results) == 1
        assert results[0]["id"] == "ep-1"
        assert results[0]["role"] == "assistant"
        mock_client.get_recent_history.assert_called_once_with("agent-1", "test-user", limit=10)
    
    @pytest.mark.asyncio
    async def test_get_relevant_skills_with_service(self):
        """Test get_relevant_skills() delegates to service client."""
        # Setup
        mock_client = AsyncMock(spec=MemoryServiceClient)
        mock_skill = ProceduralMemoryResponse(
            id="skill-1",
            tenant_id="tenant-1",
            user_id="user-1",
            agent_id="agent-1",
            procedure_type="skill",
            content="How to analyze data",
            trigger_condition="data analysis",
            created_at="2025-12-23T10:00:00Z",
            score=0.88
        )
        mock_client.get_relevant_skills = AsyncMock(return_value=[mock_skill])
        
        wrapper = MemoryClient(base_url="http://memory:8002")
        wrapper._client = mock_client
        wrapper._use_local = False
        
        # Execute
        results = await wrapper.get_relevant_skills(
            agent_id="agent-1",
            context="need to analyze data",
            user_id="test-user",
            limit=3
        )
        
        # Verify
        assert len(results) == 1
        assert results[0]["id"] == "skill-1"
        assert results[0]["procedure_type"] == "skill"
        assert results[0]["score"] == 0.88
        mock_client.get_relevant_skills.assert_called_once_with(
            "agent-1", "need to analyze data", "test-user", limit=3
        )
    
    @pytest.mark.asyncio
    async def test_ensure_client_creates_client(self):
        """Test _ensure_client() creates client if not exists."""
        # Setup
        wrapper = MemoryClient(base_url="http://memory:8002")
        wrapper._client = None
        
        # Execute
        with patch('soorma.context.MemoryServiceClient') as mock_client_class:
            mock_instance = AsyncMock(spec=MemoryServiceClient)
            mock_instance.health = AsyncMock()
            mock_client_class.return_value = mock_instance
            
            client = await wrapper._ensure_client()
            
            # Verify
            assert client == mock_instance
            assert wrapper._client == mock_instance
            mock_client_class.assert_called_once_with(base_url="http://memory:8002")
            mock_instance.health.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_ensure_client_returns_existing(self):
        """Test _ensure_client() returns existing client."""
        # Setup
        mock_client = AsyncMock(spec=MemoryServiceClient)
        wrapper = MemoryClient(base_url="http://memory:8002")
        wrapper._client = mock_client
        
        # Execute
        client = await wrapper._ensure_client()
        
        # Verify
        assert client == mock_client
    
    @pytest.mark.asyncio
    async def test_store_with_service(self):
        """Test store() delegates to service client for working memory."""
        # Setup
        mock_client = AsyncMock(spec=MemoryServiceClient)
        mock_client.set_plan_state = AsyncMock()
        
        wrapper = MemoryClient(base_url="http://memory:8002")
        wrapper._client = mock_client
        
        # Execute
        result = await wrapper.store(
            "key1", 
            {"data": "value"}, 
            plan_id="plan-1",
            tenant_id="test-tenant",
            user_id="test-user"
        )
        
        # Verify - value passed directly (wrapping happens in set_plan_state)
        assert result is True
        mock_client.set_plan_state.assert_called_once_with(
            "plan-1", "key1", {"data": "value"}, "test-tenant", "test-user"
        )
    
    @pytest.mark.asyncio
    async def test_retrieve_with_service(self):
        """Test retrieve() delegates to service client."""
        # Setup
        mock_client = AsyncMock(spec=MemoryServiceClient)
        mock_response = WorkingMemoryResponse(
            id="mem-1",
            tenant_id="tenant-1",
            plan_id="plan-1",
            key="key1",
            value={"data": "value"},  # Service returns value directly
            updated_at="2025-12-23T10:00:00Z"
        )
        mock_client.get_plan_state = AsyncMock(return_value=mock_response)
        
        wrapper = MemoryClient(base_url="http://memory:8002")
        wrapper._client = mock_client
        
        # Execute
        result = await wrapper.retrieve(
            "key1", 
            plan_id="plan-1",
            tenant_id="test-tenant",
            user_id="test-user"
        )
        
        # Verify - value returned directly
        assert result == {"data": "value"}
        mock_client.get_plan_state.assert_called_once_with(
            "plan-1", "key1", "test-tenant", "test-user"
        )
    
    @pytest.mark.asyncio
    async def test_create_plan_delegates_to_service(self):
        """Test create_plan() wrapper delegates to service client."""
        # Setup
        mock_client = AsyncMock(spec=MemoryServiceClient)
        from soorma_common.models import PlanSummary
        mock_response = PlanSummary(
            plan_id="plan-abc",
            tenant_id="tenant-1",
            user_id="user-1",
            session_id="session-1",
            goal_event="research.goal",
            goal_data={"topic": "AI agents"},
            status="pending",
            parent_plan_id=None,
            created_at="2026-02-19T10:00:00Z",
            updated_at="2026-02-19T10:00:00Z"
        )
        mock_client.create_plan = AsyncMock(return_value=mock_response)
        
        wrapper = MemoryClient(base_url="http://memory:8002")
        wrapper._client = mock_client
        
        # Execute
        result = await wrapper.create_plan(
            plan_id="plan-abc",
            goal_event="research.goal",
            goal_data={"topic": "AI agents"},
            tenant_id="tenant-1",
            user_id="user-1",
            session_id="session-1",
        )
        
        # Verify
        assert result.plan_id == "plan-abc"
        assert result.goal_event == "research.goal"
        assert result.status == "pending"
        mock_client.create_plan.assert_called_once_with(
            plan_id="plan-abc",
            goal_event="research.goal",
            goal_data={"topic": "AI agents"},
            tenant_id="tenant-1",
            user_id="user-1",
            session_id="session-1",
            parent_plan_id=None,
        )


class TestBusClientWrapper:
    """Tests for the BusClient wrapper in context.py."""
    
    @pytest.mark.asyncio
    async def test_publish_delegates_to_event_client(self):
        """Test publish() delegates to event_client."""
        # Setup
        mock_event_client = AsyncMock(spec=EventClient)
        mock_event_client.publish = AsyncMock(return_value="event-123")
        
        wrapper = BusClient(event_client=mock_event_client)
        
        # Execute
        event_id = await wrapper.publish(
            event_type="task.completed",
            data={"task_id": "task-1"},
            topic="tasks",
            correlation_id="corr-1"
        )
        
        # Verify
        assert event_id == "event-123"
        # Check that publish was called with expected parameters
        call_kwargs = mock_event_client.publish.call_args.kwargs
        assert call_kwargs["event_type"] == "task.completed"
        assert call_kwargs["topic"] == "tasks"
        assert call_kwargs["data"] == {"task_id": "task-1"}
        assert call_kwargs["correlation_id"] == "corr-1"
    
    @pytest.mark.asyncio
    async def test_publish_requires_explicit_topic(self):
        """Test publish() requires explicit topic parameter (Stage 1)."""
        # Setup
        mock_event_client = AsyncMock(spec=EventClient)
        mock_event_client.publish = AsyncMock(return_value="event-456")
        
        wrapper = BusClient(event_client=mock_event_client)
        
        # Execute
        event_id = await wrapper.publish(
            event_type="user.registered",
            topic="users",
            data={"user_id": "user-1"}
        )
        
        # Verify
        assert event_id == "event-456"
        call_kwargs = mock_event_client.publish.call_args.kwargs
        assert call_kwargs["event_type"] == "user.registered"
        assert call_kwargs["topic"] == "users"
        assert call_kwargs["data"] == {"user_id": "user-1"}
        assert event_id == "event-456"
        # Should be called with topic=None (auto-inferred)
        call_kwargs = mock_event_client.publish.call_args.kwargs
        assert call_kwargs["event_type"] == "user.registered"
        assert call_kwargs["data"] == {"user_id": "user-1"}


class TestIntegrationScenarios:
    """Integration tests for common usage patterns."""
    
    @pytest.mark.asyncio
    async def test_memory_client_lifecycle(self):
        """Test full lifecycle: create, use, close."""
        # Setup
        wrapper = MemoryClient(base_url="http://memory:8002")
        wrapper._use_local = True
        
        # Execute - store and retrieve
        await wrapper.store("key1", {"value": 100})
        result = await wrapper.retrieve("key1")
        assert result == {"value": 100}
        
        # Execute - close
        await wrapper.close()
        assert wrapper._client is None
    
    @pytest.mark.asyncio
    async def test_memory_client_error_recovery(self):
        """Test error handling and fallback behavior."""
        # Setup
        mock_client = AsyncMock(spec=MemoryServiceClient)
        mock_client.health = AsyncMock(side_effect=Exception("Connection failed"))
        
        wrapper = MemoryClient(base_url="http://memory:8002")
        wrapper._client = None
        
        # Execute - should catch exception and fallback to local mode
        with patch('soorma.context.MemoryServiceClient') as mock_client_class:
            mock_client_class.return_value = mock_client
            
            await wrapper._ensure_client()
            
            # Verify - should switch to local mode
            assert wrapper._use_local is True
        
        # Test fallback to local store still works
        result = await wrapper.store("test_key", {"value": 123})
        assert result is True
        assert wrapper._local_store["test_key"] == {"value": 123}



class TestBusClientWrapper2:
    """Additional tests for the BusClient wrapper in context.py."""
    
    @pytest.mark.asyncio
    async def test_publish_delegates_to_event_client_with_kwargs(self):
        """Test publish() delegates to event_client with all parameters."""
        # Setup
        mock_event_client = AsyncMock(spec=EventClient)
        mock_event_client.publish = AsyncMock(return_value="event-123")
        
        wrapper = BusClient(event_client=mock_event_client)
        
        # Execute
        event_id = await wrapper.publish(
            event_type="task.completed",
            data={"task_id": "task-1"},
            topic="tasks",
            correlation_id="corr-1"
        )
        
        # Verify
        assert event_id == "event-123"
        # Check that publish was called with expected parameters
        call_kwargs = mock_event_client.publish.call_args.kwargs
        assert call_kwargs["event_type"] == "task.completed"
        assert call_kwargs["topic"] == "tasks"
        assert call_kwargs["data"] == {"task_id": "task-1"}
        assert call_kwargs["correlation_id"] == "corr-1"
    
    @pytest.mark.asyncio
    async def test_publish_requires_explicit_topic_stage1(self):
        """Test publish() requires explicit topic parameter (Stage 1)."""
        # Setup
        mock_event_client = AsyncMock(spec=EventClient)
        mock_event_client.publish = AsyncMock(return_value="event-456")
        
        wrapper = BusClient(event_client=mock_event_client)
        
        # Execute
        event_id = await wrapper.publish(
            event_type="user.registered",
            topic="users",
            data={"user_id": "user-1"}
        )
        
        # Verify
        assert event_id == "event-456"
        call_kwargs = mock_event_client.publish.call_args.kwargs
        assert call_kwargs["event_type"] == "user.registered"
        assert call_kwargs["topic"] == "users"
        assert call_kwargs["data"] == {"user_id": "user-1"}


class TestIntegrationScenarios:
    """Integration tests for common usage patterns."""
    

