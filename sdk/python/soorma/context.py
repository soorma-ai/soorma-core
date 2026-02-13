"""
Platform Context - Infrastructure services for Soorma agents.

The PlatformContext provides access to all platform services:
- registry: Service discovery and capability registration
- memory: Distributed state management (procedural, semantic, episodic)
- bus: Event choreography (publish/subscribe)
- tracker: Observability and state machine tracking

Usage:
    @worker.on_task("schedule_technician")
    async def schedule_service(task, context: PlatformContext):
        # Service Discovery
        agents = await context.registry.query_agents(name="calendar_api_tool")
        calendar_tool = agents[0] if agents else None
        
        # Shared Memory
        vehicle = await context.memory.retrieve(f"vehicle:{task.data['vehicle_id']}")
        
        # Event Publishing (automatic state tracking by platform)
        await context.bus.publish("technician_scheduled", result)
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
import httpx
import logging
import os

from soorma_common.events import EventTopic
from soorma_common.models import (
    TaskContextResponse,
    WorkingMemoryDeleteKeyResponse,
    WorkingMemoryDeletePlanResponse,
)
from .events import EventClient
from .memory import MemoryClient as MemoryServiceClient
from .registry.client import RegistryClient
from .ai.event_toolkit import EventToolkit

logger = logging.getLogger(__name__)


# Legacy RegistryClient wrapper removed - now using full RegistryClient from soorma.registry.client
# The full client provides all the same methods plus proper Pydantic models and event discovery


@dataclass
class MemoryClient:
    """
    Distributed State Management client.
    
    Powered by: Memory Service (PostgreSQL + pgvector)
    
    Memory types (CoALA framework):
    - Semantic: Facts and knowledge (RAG with vector search)
    - Episodic: Past experiences and events (interaction history)
    - Procedural: How to do things (skills, procedures)
    - Working: Current task context (plan-scoped state)
    
    Methods:
        Semantic Memory:
            store_knowledge(): Store facts/knowledge with automatic embeddings
            search_knowledge(): Vector search for relevant knowledge
        
        Episodic Memory:
            log_interaction(): Log agent/user interactions
            get_recent_history(): Get recent interaction context window
            search_interactions(): Vector search past interactions
        
        Procedural Memory:
            get_relevant_skills(): Retrieve relevant skills/prompts
        
        Working Memory:
            store(): Set plan-scoped state
            retrieve(): Get plan-scoped state
            delete_key(): Delete a single state key
            cleanup_plan(): Delete all state for a plan
        
        Task Context (Async Worker Pattern - RF-SDK-004):
            store_task_context(): Persist async worker task state
            get_task_context(): Retrieve task context by task ID
            update_task_context(): Update task state/sub-tasks
            delete_task_context(): Clean up completed task
            get_task_by_subtask(): Find parent task from sub-task ID
            
            Note: Prefer using TaskContext methods (save(), restore(), etc.)
            over direct memory calls. These are low-level APIs.
    """
    base_url: str = field(default_factory=lambda: os.getenv("SOORMA_MEMORY_SERVICE_URL", "http://localhost:8083"))
    # Note: Local fallback removed - Memory Service required for multi-agent workflows
    _client: Optional[MemoryServiceClient] = field(default=None, repr=False, init=False)
    
    async def _ensure_client(self) -> MemoryServiceClient:
        if self._client is None:
            self._client = MemoryServiceClient(base_url=self.base_url)
            # Test connection
            try:
                await self._client.health()
                logger.info(f"Connected to Memory Service at {self.base_url}")
            except Exception as e:
                logger.error(
                    f"Memory Service unavailable at {self.base_url}. "
                    f"Multi-agent workflows require Memory Service for shared state. "
                    f"Start it with: soorma dev"
                )
                raise RuntimeError(
                    f"Memory Service required but unavailable: {e}"
                ) from e
        return self._client
    
    async def retrieve(self, key: str, plan_id: Optional[str] = None, tenant_id: str = None, user_id: str = None) -> Optional[Any]:
        """
        Read shared memory by key (Working Memory).
        
        Args:
            key: Memory key (e.g., "research_summary", "account_id")
            plan_id: Plan ID for working memory scope (defaults to "default")
            tenant_id: Tenant ID from event context (REQUIRED)
            user_id: User ID from event context (REQUIRED)
            
        Returns:
            Stored value if found, None otherwise
        """
        if not tenant_id or not user_id:
            raise ValueError("tenant_id and user_id are required (get from event context)")
            
        client = await self._ensure_client()
        try:
            plan = plan_id or "default"
            result = await client.get_plan_state(plan, key, tenant_id, user_id)
            # Return value directly - no unwrapping needed
            return result.value
        except Exception as e:
            if "404" in str(e):
                return None
            raise
    
    async def store(
        self,
        key: str,
        value: Any,
        plan_id: Optional[str] = None,
        tenant_id: str = None,
        user_id: str = None,
    ) -> bool:
        """
        Persist plan-scoped state to Working Memory.
        
        Args:
            key: Memory key (e.g., "research_summary", "account_id")
            value: Value to store (will be JSON serialized)
            plan_id: Plan ID for working memory scope (defaults to "default")
            tenant_id: Tenant ID from event context (REQUIRED)
            user_id: User ID from event context (REQUIRED)
            
        Returns:
            True if store succeeded
        """
        if not tenant_id or not user_id:
            raise ValueError("tenant_id and user_id are required (get from event context)")
            
        client = await self._ensure_client()
        plan = plan_id or "default"
        # Pass value directly - set_plan_state wraps it in WorkingMemorySet
        await client.set_plan_state(plan, key, value, tenant_id, user_id)
        return True
    
    async def store_knowledge(
        self,
        content: str,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Store knowledge in Semantic Memory with automatic embeddings.
        
        Args:
            content: Knowledge content/facts to store
            user_id: User identifier (required in single-tenant mode)
            metadata: Optional metadata (source, tags, doc_id, etc.)
            
        Returns:
            Memory ID if successful, None otherwise
        """
        client = await self._ensure_client()
        result = await client.store_knowledge(content, user_id=user_id, metadata=metadata or {})
        return str(result.id)
    
    async def search_knowledge(
        self,
        query: str,
        user_id: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Search Semantic Memory using vector similarity.
        
        Args:
            query: Natural language search query
            user_id: User identifier (required in single-tenant mode)
            limit: Maximum results to return (1-50)
            
        Returns:
            List of matching knowledge entries with similarity scores
        """
        client = await self._ensure_client()
        results = await client.search_knowledge(query, user_id=user_id, limit=limit)
        return [
            {
                "id": r.id,
                "content": r.content,
                "metadata": r.metadata,
                "score": r.score,
                "created_at": r.created_at,
            }
            for r in results
        ]
    
    async def search_interactions(
        self,
        agent_id: str,
        query: str,
        user_id: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Search Episodic Memory using vector similarity (long-term recall).
        
        Args:
            agent_id: Agent identifier
            query: Natural language search query
            user_id: User identifier (required in single-tenant mode)
            limit: Maximum results to return (1-50)
            
        Returns:
            List of matching interaction entries with similarity scores
        """
        client = await self._ensure_client()
        results = await client.search_interactions(agent_id, query, user_id, limit=limit)
        return [
            {
                "id": r.id,
                "role": r.role,
                "content": r.content,
                "metadata": r.metadata,
                "score": r.score,
                "created_at": r.created_at,
            }
            for r in results
        ]
    
    async def log_interaction(
        self,
        agent_id: str,
        role: str,
        content: str,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Log an interaction to episodic memory.
        
        Args:
            agent_id: Agent identifier
            role: Role (user, assistant, system, tool)
            content: Interaction content
            user_id: User identifier (required in single-tenant mode)
            metadata: Optional metadata
            
        Returns:
            True if log succeeded
        """
        client = await self._ensure_client()
        await client.log_interaction(agent_id, role, content, user_id, metadata)
        return True
    
    async def get_recent_history(
        self,
        agent_id: str,
        user_id: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Get recent interaction history (context window).
        
        Args:
            agent_id: Agent identifier
            user_id: User identifier (required in single-tenant mode)
            limit: Maximum number of results (1-100)
            
        Returns:
            List of recent interactions ordered by recency
        """
        client = await self._ensure_client()
        results = await client.get_recent_history(agent_id, user_id, limit=limit)
        return [
            {
                "id": r.id,
                "role": r.role,
                "content": r.content,
                "metadata": r.metadata,
                "created_at": r.created_at,
            }
            for r in results
        ]
    
    async def get_relevant_skills(
        self,
        agent_id: str,
        context: str,
        user_id: str,
        limit: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Get relevant procedural knowledge (skills, prompts, rules).
        
        Args:
            agent_id: Agent identifier
            context: Task/query context
            user_id: User identifier (required in single-tenant mode)
            limit: Maximum number of results (1-20)
            
        Returns:
            List of relevant skills ordered by relevance
        """
        client = await self._ensure_client()
        results = await client.get_relevant_skills(agent_id, context, user_id, limit=limit)
        return [
            {
                "id": r.id,
                "procedure_type": r.procedure_type,
                "content": r.content,
                "trigger_condition": r.trigger_condition,
                "score": r.score,
            }
            for r in results
        ]
    
    
    async def delete_key(
        self,
        plan_id: str,
        tenant_id: str,
        user_id: str,
        key: str,
    ) -> WorkingMemoryDeleteKeyResponse:
        """
        Delete a single key from plan working memory.
        
        Args:
            plan_id: Plan identifier
            tenant_id: Tenant ID from event context
            user_id: User ID from event context
            key: State key to delete
                 
        Returns:
            WorkingMemoryDeleteKeyResponse with success, deleted, and message
            
        Raises:
            httpx.HTTPStatusError: If plan not found (404)
            
        Example:
            ```python
            result = await context.memory.delete_key(
                plan_id="plan-123",
                tenant_id="tenant-1",
                user_id="user-1",
                key="agent_state"
            )
            if result.deleted:
                print("Key deleted")
            ```
        """
        client = await self._ensure_client()
        return await client.delete_plan_state(
            plan_id=plan_id,
            tenant_id=tenant_id,
            user_id=user_id,
            key=key,
        )
    
    async def cleanup_plan(
        self,
        plan_id: str,
        tenant_id: str,
        user_id: str,
    ) -> WorkingMemoryDeletePlanResponse:
        """
        Delete all working memory for a plan (cleanup).
        
        Removes all keys for the plan. Useful after plan completion or when
        reclaiming resources.
        
        Args:
            plan_id: Plan identifier
            tenant_id: Tenant ID from event context
            user_id: User ID from event context
                 
        Returns:
            WorkingMemoryDeletePlanResponse with success, count_deleted, and message
            
        Raises:
            httpx.HTTPStatusError: If plan not found (404)
            
        Example:
            ```python
            result = await context.memory.cleanup_plan(
                plan_id="plan-123",
                tenant_id="tenant-1",
                user_id="user-1"
            )
            print(f"Cleaned up {result.count_deleted} state entries")
            ```
        """
        client = await self._ensure_client()
        return await client.delete_plan_state(
            plan_id=plan_id,
            tenant_id=tenant_id,
            user_id=user_id,
            key=None,
        )

    async def store_task_context(
        self,
        task_id: str,
        plan_id: Optional[str],
        event_type: str,
        response_event: Optional[str] = None,
        response_topic: str = "action-results",
        data: Optional[Dict[str, Any]] = None,
        sub_tasks: Optional[List[str]] = None,
        state: Optional[Dict[str, Any]] = None,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> TaskContextResponse:
        """
        Persist async Worker task context for resumption (RF-SDK-004).
        
        Stores task metadata, sub-task tracking, and worker state so that
        tasks can be paused during delegation and resumed when results arrive.
        
        LOW-LEVEL API: Prefer TaskContext.save() which handles serialization.
        
        Args:
            task_id: Unique task identifier
            plan_id: Optional plan ID for coordinated workflows
            event_type: Event type that triggered this task
            response_event: Event type to publish when task completes
            response_topic: Topic for response event (default: "action-results")
            data: Request data payload from triggering event
            sub_tasks: List of sub-task IDs (for tracking delegations)
            state: Worker-specific state dict (persisted across delegations)
            tenant_id: Tenant ID from event context (REQUIRED)
            user_id: User ID from event context (REQUIRED)
            
        Returns:
            Task context DTO from Memory Service
            
        Example:
            ```python
            # Prefer TaskContext.save() instead:
            task.state["order_details"] = order
            await task.save()  # Calls this internally
            
            # Direct usage (not recommended):
            await context.memory.store_task_context(
                task_id="task-123",
                plan_id="plan-456",
                event_type="process_order",
                response_event="order_processed",
                data={"order_id": "ord-789"},
                state={"validation_step": "inventory_check"},
            )
            ```
        """
        client = await self._ensure_client()
        return await client.store_task_context(
            task_id=task_id,
            plan_id=plan_id,
            event_type=event_type,
            response_event=response_event,
            response_topic=response_topic,
            data=data,
            sub_tasks=sub_tasks,
            state=state,
            tenant_id=tenant_id,
            user_id=user_id,
        )

    async def get_task_context(
        self,
        task_id: str,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Optional[TaskContextResponse]:
        """
        Retrieve persisted task context by task ID.
        
        LOW-LEVEL API: Prefer TaskContext.restore() which deserializes properly.
        
        Args:
            task_id: Task identifier
            tenant_id: Tenant ID from event context (REQUIRED)
            user_id: User ID from event context (REQUIRED)
            
        Returns:
            Task context DTO if found, None otherwise
            
        Example:
            ```python
            # Prefer TaskContext.restore() instead:
            task = await TaskContext.restore(task_id, context)
            
            # Direct usage (not recommended):
            task_data = await context.memory.get_task_context("task-123")
            if task_data:
                print(f"Task {task_data.task_id}: {task_data.event_type}")
            ```
        """
        client = await self._ensure_client()
        return await client.get_task_context(task_id, tenant_id=tenant_id, user_id=user_id)

    async def update_task_context(
        self,
        task_id: str,
        sub_tasks: Optional[List[str]] = None,
        state: Optional[Dict[str, Any]] = None,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> TaskContextResponse:
        """
        Update persisted task context with new state or sub-task tracking.
        
        LOW-LEVEL API: Prefer TaskContext.save() which handles incremental updates.
        
        Args:
            task_id: Task identifier
            sub_tasks: Optional list of sub-task IDs to update tracking
            state: Optional state dict to merge/replace
            tenant_id: Tenant ID from event context (REQUIRED)
            user_id: User ID from event context (REQUIRED)
            
        Returns:
            Updated task context DTO
            
        Example:
            ```python
            # Prefer TaskContext.save() instead:
            task.state["validation_result"] = result
            await task.save()  # Updates existing task context
            
            # Direct usage (not recommended):
            await context.memory.update_task_context(
                task_id="task-123",
                state={"validation_result": "passed", "step": 2},
            )
            ```
        """
        client = await self._ensure_client()
        return await client.update_task_context(
            task_id=task_id,
            sub_tasks=sub_tasks,
            state=state,
            tenant_id=tenant_id,
            user_id=user_id,
        )

    async def delete_task_context(
        self,
        task_id: str,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> bool:
        """
        Delete persisted task context (cleanup after completion).
        
        LOW-LEVEL API: TaskContext.complete() calls this automatically.
        
        Args:
            task_id: Task identifier
            tenant_id: Tenant ID from event context (REQUIRED)
            user_id: User ID from event context (REQUIRED)
            
        Returns:
            True if deleted successfully
            
        Example:
            ```python
            # TaskContext.complete() handles this automatically:
            await task.complete({"status": "completed"})
            # ^ Publishes response and deletes task context
            
            # Direct usage (not recommended):
            await context.memory.delete_task_context("task-123")
            ```
        """
        client = await self._ensure_client()
        return await client.delete_task_context(task_id, tenant_id=tenant_id, user_id=user_id)

    async def get_task_by_subtask(
        self,
        sub_task_id: str,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Optional[TaskContextResponse]:
        """
        Find parent task context using sub-task correlation ID.
        
        Used by ResultContext.restore_task() to resume parent task when
        a sub-task result arrives. Queries the reverse index maintained
        by Memory Service.
        
        LOW-LEVEL API: Prefer ResultContext.restore_task() in on_result() handlers.
        
        Args:
            sub_task_id: Sub-task identifier (correlation_id from result event)
            tenant_id: Tenant ID from event context (REQUIRED)
            user_id: User ID from event context (REQUIRED)
            
        Returns:
            Parent task context DTO if found, None otherwise
            
        Example:
            ```python
            # Prefer ResultContext.restore_task() instead:
            @worker.on_result("payment_completed")
            async def handle_payment(result: ResultContext, context: PlatformContext):
                task = await result.restore_task()  # Calls this internally
            
            # Direct usage (not recommended):
            task_data = await context.memory.get_task_by_subtask("subtask-456")
            if task_data:
                print(f"Parent task: {task_data.task_id}")
            ```
        """
        client = await self._ensure_client()
        return await client.get_task_by_subtask(sub_task_id, tenant_id=tenant_id, user_id=user_id)
    
    async def close(self) -> None:
        """Close the Memory Service client connection."""
        if self._client is not None:
            await self._client.close()
            self._client = None


@dataclass
class BusClient:
    """
    Event Choreography client.
    
    Powered by: Kafka / NATS (via Event Service)
    
    Methods:
        publish(): Emit domain events with explicit topic
        request(): Convenience method for action requests
        respond(): Convenience method for responses
        announce(): Convenience method for business facts
        create_child_request(): Create child event with metadata propagation
        create_response(): Create response event from request
        publish_envelope(): Publish pre-constructed envelope
        subscribe(): React to events (via EventClient)
    """
    event_client: EventClient = field(default_factory=EventClient)
    
    async def publish(
        self,
        topic: str,
        event_type: str,
        data: Dict[str, Any],
        correlation_id: Optional[str] = None,
        response_event: Optional[str] = None,
        response_topic: Optional[str] = None,
        trace_id: Optional[str] = None,
        parent_event_id: Optional[str] = None,
        payload_schema_name: Optional[str] = None,
        subject: Optional[str] = None,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> str:
        """
        Emit a domain event with explicit topic.
        
        Args:
            topic: Target topic (required, no inference)
            event_type: Event type (e.g., "technician_scheduled")
            data: Event payload
            correlation_id: Optional correlation ID for tracing
            response_event: Event type for response (DisCo pattern)
            response_topic: Topic for response (defaults to action-results)
            trace_id: Root trace ID for distributed tracing
            parent_event_id: ID of parent event in trace tree
            payload_schema_name: Registered schema name for payload
            subject: Optional subject/resource identifier
            tenant_id: Tenant ID for multi-tenancy (envelope metadata)
            user_id: User ID for authentication/authorization (envelope metadata)
            session_id: Session ID for conversation correlation
            
        Returns:
            The event ID
        """
        return await self.event_client.publish(
            event_type=event_type,
            topic=topic,
            data=data,
            correlation_id=correlation_id,
            response_event=response_event,
            response_topic=response_topic,
            trace_id=trace_id,
            parent_event_id=parent_event_id,
            payload_schema_name=payload_schema_name,
            subject=subject,
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=session_id,
        )
    
    async def request(
        self,
        event_type: str,
        data: Dict[str, Any],
        response_event: str,
        correlation_id: Optional[str] = None,
        response_topic: str = "action-results",
        trace_id: Optional[str] = None,
        parent_event_id: Optional[str] = None,
        subject: Optional[str] = None,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> str:
        """
        Publish to action-requests topic with mandatory response_event.
        Enforces the request/response contract.
        
        Args:
            event_type: Request event type
            data: Request payload
            response_event: Event type for response (required)
            correlation_id: Optional correlation ID
            response_topic: Topic for response (defaults to action-results)
            trace_id: Root trace ID for distributed tracing
            parent_event_id: ID of parent event in trace tree
            subject: Optional subject/resource identifier
            tenant_id: Tenant ID for multi-tenancy (envelope metadata)
            user_id: User ID for authentication/authorization (envelope metadata)
            session_id: Session ID for conversation correlation
            
        Returns:
            The event ID
        """
        return await self.publish(
            topic="action-requests",
            event_type=event_type,
            data=data,
            correlation_id=correlation_id,
            response_event=response_event,
            response_topic=response_topic,
            trace_id=trace_id,
            parent_event_id=parent_event_id,
            subject=subject,
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=session_id,
        )
    
    async def respond(
        self,
        event_type: str,
        data: Dict[str, Any],
        correlation_id: str,
        topic: str = "action-results",
        trace_id: Optional[str] = None,
        parent_event_id: Optional[str] = None,
        payload_schema_name: Optional[str] = None,
        subject: Optional[str] = None,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> str:
        """
        Publish to action-results topic with mandatory correlation_id.
        Enforces response correlation contract.
        
        Args:
            event_type: Response event type (from request.response_event)
            data: Response payload
            correlation_id: Correlation ID from original request (required)
            topic: Response topic (defaults to action-results)
            trace_id: Root trace ID for distributed tracing
            parent_event_id: ID of parent event in trace tree
            payload_schema_name: Registered schema name for payload
            subject: Optional subject/resource identifier
            tenant_id: Tenant ID for multi-tenancy (envelope metadata)
            user_id: User ID for authentication/authorization (envelope metadata)
            session_id: Session ID for conversation correlation
            
        Returns:
            The event ID
        """
        return await self.publish(
            topic=topic,
            event_type=event_type,
            data=data,
            correlation_id=correlation_id,
            trace_id=trace_id,
            parent_event_id=parent_event_id,
            payload_schema_name=payload_schema_name,
            subject=subject,
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=session_id,
        )
    
    async def announce(
        self,
        event_type: str,
        data: Dict[str, Any],
        correlation_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        parent_event_id: Optional[str] = None,
        subject: Optional[str] = None,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> str:
        """
        Publish to business-facts topic for domain events/observations.
        No response expected.
        
        Args:
            event_type: Business fact event type
            data: Event payload
            correlation_id: Optional correlation ID
            trace_id: Root trace ID for distributed tracing
            parent_event_id: ID of parent event in trace tree
            subject: Optional subject/resource identifier
            tenant_id: Tenant ID for multi-tenancy (envelope metadata)
            user_id: User ID for authentication/authorization (envelope metadata)
            session_id: Session ID for conversation correlation
            
        Returns:
            The event ID
        """
        return await self.publish(
            topic="business-facts",
            event_type=event_type,
            data=data,
            correlation_id=correlation_id,
            trace_id=trace_id,
            parent_event_id=parent_event_id,
            subject=subject,
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=session_id,
        )
    
    def create_child_request(
        self,
        parent_event: "EventEnvelope",
        event_type: str,
        data: Dict[str, Any],
        response_event: str,
        new_correlation_id: Optional[str] = None,
    ) -> "EventEnvelope":
        """
        Create child request envelope from parent event, auto-propagating metadata.
        Returns EventEnvelope with proper type safety.
        
        Args:
            parent_event: The parent event to derive metadata from
            event_type: Child event type
            data: Child event payload
            response_event: Expected response event type
            new_correlation_id: Optional new correlation ID (generated if not provided)
            
        Returns:
            EventEnvelope with auto-propagated metadata
        """
        from uuid import uuid4
        from soorma_common.events import EventEnvelope, EventTopic
        
        return EventEnvelope(
            id=str(uuid4()),
            source=parent_event.source,
            type=event_type,
            topic=EventTopic.ACTION_REQUESTS,
            data=data,
            response_event=response_event,
            response_topic="action-results",
            trace_id=parent_event.trace_id,  # PROPAGATE
            parent_event_id=parent_event.id,  # LINK
            correlation_id=new_correlation_id or str(uuid4()),
            tenant_id=parent_event.tenant_id,  # PROPAGATE
            session_id=parent_event.session_id,  # PROPAGATE
        )
    
    def create_response(
        self,
        request_event: "EventEnvelope",
        data: Dict[str, Any],
        payload_schema_name: Optional[str] = None,
    ) -> "EventEnvelope":
        """
        Create response envelope from request event, auto-copying metadata.
        Returns EventEnvelope with proper type safety.
        
        Args:
            request_event: The request event to respond to
            data: Response payload
            payload_schema_name: Optional schema reference for payload
            
        Returns:
            EventEnvelope with auto-matched correlation and propagated metadata
        """
        from uuid import uuid4
        from soorma_common.events import EventEnvelope, EventTopic
        
        return EventEnvelope(
            id=str(uuid4()),
            source=request_event.source,
            type=request_event.response_event,  # USE REQUESTED
            topic=EventTopic.ACTION_RESULTS if not request_event.response_topic else EventTopic(request_event.response_topic),
            data=data,
            correlation_id=request_event.correlation_id,  # MATCH
            trace_id=request_event.trace_id,  # PROPAGATE
            parent_event_id=request_event.id,  # LINK
            payload_schema_name=payload_schema_name,  # SCHEMA REFERENCE
            tenant_id=request_event.tenant_id,  # PROPAGATE
            session_id=request_event.session_id,  # PROPAGATE
        )
    
    async def publish_envelope(self, envelope: "EventEnvelope") -> str:
        """
        Publish a pre-constructed EventEnvelope.
        Convenience method for use with create_child_request() and create_response().
        
        Args:
            envelope: Pre-constructed EventEnvelope
            
        Returns:
            The event ID
        """
        return await self.publish(
            topic=envelope.topic.value,
            event_type=envelope.type,
            data=envelope.data,
            correlation_id=envelope.correlation_id,
            response_event=envelope.response_event,
            response_topic=envelope.response_topic,
            trace_id=envelope.trace_id,
            parent_event_id=envelope.parent_event_id,
            payload_schema_name=envelope.payload_schema_name,
            subject=envelope.subject,
            tenant_id=envelope.tenant_id,
            session_id=envelope.session_id,
        )
    
    async def subscribe(self, topics: List[Union[EventTopic, str]]) -> None:
        """
        Subscribe to event topics.
        
        This connects to the Event Service and starts receiving events.
        Use @event_client.on_event() decorator to register handlers.
        
        Args:
            topics: List of topics (EventTopic enum) or patterns (str for wildcards)
        """
        # Convert EventTopic enums to strings
        topic_strings = [t.value if isinstance(t, EventTopic) else t for t in topics]
        await self.event_client.connect(topics=topic_strings)
    
    async def close(self) -> None:
        """Close the event client."""
        await self.event_client.disconnect()


@dataclass
class TrackerClient:
    """
    Observability & State Machine client.
    
    Powered by: Time-series DB (in production)
    
    Methods:
        start_plan(): Initialize execution trace
        emit_progress(): Log checkpoints
        detect_timeout(): Handle failures
    
    NOTE: Tracker Service is not yet implemented. This client provides
    a no-op implementation that logs operations for development.
    """
    base_url: str = field(default_factory=lambda: os.getenv("SOORMA_TRACKER_URL", "http://localhost:8084"))
    _http_client: Optional[httpx.AsyncClient] = field(default=None, repr=False)
    _use_noop: bool = field(default=True, repr=False)  # Use no-op by default until service is implemented
    
    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient()
        return self._http_client
    
    async def start_plan(
        self,
        plan_id: str,
        agent_id: str,
        goal: str,
        tasks: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Initialize execution trace for a plan.
        
        Args:
            plan_id: Unique plan identifier
            agent_id: The planning agent ID
            goal: The goal being solved
            tasks: List of planned tasks
            metadata: Optional additional metadata
            
        Returns:
            True if plan was started
        """
        # No-op for development
        if self._use_noop:
            logger.debug(f"Tracker start_plan (noop): {plan_id} with {len(tasks)} tasks")
            return True
        
        client = await self._ensure_client()
        try:
            response = await client.post(
                f"{self.base_url}/v1/plans",
                json={
                    "plan_id": plan_id,
                    "agent_id": agent_id,
                    "goal": goal,
                    "tasks": tasks,
                    "metadata": metadata or {},
                },
                timeout=10.0,
            )
            return response.status_code in (200, 201)
        except Exception as e:
            logger.debug(f"Tracker start_plan failed (continuing): {e}")
            return True
    
    async def emit_progress(
        self,
        plan_id: str,
        task_id: str,
        status: str,
        progress: float = 0.0,
        message: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Log a checkpoint/progress update.
        
        Args:
            plan_id: The plan being executed
            task_id: The specific task
            status: Status (pending, running, completed, failed)
            progress: Progress percentage (0.0 - 1.0)
            message: Optional status message
            data: Optional data payload
            
        Returns:
            True if progress was recorded
        """
        # No-op for development
        if self._use_noop:
            logger.debug(f"Tracker emit_progress (noop): {task_id} -> {status} ({progress:.0%})")
            return True
        
        client = await self._ensure_client()
        try:
            response = await client.post(
                f"{self.base_url}/v1/plans/{plan_id}/progress",
                json={
                    "task_id": task_id,
                    "status": status,
                    "progress": progress,
                    "message": message,
                    "data": data or {},
                },
                timeout=10.0,
            )
            return response.status_code == 200
        except Exception as e:
            logger.debug(f"Tracker emit_progress failed (continuing): {e}")
            return True
    
    async def complete_task(
        self,
        plan_id: str,
        task_id: str,
        result: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Mark a task as completed.
        
        Args:
            plan_id: The plan ID
            task_id: The task ID
            result: Optional result data
            
        Returns:
            True if task was marked complete
        """
        return await self.emit_progress(
            plan_id=plan_id,
            task_id=task_id,
            status="completed",
            progress=1.0,
            data=result,
        )
    
    async def fail_task(
        self,
        plan_id: str,
        task_id: str,
        error: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Mark a task as failed.
        
        Args:
            plan_id: The plan ID
            task_id: The task ID
            error: Error message
            data: Optional error data
            
        Returns:
            True if task was marked failed
        """
        return await self.emit_progress(
            plan_id=plan_id,
            task_id=task_id,
            status="failed",
            message=error,
            data=data,
        )
    
    async def get_plan_status(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the current status of a plan.
        
        Args:
            plan_id: The plan ID
            
        Returns:
            Plan status dict if found, None otherwise
        """
        # No-op for development
        if self._use_noop:
            logger.debug(f"Tracker get_plan_status (noop): {plan_id}")
            return {"plan_id": plan_id, "status": "unknown"}
        
        client = await self._ensure_client()
        try:
            response = await client.get(
                f"{self.base_url}/v1/plans/{plan_id}",
                timeout=10.0,
            )
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.debug(f"Tracker get_plan_status failed: {e}")
            return None
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None


@dataclass
class PlatformContext:
    """
    Platform Context - The complete infrastructure access for agents.
    
    Every event handler receives a PlatformContext that provides access to
    all platform services. This eliminates configuration overhead and provides
    a consistent interface regardless of deployment environment.
    
    Attributes:
        registry: Service Discovery & Capabilities
        memory: Distributed State Management
        bus: Event Choreography
        tracker: Observability & State Machines
        toolkit: AI-friendly event discovery and generation utilities
    
    Usage:
        @worker.on_task("schedule_technician")
        async def schedule_service(task, context: PlatformContext):
            # Service Discovery
            agents = await context.registry.query_agents(name="calendar_api_tool")
            calendar_tool = agents[0] if agents else None
            
            # Shared Memory
            vehicle = await context.memory.retrieve(f"vehicle:{task.data['vehicle_id']}")
            
            # Event Publishing
            await context.bus.publish("technician_scheduled", result)
            
            # Progress tracking (automatic for most cases)
            await context.tracker.emit_progress(
                plan_id=task.plan_id,
                task_id=task.id,
                status="completed",
            )
    """
    registry: RegistryClient
    memory: MemoryClient
    bus: BusClient
    tracker: TrackerClient
    toolkit: EventToolkit
    
    def __init__(
        self,
        registry: RegistryClient = None,
        memory: MemoryClient = None,
        bus: BusClient = None,
        tracker: TrackerClient = None,
        toolkit: EventToolkit = None,
    ):
        """
        Create a PlatformContext with configured clients.
        
        Args:
            registry: Registry client (optional)
            memory: Memory client with tenant_id/user_id configured (required for memory operations)
            bus: Bus client (optional)
            tracker: Tracker client (optional)
            toolkit: EventToolkit for AI-friendly event utilities (optional)
        """
        self.registry = registry or RegistryClient(base_url=os.getenv("SOORMA_REGISTRY_URL", "http://localhost:8081"))
        self.memory = memory or MemoryClient()
        self.bus = bus or BusClient()
        self.tracker = tracker or TrackerClient()
        # Toolkit reuses registry client - no async with needed when using context.toolkit!
        self.toolkit = toolkit or EventToolkit(registry_url=self.registry.base_url, registry_client=self.registry)
    
    @classmethod
    def from_env(cls) -> "PlatformContext":
        """
        Create a PlatformContext from environment variables (convenience method).
        
        Environment variables:
            SOORMA_REGISTRY_URL: Registry service URL (default: http://localhost:8081)
            SOORMA_EVENT_SERVICE_URL: Event service URL (default: http://localhost:8082)
            SOORMA_MEMORY_URL: Memory service URL (default: http://localhost:8083)
            SOORMA_TRACKER_URL: Tracker service URL (default: http://localhost:8084)
            
        Returns:
            PlatformContext with clients configured from environment
            
        Note:
            MemoryClient is initialized here, but tenant_id/user_id must be provided
            at runtime when calling memory methods (from event context).
        """
        event_client = EventClient(
            event_service_url=os.getenv("SOORMA_EVENT_SERVICE_URL", "http://localhost:8082"),
        )
        
        registry_url = os.getenv("SOORMA_REGISTRY_URL", "http://localhost:8081")
        registry_client = RegistryClient(base_url=registry_url)
        
        return cls(
            registry=registry_client,
            memory=MemoryClient(
                base_url=os.getenv("SOORMA_MEMORY_URL", "http://localhost:8083"),
            ),
            bus=BusClient(event_client=event_client),
            tracker=TrackerClient(
                base_url=os.getenv("SOORMA_TRACKER_URL", "http://localhost:8084"),
            ),
            toolkit=EventToolkit(registry_url=registry_url, registry_client=registry_client),
        )
    
    async def close(self) -> None:
        """Close all clients."""
        await self.registry.close()
        await self.memory.close()
        await self.bus.close()
        await self.tracker.close()
        # EventToolkit doesn't need explicit close - it uses context managers internally
