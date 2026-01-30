"""
Client library for interacting with the Memory Service.

The Memory Service implements the CoALA (Cognitive Architectures for Language Agents)
framework with four types of memory:
- Semantic Memory: Knowledge base with RAG and vector search
- Episodic Memory: User/Agent interaction history with temporal recall
- Procedural Memory: Dynamic prompts, rules, and skills
- Working Memory: Plan-scoped shared state for multi-agent collaboration
"""

from typing import Any, Dict, List, Optional
from uuid import UUID
import httpx

from soorma_common.models import (
    SemanticMemoryCreate,
    SemanticMemoryResponse,
    EpisodicMemoryCreate,
    EpisodicMemoryResponse,
    ProceduralMemoryResponse,
    WorkingMemorySet,
    WorkingMemoryResponse,
    WorkingMemoryDeleteKeyResponse,
    WorkingMemoryDeletePlanResponse,
    # Task Context
    TaskContextCreate,
    TaskContextUpdate,
    TaskContextResponse,
    # Plan Context
    PlanContextCreate,
    PlanContextUpdate,
    PlanContextResponse,
    # Plans & Sessions
    PlanCreate,
    PlanUpdate,
    PlanSummary,
    SessionCreate,
    SessionSummary,
)


class MemoryClient:
    """
    Client for interacting with the Memory Service API.
    
    This client provides methods for all four CoALA memory types:
    - Semantic: Knowledge storage and semantic search
    - Episodic: Interaction history and temporal recall
    - Procedural: Dynamic prompts and skills retrieval
    - Working: Plan-scoped state management
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:8083",
        timeout: float = 30.0,
    ):
        """
        Initialize the memory client.
        
        Args:
            base_url: Base URL of the memory service (e.g., "http://localhost:8083")
            timeout: HTTP request timeout in seconds
            
        Note:
            tenant_id and user_id are passed per-request in method calls.
            This allows a single agent to serve multiple users/tenants.
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout)
    
    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    # Semantic Memory Methods
    
    async def store_knowledge(
        self,
        content: str,
        user_id: str,
        external_id: Optional[str] = None,
        is_public: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        source: Optional[str] = None,
    ) -> SemanticMemoryResponse:
        """
        Store or update knowledge in semantic memory (upsert).
        
        RF-ARCH-012: Upserts by external_id (if provided) or content_hash (automatic)
        RF-ARCH-014: Defaults to private (user-scoped). Use is_public=True for shared knowledge.
        
        The service automatically generates embeddings for vector search.
        
        Behavior:
        - With external_id: Updates existing knowledge with same external_id
        - Without external_id: Prevents duplicate content via content_hash
        - Privacy: Knowledge is private by default (only visible to this user)
        
        Args:
            content: Knowledge content to store (required)
            user_id: User who owns this knowledge (required)
            external_id: Optional user-provided ID for versioning/upsert
            is_public: If True, visible to all users in tenant. Default False (private).
            metadata: Optional metadata dict
            tags: Optional tags for categorization
            source: Optional source identifier
            
        Returns:
            SemanticMemoryResponse with the stored memory
            
        Examples:
            # Store private knowledge (default)
            await memory.store_knowledge(
                content="My personal research notes",
                user_id="alice"
            )
            
            # Store and update by external_id
            await memory.store_knowledge(
                content="Docker v2 documentation",
                user_id="alice",
                external_id="doc-docker",
                metadata={"version": "2.0"}
            )
            
            # Store public knowledge (shared with all users in tenant)
            await memory.store_knowledge(
                content="Team's API best practices",
                user_id="alice",
                external_id="best-practices",
                is_public=True
            )
        """
        data = SemanticMemoryCreate(
            content=content,
            external_id=external_id,
            is_public=is_public,
            metadata=metadata or {},
            tags=tags,
            source=source,
        )
        
        response = await self._client.post(
            f"{self.base_url}/v1/memory/semantic",
            params={"user_id": user_id},  # Pass user_id as query parameter for API context
            json=data.model_dump(by_alias=True),
        )
        response.raise_for_status()
        return SemanticMemoryResponse.model_validate(response.json())
    
    async def query_knowledge(
        self,
        query: str,
        user_id: str,
        limit: int = 5,
        include_public: bool = True,
    ) -> List[SemanticMemoryResponse]:
        """
        Query semantic memory using vector similarity with privacy support.
        
        RF-ARCH-014: Returns your private knowledge + optional public knowledge.
        
        Args:
            query: Search query text
            user_id: User performing the query
            limit: Maximum number of results (1-50)
            include_public: If True (default), includes public knowledge from all users
            
        Returns:
            List of SemanticMemoryResponse sorted by similarity score (highest first)
        """
        response = await self._client.post(
            f"{self.base_url}/v1/memory/semantic/query",
            params={
                "user_id": user_id,
                "query": query,
                "limit": limit,
                "include_public": include_public,
            },
        )
        response.raise_for_status()
        return [SemanticMemoryResponse.model_validate(item) for item in response.json()]
    
    async def search_knowledge(
        self,
        query: str,
        user_id: str,
        limit: int = 5,
    ) -> List[SemanticMemoryResponse]:
        """
        Search semantic memory using vector similarity (backward compatibility).
        
        Deprecated: Use query_knowledge() instead for better consistency.
        
        This endpoint maintains backward compatibility and includes public knowledge.
        
        Args:
            query: Search query
            user_id: User identifier
            limit: Maximum number of results (1-50)
            
        Returns:
            List of SemanticMemoryResponse ordered by relevance
        """
        return await self.query_knowledge(query, user_id, limit, include_public=True)
    
    # Episodic Memory Methods
    
    async def log_interaction(
        self,
        agent_id: str,
        role: str,
        content: str,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EpisodicMemoryResponse:
        """
        Log an interaction to episodic memory.
        
        Args:
            agent_id: Agent identifier
            role: Role (user, assistant, system, tool)
            content: Interaction content
            user_id: User identifier (required in single-tenant mode)
            metadata: Optional metadata
            
        Returns:
            EpisodicMemoryResponse with the logged memory
        """
        data = EpisodicMemoryCreate(
            agent_id=agent_id,
            role=role,
            content=content,
            metadata=metadata or {},
        )
        
        response = await self._client.post(
            f"{self.base_url}/v1/memory/episodic",
            json=data.model_dump(by_alias=True),
            params={"user_id": user_id},
        )
        response.raise_for_status()
        return EpisodicMemoryResponse.model_validate(response.json())
    
    async def get_recent_history(
        self,
        agent_id: str,
        user_id: str,
        limit: int = 10,
    ) -> List[EpisodicMemoryResponse]:
        """
        Get recent interaction history (context window).
        
        Args:
            agent_id: Agent identifier
            user_id: User identifier (required in single-tenant mode)
            limit: Maximum number of results (1-100)
            
        Returns:
            List of EpisodicMemoryResponse ordered by recency
        """
        response = await self._client.get(
            f"{self.base_url}/v1/memory/episodic/recent",
            params={"agent_id": agent_id, "user_id": user_id, "limit": limit},
        )
        response.raise_for_status()
        return [EpisodicMemoryResponse.model_validate(item) for item in response.json()]
    
    async def search_interactions(
        self,
        agent_id: str,
        query: str,
        user_id: str,
        limit: int = 5,
    ) -> List[EpisodicMemoryResponse]:
        """
        Search episodic memory using vector similarity (long-term recall).
        
        Args:
            agent_id: Agent identifier
            query: Search query
            user_id: User identifier (required in single-tenant mode)
            limit: Maximum number of results (1-50)
            
        Returns:
            List of EpisodicMemoryResponse ordered by relevance
        """
        response = await self._client.get(
            f"{self.base_url}/v1/memory/episodic/search",
            params={"agent_id": agent_id, "q": query, "user_id": user_id, "limit": limit},
        )
        response.raise_for_status()
        return [EpisodicMemoryResponse.model_validate(item) for item in response.json()]
    
    # Procedural Memory Methods
    
    async def get_relevant_skills(
        self,
        agent_id: str,
        context: str,
        user_id: str,
        limit: int = 3,
    ) -> List[ProceduralMemoryResponse]:
        """
        Get relevant procedural knowledge (skills, prompts, rules).
        
        Returns system prompts and few-shot examples matching the context.
        
        Args:
            agent_id: Agent identifier
            context: Task/query context
            user_id: User identifier (required in single-tenant mode)
            limit: Maximum number of results (1-20)
            
        Returns:
            List of ProceduralMemoryResponse ordered by relevance
        """
        response = await self._client.get(
            f"{self.base_url}/v1/memory/procedural/context",
            params={"agent_id": agent_id, "q": context, "user_id": user_id, "limit": limit},
        )
        response.raise_for_status()
        return [ProceduralMemoryResponse.model_validate(item) for item in response.json()]
    
    # Working Memory Methods
    
    async def set_plan_state(
        self,
        plan_id: str,
        key: str,
        value: Any,
        tenant_id: str,
        user_id: str,
    ) -> WorkingMemoryResponse:
        """
        Set or update working memory value for a plan.
        
        Args:
            plan_id: Plan identifier
            key: State key
            value: State value (any JSON-serializable type)
            tenant_id: Tenant ID (from event context)
            user_id: User ID (from event context)
            
        Returns:
            WorkingMemoryResponse with the stored state
        """
        data = WorkingMemorySet(value=value)
        
        response = await self._client.put(
            f"{self.base_url}/v1/memory/working/{plan_id}/{key}",
            json=data.model_dump(by_alias=True),
            headers={
                "X-Tenant-ID": tenant_id,
                "X-User-ID": user_id,
            },
        )
        response.raise_for_status()
        return WorkingMemoryResponse.model_validate(response.json())
    
    async def get_plan_state(
        self,
        plan_id: str,
        key: str,
        tenant_id: str,
        user_id: str,
    ) -> WorkingMemoryResponse:
        """
        Get working memory value for a plan.
        
        Args:
            plan_id: Plan identifier
            key: State key
            tenant_id: Tenant ID (from event context)
            user_id: User ID (from event context)
            
        Returns:
            WorkingMemoryResponse with the state
            
        Raises:
            httpx.HTTPStatusError: If key not found (404)
        """
        response = await self._client.get(
            f"{self.base_url}/v1/memory/working/{plan_id}/{key}",
            headers={
                "X-Tenant-ID": tenant_id,
                "X-User-ID": user_id,
            },
        )
        response.raise_for_status()
        return WorkingMemoryResponse.model_validate(response.json())
    
    async def delete_plan_state(
        self,
        plan_id: str,
        tenant_id: str,
        user_id: str,
        key: Optional[str] = None,
    ) -> WorkingMemoryDeleteKeyResponse | WorkingMemoryDeletePlanResponse:
        """
        Delete working memory for a plan.
        
        Delete a single key or all keys for a plan.
        
        Args:
            plan_id: Plan identifier
            tenant_id: Tenant ID (from event context)
            user_id: User ID (from event context)
            key: Optional state key. If provided, deletes only this key.
                 If not provided, deletes all keys for the plan.
                 
        Returns:
            WorkingMemoryDeleteKeyResponse if key is provided (includes deleted: bool flag)
            WorkingMemoryDeletePlanResponse if key is None (includes count_deleted: int)
            
        Raises:
            httpx.HTTPStatusError: If plan not found (404)
            
        Examples:
            # Delete single key
            result = await client.delete_plan_state(
                plan_id="plan-123",
                tenant_id="tenant-1",
                user_id="user-1",
                key="agent_state"
            )
            if result.deleted:
                print("Key deleted")
            else:
                print("Key not found")
                
            # Delete all keys for plan (cleanup)
            result = await client.delete_plan_state(
                plan_id="plan-123",
                tenant_id="tenant-1",
                user_id="user-1"
            )
            print(f"Deleted {result.count_deleted} keys")
        """
        if key:
            # Delete single key
            response = await self._client.delete(
                f"{self.base_url}/v1/memory/working/{plan_id}/{key}",
                headers={
                    "X-Tenant-ID": tenant_id,
                    "X-User-ID": user_id,
                },
            )
            response.raise_for_status()
            return WorkingMemoryDeleteKeyResponse.model_validate(response.json())
        else:
            # Delete all keys for plan
            response = await self._client.delete(
                f"{self.base_url}/v1/memory/working/{plan_id}",
                headers={
                    "X-Tenant-ID": tenant_id,
                    "X-User-ID": user_id,
                },
            )
            response.raise_for_status()
            return WorkingMemoryDeletePlanResponse.model_validate(response.json())
    
    # Health Check
    
    async def health(self) -> Dict[str, Any]:
        """
        Check if the Memory Service is healthy.
        
        Returns:
            Health status dictionary
        """
        response = await self._client.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()
    
    # Task Context Methods (for async Worker completion)
    
    async def store_task_context(
        self,
        task_id: str,
        plan_id: Optional[str],
        event_type: str,
        response_event: Optional[str] = None,
        response_topic: str = 'action-results',
        data: Optional[Dict[str, Any]] = None,
        sub_tasks: Optional[List[str]] = None,
        state: Optional[Dict[str, Any]] = None,
    ) -> TaskContextResponse:
        """
        Store task context for async completion.
        
        Called by TaskContext.save() when Worker delegates to sub-agent.
        
        Args:
            task_id: Task identifier
            plan_id: Optional plan identifier
            event_type: Event type that triggered this task
            response_event: Expected response event
            response_topic: Response topic (default: action-results)
            data: Original request data
            sub_tasks: List of sub-task IDs
            state: Worker-specific state
            
        Returns:
            TaskContextResponse with the stored context
        """
        request_data = TaskContextCreate(
            task_id=task_id,
            plan_id=plan_id,
            event_type=event_type,
            response_event=response_event,
            response_topic=response_topic,
            data=data or {},
            sub_tasks=sub_tasks or [],
            state=state or {},
        )
        
        response = await self._client.post(
            f"{self.base_url}/v1/memory/task-context",
            json=request_data.model_dump(by_alias=True),
        )
        response.raise_for_status()
        return TaskContextResponse.model_validate(response.json())
    
    async def get_task_context(self, task_id: str) -> Optional[TaskContextResponse]:
        """
        Retrieve task context.
        
        Called by TaskContext.restore() when Worker resumes after result.
        
        Args:
            task_id: Task identifier
            
        Returns:
            TaskContextResponse or None if not found
        """
        try:
            response = await self._client.get(
                f"{self.base_url}/v1/memory/task-context/{task_id}",
            )
            response.raise_for_status()
            return TaskContextResponse.model_validate(response.json())
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise
    
    async def update_task_context(
        self,
        task_id: str,
        sub_tasks: Optional[List[str]] = None,
        state: Optional[Dict[str, Any]] = None,
    ) -> TaskContextResponse:
        """
        Update task context.
        
        Args:
            task_id: Task identifier
            sub_tasks: Updated sub-task list
            state: Updated state
            
        Returns:
            TaskContextResponse with updated context
        """
        request_data = TaskContextUpdate(
            sub_tasks=sub_tasks,
            state=state,
        )
        
        response = await self._client.put(
            f"{self.base_url}/v1/memory/task-context/{task_id}",
            json=request_data.model_dump(by_alias=True, exclude_none=True),
        )
        response.raise_for_status()
        return TaskContextResponse.model_validate(response.json())
    
    async def delete_task_context(self, task_id: str) -> bool:
        """
        Delete task context after completion.
        
        Called by TaskContext.complete() to cleanup.
        
        Args:
            task_id: Task identifier
            
        Returns:
            True if deleted, False if not found
        """
        try:
            response = await self._client.delete(
                f"{self.base_url}/v1/memory/task-context/{task_id}",
            )
            response.raise_for_status()
            return True
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return False
            raise
    
    async def get_task_by_subtask(self, sub_task_id: str) -> Optional[TaskContextResponse]:
        """
        Find parent task by sub-task correlation ID.
        
        Called by ResultContext.restore_task() to find parent task.
        
        Args:
            sub_task_id: Sub-task identifier
            
        Returns:
            TaskContextResponse or None if not found
        """
        try:
            response = await self._client.get(
                f"{self.base_url}/v1/memory/task-context/by-subtask/{sub_task_id}",
            )
            response.raise_for_status()
            return TaskContextResponse.model_validate(response.json())
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise
    
    # Plan Context Methods (for Planner state machine)
    
    async def store_plan_context(
        self,
        plan_id: str,
        session_id: Optional[str],
        goal_event: str,
        goal_data: Dict[str, Any],
        response_event: Optional[str] = None,
        state: Optional[Dict[str, Any]] = None,
        current_state: Optional[str] = None,
        correlation_ids: Optional[List[str]] = None,
    ) -> PlanContextResponse:
        """
        Store plan context.
        
        Called by PlanContext.save() after state transitions.
        
        Args:
            plan_id: Plan identifier
            session_id: Optional session identifier
            goal_event: Goal event type
            goal_data: Goal data
            response_event: Expected response event
            state: Plan state machine
            current_state: Current state name
            correlation_ids: List of correlation IDs
            
        Returns:
            PlanContextResponse with the stored context
        """
        request_data = PlanContextCreate(
            plan_id=plan_id,
            session_id=session_id,
            goal_event=goal_event,
            goal_data=goal_data,
            response_event=response_event,
            state=state or {},
            current_state=current_state,
            correlation_ids=correlation_ids or [],
        )
        
        response = await self._client.post(
            f"{self.base_url}/v1/memory/plan-context",
            json=request_data.model_dump(by_alias=True),
        )
        response.raise_for_status()
        return PlanContextResponse.model_validate(response.json())
    
    async def get_plan_context(self, plan_id: str) -> Optional[PlanContextResponse]:
        """
        Retrieve plan context.
        
        Called by PlanContext.restore() to resume plan execution.
        
        Args:
            plan_id: Plan identifier
            
        Returns:
            PlanContextResponse or None if not found
        """
        try:
            response = await self._client.get(
                f"{self.base_url}/v1/memory/plan-context/{plan_id}",
            )
            response.raise_for_status()
            return PlanContextResponse.model_validate(response.json())
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise
    
    async def update_plan_context(
        self,
        plan_id: str,
        state: Optional[Dict[str, Any]] = None,
        current_state: Optional[str] = None,
        correlation_ids: Optional[List[str]] = None,
    ) -> PlanContextResponse:
        """
        Update plan context.
        
        Args:
            plan_id: Plan identifier
            state: Updated state
            current_state: Updated current state
            correlation_ids: Updated correlation IDs
            
        Returns:
            PlanContextResponse with updated context
        """
        request_data = PlanContextUpdate(
            state=state,
            current_state=current_state,
            correlation_ids=correlation_ids,
        )
        
        response = await self._client.put(
            f"{self.base_url}/v1/memory/plan-context/{plan_id}",
            json=request_data.model_dump(by_alias=True, exclude_none=True),
        )
        response.raise_for_status()
        return PlanContextResponse.model_validate(response.json())
    
    async def get_plan_by_correlation(self, correlation_id: str) -> Optional[PlanContextResponse]:
        """
        Find plan by task/step correlation ID.
        
        Called when a transition event arrives to find the owning plan.
        
        Args:
            correlation_id: Correlation identifier
            
        Returns:
            PlanContextResponse or None if not found
        """
        try:
            response = await self._client.get(
                f"{self.base_url}/v1/memory/plan-context/by-correlation/{correlation_id}",
            )
            response.raise_for_status()
            return PlanContextResponse.model_validate(response.json())
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise
    
    # Plans & Sessions Management
    
    async def create_plan(
        self,
        plan_id: str,
        goal_event: str,
        goal_data: Dict[str, Any],
        tenant_id: str,
        user_id: str,
        session_id: Optional[str] = None,
        parent_plan_id: Optional[str] = None,
    ) -> PlanSummary:
        """
        Create a new plan record.
        
        Called when a Planner receives a goal and creates a plan.
        
        Args:
            plan_id: Plan identifier
            goal_event: Goal event type
            goal_data: Goal data
            tenant_id: Tenant ID (required for multi-tenant isolation)
            user_id: User ID (required for ownership)
            session_id: Optional session identifier
            parent_plan_id: Optional parent plan identifier
            
        Returns:
            PlanSummary with the created plan
        """
        request_data = PlanCreate(
            plan_id=plan_id,
            session_id=session_id,
            goal_event=goal_event,
            goal_data=goal_data,
            parent_plan_id=parent_plan_id,
        )
        
        response = await self._client.post(
            f"{self.base_url}/v1/memory/plans",
            json=request_data.model_dump(by_alias=True),
            headers={
                "X-Tenant-ID": tenant_id,
                "X-User-ID": user_id,
            },
        )
        response.raise_for_status()
        return PlanSummary.model_validate(response.json())
    
    async def delete_plan(
        self,
        plan_id: str,
        tenant_id: str,
        user_id: str,
    ) -> bool:
        """
        Delete a plan record and all associated working memory state.
        
        This performs a complete cleanup:
        1. Deletes all working memory keys for the plan
        2. Deletes the Plan metadata record
        
        Args:
            plan_id: Plan identifier
            tenant_id: Tenant ID (required for multi-tenant isolation)
            user_id: User ID (required for ownership)
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            httpx.HTTPStatusError: If deletion fails
        """
        try:
            # First, clean up all working memory state for this plan
            try:
                await self.delete_plan_state(
                    plan_id=plan_id,
                    tenant_id=tenant_id,
                    user_id=user_id
                )
            except httpx.HTTPStatusError:
                # Ignore errors - working memory may not exist
                pass
            
            # Then delete the Plan record itself
            response = await self._client.delete(
                f"{self.base_url}/v1/memory/plans/{plan_id}",
                headers={
                    "X-Tenant-ID": tenant_id,
                    "X-User-ID": user_id,
                },
            )
            response.raise_for_status()
            return True
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return False
            raise
    
    async def create_session(
        self,
        session_id: str,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SessionSummary:
        """
        Create a new session/conversation record.
        
        Sessions group related plans and provide conversation context.
        
        Args:
            session_id: Session identifier
            name: Optional session name
            metadata: Optional session metadata
            
        Returns:
            SessionSummary with the created session
        """
        request_data = SessionCreate(
            session_id=session_id,
            name=name,
            metadata=metadata or {},
        )
        
        response = await self._client.post(
            f"{self.base_url}/v1/memory/sessions",
            json=request_data.model_dump(by_alias=True),
        )
        response.raise_for_status()
        return SessionSummary.model_validate(response.json())
    
    async def list_plans(
        self,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        session_id: Optional[str] = None,
        limit: int = 20,
    ) -> List[PlanSummary]:
        """
        List plans for a user.
        
        Args:
            tenant_id: Tenant ID. If not provided, lists all accessible plans
            user_id: User ID. If not provided, lists all accessible plans
            status: Filter by status (running, completed, failed, paused)
            session_id: Filter by session
            limit: Maximum number of results (1-100)
            
        Returns:
            List of PlanSummary ordered by recency
        """
        params = {"limit": limit}
        if status:
            params["status"] = status
        if session_id:
            params["session_id"] = session_id
        
        headers = {}
        if tenant_id:
            headers["X-Tenant-ID"] = tenant_id
        if user_id:
            headers["X-User-ID"] = user_id
        
        response = await self._client.get(
            f"{self.base_url}/v1/memory/plans",
            params=params,
            headers=headers if headers else None,
        )
        response.raise_for_status()
        return [PlanSummary.model_validate(item) for item in response.json()]
    
    async def list_sessions(
        self,
        limit: int = 20,
    ) -> List[SessionSummary]:
        """
        List active sessions/conversations for the authenticated user.
        
        Args:
            limit: Maximum number of results (1-100)
            
        Returns:
            List of SessionSummary ordered by last interaction
        """
        response = await self._client.get(
            f"{self.base_url}/v1/memory/sessions",
            params={"limit": limit},
        )
        response.raise_for_status()
        return [SessionSummary.model_validate(item) for item in response.json()]

