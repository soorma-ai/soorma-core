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
        calendar_tool = await context.registry.find("calendar_api_tool")
        
        # Shared Memory
        vehicle = await context.memory.retrieve(f"vehicle:{task.data['vehicle_id']}")
        
        # Event Publishing (automatic state tracking by platform)
        await context.bus.publish("technician_scheduled", result)
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import httpx
import logging
import os

from .events import EventClient
from .memory import MemoryClient as MemoryServiceClient

logger = logging.getLogger(__name__)


@dataclass
class RegistryClient:
    """
    Service Discovery & Capabilities client.
    
    Powered by: PostgreSQL + gRPC (in production)
    
    Methods:
        find(): Locate agents by capability
        register(): Announce your services  
        query_schemas(): Get event DTOs
    """
    base_url: str = field(default_factory=lambda: os.getenv("SOORMA_REGISTRY_URL", "http://localhost:8081"))
    _http_client: Optional[httpx.AsyncClient] = field(default=None, repr=False)
    
    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient()
        return self._http_client
    
    async def find(self, capability: str) -> Optional[Dict[str, Any]]:
        """
        Locate agents by capability.
        
        Args:
            capability: The capability to search for (e.g., "calendar_api_tool")
            
        Returns:
            Agent info dict if found, None otherwise
        """
        client = await self._ensure_client()
        try:
            response = await client.get(
                f"{self.base_url}/v1/agents/search",
                params={"capability": capability},
                timeout=10.0,
            )
            if response.status_code == 200:
                results = response.json()
                return results[0] if results else None
            return None
        except Exception as e:
            logger.error(f"Registry lookup failed: {e}")
            return None
    
    async def find_all(self, capability: str) -> List[Dict[str, Any]]:
        """
        Find all agents with a specific capability.
        
        Args:
            capability: The capability to search for
            
        Returns:
            List of agent info dicts
        """
        client = await self._ensure_client()
        try:
            response = await client.get(
                f"{self.base_url}/v1/agents/search",
                params={"capability": capability},
                timeout=10.0,
            )
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            logger.error(f"Registry lookup failed: {e}")
            return []
    
    async def register(
        self,
        agent_id: str,
        name: str,
        agent_type: str,
        capabilities: List[Any],  # Can be str or AgentCapability
        events_consumed: List[str],
        events_produced: List[str],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Register an agent with the platform.
        
        Args:
            agent_id: Unique identifier for the agent
            name: Human-readable name
            agent_type: Type of agent (planner, worker, tool)
            capabilities: List of capabilities (strings or AgentCapability objects)
            events_consumed: Event types this agent subscribes to
            events_produced: Event types this agent publishes
            metadata: Optional additional metadata
            
        Returns:
            True if registration succeeded
        """
        client = await self._ensure_client()
        
        # Convert capabilities to structured format if they are strings
        structured_capabilities = []
        for cap in capabilities:
            if isinstance(cap, str):
                # Auto-convert string capability to structured
                structured_capabilities.append({
                    "taskName": cap,
                    "description": f"Capability: {cap}",
                    "consumedEvent": "unknown",
                    "producedEvents": []
                })
            elif hasattr(cap, "model_dump"):
                # It's a Pydantic model (AgentCapability)
                structured_capabilities.append(cap.model_dump(by_alias=True))
            elif isinstance(cap, dict):
                # Already a dict
                structured_capabilities.append(cap)
            else:
                logger.warning(f"Unknown capability format: {cap}")

        # Construct the full AgentDefinition structure
        agent_def = {
            "agentId": agent_id,
            "name": name,
            "description": (metadata or {}).get("description", ""),
            "capabilities": structured_capabilities,
            "consumedEvents": events_consumed,
            "producedEvents": events_produced
        }

        try:
            # Wrap in AgentRegistrationRequest structure
            request_payload = {"agent": agent_def}
            
            response = await client.post(
                f"{self.base_url}/v1/agents",
                json=request_payload,
                timeout=10.0,
            )
            return response.status_code in (200, 201)
        except Exception as e:
            logger.error(f"Registry registration failed: {e}")
            return False

    async def register_event(self, event_definition: Any) -> bool:
        """
        Register an event definition.
        
        Args:
            event_definition: EventDefinition object or dict
            
        Returns:
            True if registration succeeded
        """
        client = await self._ensure_client()
        
        payload = event_definition
        if hasattr(event_definition, "model_dump"):
            payload = event_definition.model_dump(by_alias=True)
            
        # Wrap in EventRegistrationRequest structure
        request_payload = {"event": payload}
            
        try:
            response = await client.post(
                f"{self.base_url}/v1/events",
                json=request_payload,
                timeout=10.0,
            )
            return response.status_code in (200, 201)
        except Exception as e:
            logger.error(f"Event registration failed: {e}")
            return False
    
    async def deregister(self, agent_id: str) -> bool:
        """
        Remove an agent from the registry.
        
        Args:
            agent_id: The agent ID to remove
            
        Returns:
            True if deregistration succeeded
        """
        client = await self._ensure_client()
        try:
            response = await client.delete(
                f"{self.base_url}/v1/agents/{agent_id}",
                timeout=10.0,
            )
            return response.status_code in (200, 204)
        except Exception as e:
            logger.error(f"Registry deregistration failed: {e}")
            return False
    
    async def query_schemas(self, event_type: str) -> Optional[Dict[str, Any]]:
        """
        Get the JSON schema for an event type.
        
        Args:
            event_type: The event type to get schema for
            
        Returns:
            JSON schema dict if found, None otherwise
        """
        client = await self._ensure_client()
        try:
            response = await client.get(
                f"{self.base_url}/v1/events",
                params={"event_name": event_type},
                timeout=10.0,
            )
            if response.status_code == 200:
                data = response.json()
                events = data.get("events", [])
                if events:
                    return events[0].get("payload_schema")
            return None
        except Exception as e:
            logger.error(f"Schema query failed: {e}")
            return None
    
    async def heartbeat(self, agent_id: str) -> bool:
        """
        Send a heartbeat to keep registration alive.
        
        Args:
            agent_id: The agent ID
            
        Returns:
            True if heartbeat succeeded
        """
        client = await self._ensure_client()
        try:
            response = await client.post(
                f"{self.base_url}/v1/agents/{agent_id}/heartbeat",
                timeout=5.0,
            )
            return response.status_code == 200
        except Exception as e:
            logger.debug(f"Heartbeat failed: {e}")
            return False
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None


@dataclass
class MemoryClient:
    """
    Distributed State Management client.
    
    Powered by: Memory Service (PostgreSQL + pgvector)
    
    Memory types (CoALA framework):
    - Procedural: How to do things (skills, procedures)
    - Semantic: Facts and knowledge (RAG with vector search)
    - Episodic: Past experiences and events (interaction history)
    - Working: Current task context (plan-scoped state)
    
    Methods:
        retrieve(): Read shared memory
        store(): Persist agent state
        search(): Semantic memory lookup
        log_interaction(): Store episodic memory
        get_recent_history(): Retrieve recent interactions
        get_relevant_skills(): Fetch procedural memories
    """
    base_url: str = field(default_factory=lambda: os.getenv("SOORMA_MEMORY_SERVICE_URL", "http://localhost:8083"))
    # Fallback in-memory storage for development (when Memory Service is not available)
    _local_store: Dict[str, Any] = field(default_factory=dict, repr=False, init=False)
    _use_local: bool = field(default=False, repr=False, init=False)  # Try service first, fallback to local
    _client: Optional[MemoryServiceClient] = field(default=None, repr=False, init=False)
    
    async def _ensure_client(self) -> MemoryServiceClient:
        if self._client is None:
            self._client = MemoryServiceClient(base_url=self.base_url)
            # Test connection
            try:
                await self._client.health()
                logger.info(f"Connected to Memory Service at {self.base_url}")
            except Exception as e:
                logger.warning(f"Memory Service unavailable, using local fallback: {e}")
                self._use_local = True
        return self._client
    
    async def retrieve(self, key: str, plan_id: Optional[str] = None) -> Optional[Any]:
        """
        Read shared memory by key (Working Memory).
        
        Args:
            key: Memory key (e.g., "research_summary", "account_id")
            plan_id: Plan ID for working memory scope (defaults to "default")
            
        Returns:
            Stored value if found, None otherwise
        """
        if self._use_local:
            value = self._local_store.get(key)
            logger.debug(f"Memory retrieve (local): {key} -> {value is not None}")
            return value
        
        client = await self._ensure_client()
        try:
            plan = plan_id or "default"
            result = await client.get_plan_state(plan, key)
            return result.value
        except Exception as e:
            if "404" in str(e):
                return None
            logger.debug(f"Memory retrieve failed, using local: {e}")
            self._use_local = True
            return self._local_store.get(key)
    
    async def store(
        self,
        key: str,
        value: Any,
        plan_id: Optional[str] = None,
        memory_type: str = "working",
    ) -> bool:
        """
        Persist agent state to shared memory.
        
        Args:
            key: Memory key
            value: Value to store (will be JSON serialized)
            plan_id: Plan ID for working memory scope (defaults to "default")
            memory_type: Type of memory (working, semantic, episodic, procedural)
            
        Returns:
            True if store succeeded
        """
        if self._use_local:
            self._local_store[key] = value
            logger.debug(f"Memory store (local): {key}")
            return True
        
        client = await self._ensure_client()
        try:
            plan = plan_id or "default"
            if memory_type == "working":
                await client.set_plan_state(plan, key, value)
            elif memory_type == "semantic":
                content = str(value)
                await client.store_knowledge(content, metadata={"key": key})
            else:
                logger.warning(f"Unsupported memory_type for store(): {memory_type}")
                return False
            return True
        except Exception as e:
            logger.debug(f"Memory store failed, using local: {e}")
            self._use_local = True
            self._local_store[key] = value
            return True
    
    async def search(
        self,
        query: str,
        memory_type: str = "semantic",
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Semantic memory lookup (vector search).
        
        Args:
            query: Natural language search query
            memory_type: Type of memory ("semantic" or "episodic")
            limit: Maximum results to return (1-50)
            
        Returns:
            List of matching memory entries with similarity scores
        """
        if self._use_local:
            logger.debug(f"Memory search (local): '{query}' - semantic search not available in dev mode")
            return []
        
        client = await self._ensure_client()
        try:
            if memory_type == "semantic":
                results = await client.search_knowledge(query, limit=limit)
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
            else:
                logger.warning(f"Unsupported memory_type for search(): {memory_type}")
                return []
        except Exception as e:
            logger.debug(f"Memory search failed: {e}")
            self._use_local = True
            return []
    
    async def log_interaction(
        self,
        agent_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Log an interaction to episodic memory.
        
        Args:
            agent_id: Agent identifier
            role: Role (user, assistant, system, tool)
            content: Interaction content
            metadata: Optional metadata
            
        Returns:
            True if log succeeded
        """
        if self._use_local:
            logger.debug(f"Memory log_interaction (local): {agent_id} - not persisted")
            return True
        
        client = await self._ensure_client()
        try:
            await client.log_interaction(agent_id, role, content, metadata)
            return True
        except Exception as e:
            logger.debug(f"Memory log_interaction failed: {e}")
            self._use_local = True
            return False
    
    async def get_recent_history(
        self,
        agent_id: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Get recent interaction history (context window).
        
        Args:
            agent_id: Agent identifier
            limit: Maximum number of results (1-100)
            
        Returns:
            List of recent interactions ordered by recency
        """
        if self._use_local:
            logger.debug(f"Memory get_recent_history (local): {agent_id} - not available in dev mode")
            return []
        
        client = await self._ensure_client()
        try:
            results = await client.get_recent_history(agent_id, limit=limit)
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
        except Exception as e:
            logger.debug(f"Memory get_recent_history failed: {e}")
            self._use_local = True
            return []
    
    async def get_relevant_skills(
        self,
        agent_id: str,
        context: str,
        limit: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Get relevant procedural knowledge (skills, prompts, rules).
        
        Args:
            agent_id: Agent identifier
            context: Task/query context
            limit: Maximum number of results (1-20)
            
        Returns:
            List of relevant skills ordered by relevance
        """
        if self._use_local:
            logger.debug(f"Memory get_relevant_skills (local): {agent_id} - not available in dev mode")
            return []
        
        client = await self._ensure_client()
        try:
            results = await client.get_relevant_skills(agent_id, context, limit=limit)
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
        except Exception as e:
            logger.debug(f"Memory get_relevant_skills failed: {e}")
            self._use_local = True
            return []
    
    async def delete(self, key: str, plan_id: Optional[str] = None) -> bool:
        """
        Delete a memory entry (Working Memory).
        
        Args:
            key: Memory key to delete
            plan_id: Plan ID for working memory scope (defaults to "default")
            
        Returns:
            True if deletion succeeded
        """
        if self._use_local:
            self._local_store.pop(key, None)
            logger.debug(f"Memory delete (local): {key}")
            return True
        
        # Note: Memory Service doesn't have a delete endpoint yet
        logger.warning("Memory delete not implemented in Memory Service")
        return False
    
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
        publish(): Emit domain events
        subscribe(): React to events (via EventClient)
        request(): RPC-style calls
    """
    event_client: EventClient = field(default_factory=EventClient)
    
    async def publish(
        self,
        event_type: str,
        data: Dict[str, Any],
        topic: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> str:
        """
        Emit a domain event.
        
        Args:
            event_type: Event type (e.g., "technician_scheduled")
            data: Event payload
            topic: Target topic (auto-inferred from event_type if not provided)
            correlation_id: Optional correlation ID for tracing
            
        Returns:
            The event ID
        """
        # Auto-infer topic from event type if not provided
        if topic is None:
            topic = self._infer_topic(event_type)
        
        return await self.event_client.publish(
            event_type=event_type,
            topic=topic,
            data=data,
            correlation_id=correlation_id,
        )
    
    def _infer_topic(self, event_type: str) -> str:
        """Infer the topic from event type based on conventions."""
        # Map common patterns to topics
        if event_type.endswith(".requested") or event_type.endswith(".request"):
            return "action-requests"
        elif event_type.endswith(".completed") or event_type.endswith(".result"):
            return "action-results"
        elif event_type.startswith("billing."):
            return "billing"
        elif event_type.startswith("notification."):
            return "notifications"
        else:
            return "business-facts"
    
    async def subscribe(self, topics: List[str]) -> None:
        """
        Subscribe to event topics.
        
        This connects to the Event Service and starts receiving events.
        Use @event_client.on_event() decorator to register handlers.
        
        Args:
            topics: List of topic patterns to subscribe to
        """
        await self.event_client.connect(topics=topics)
    
    async def request(
        self,
        event_type: str,
        data: Dict[str, Any],
        timeout: float = 30.0,
    ) -> Optional[Dict[str, Any]]:
        """
        RPC-style request/response.
        
        Publishes a request event and waits for a correlated response.
        
        Args:
            event_type: Request event type
            data: Request payload
            timeout: Timeout in seconds
            
        Returns:
            Response data if received, None on timeout
        """
        import asyncio
        from uuid import uuid4
        
        correlation_id = str(uuid4())
        response_received = asyncio.Event()
        response_data: Dict[str, Any] = {}
        
        # Create a one-time handler for the response
        async def handle_response(event: Dict[str, Any]) -> None:
            if event.get("correlation_id") == correlation_id:
                response_data.update(event.get("data", {}))
                response_received.set()
        
        # Register temporary handler
        response_type = event_type.replace(".request", ".response")
        original_handlers = self.event_client._handlers.get(response_type, [])
        self.event_client._handlers.setdefault(response_type, []).append(handle_response)
        
        try:
            # Publish request
            await self.publish(
                event_type=event_type,
                data=data,
                correlation_id=correlation_id,
            )
            
            # Wait for response
            try:
                await asyncio.wait_for(response_received.wait(), timeout=timeout)
                return response_data
            except asyncio.TimeoutError:
                logger.warning(f"Request {event_type} timed out after {timeout}s")
                return None
        finally:
            # Cleanup handler
            if handle_response in self.event_client._handlers.get(response_type, []):
                self.event_client._handlers[response_type].remove(handle_response)
    
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
    
    Usage:
        @worker.on_task("schedule_technician")
        async def schedule_service(task, context: PlatformContext):
            # Service Discovery
            calendar_tool = await context.registry.find("calendar_api_tool")
            
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
    registry: RegistryClient = field(default_factory=RegistryClient)
    memory: MemoryClient = field(default_factory=MemoryClient)
    bus: BusClient = field(default_factory=BusClient)
    tracker: TrackerClient = field(default_factory=TrackerClient)
    
    @classmethod
    def from_env(cls) -> "PlatformContext":
        """
        Create a PlatformContext from environment variables.
        
        Environment variables:
            SOORMA_REGISTRY_URL: Registry service URL
            SOORMA_EVENT_SERVICE_URL: Event service URL
            SOORMA_MEMORY_URL: Memory service URL
            SOORMA_TRACKER_URL: Tracker service URL
        """
        event_client = EventClient(
            event_service_url=os.getenv("SOORMA_EVENT_SERVICE_URL", "http://localhost:8082"),
        )
        
        return cls(
            registry=RegistryClient(
                base_url=os.getenv("SOORMA_REGISTRY_URL", "http://localhost:8081"),
            ),
            memory=MemoryClient(
                base_url=os.getenv("SOORMA_MEMORY_URL", "http://localhost:8083"),
            ),
            bus=BusClient(event_client=event_client),
            tracker=TrackerClient(
                base_url=os.getenv("SOORMA_TRACKER_URL", "http://localhost:8084"),
            ),
        )
    
    async def close(self) -> None:
        """Close all clients."""
        await self.registry.close()
        await self.memory.close()
        await self.bus.close()
        await self.tracker.close()
