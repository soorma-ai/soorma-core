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
        capabilities: List[str],
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
            capabilities: List of capabilities offered
            events_consumed: Event types this agent subscribes to
            events_produced: Event types this agent publishes
            metadata: Optional additional metadata
            
        Returns:
            True if registration succeeded
        """
        client = await self._ensure_client()
        try:
            response = await client.post(
                f"{self.base_url}/v1/agents",
                json={
                    "agent_id": agent_id,
                    "name": name,
                    "agent_type": agent_type,
                    "capabilities": capabilities,
                    "events_consumed": events_consumed,
                    "events_produced": events_produced,
                    "metadata": metadata or {},
                },
                timeout=10.0,
            )
            return response.status_code in (200, 201)
        except Exception as e:
            logger.error(f"Registry registration failed: {e}")
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
                f"{self.base_url}/v1/events/schemas/{event_type}",
                timeout=10.0,
            )
            if response.status_code == 200:
                return response.json()
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
    
    Powered by: Redis + Vector DB (in production)
    
    Memory types:
    - Procedural: How to do things (skills, procedures)
    - Semantic: Facts and knowledge
    - Episodic: Past experiences and events
    - Working: Current task context
    
    Methods:
        retrieve(): Read shared memory
        store(): Persist agent state
        search(): Semantic memory lookup
    
    NOTE: Memory Service is not yet implemented. This client provides
    a mock implementation that stores data in-memory for development.
    """
    base_url: str = field(default_factory=lambda: os.getenv("SOORMA_MEMORY_URL", "http://localhost:8083"))
    _http_client: Optional[httpx.AsyncClient] = field(default=None, repr=False)
    # In-memory storage for development (when Memory Service is not available)
    _local_store: Dict[str, Any] = field(default_factory=dict, repr=False)
    _use_local: bool = field(default=True, repr=False)  # Use local store by default until service is implemented
    
    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient()
        return self._http_client
    
    async def retrieve(self, key: str) -> Optional[Any]:
        """
        Read shared memory by key.
        
        Args:
            key: Memory key (e.g., "vehicle:123", "user:abc")
            
        Returns:
            Stored value if found, None otherwise
        """
        # Use local store for development
        if self._use_local:
            value = self._local_store.get(key)
            logger.debug(f"Memory retrieve (local): {key} -> {value is not None}")
            return value
        
        client = await self._ensure_client()
        try:
            response = await client.get(
                f"{self.base_url}/v1/memory/{key}",
                timeout=10.0,
            )
            if response.status_code == 200:
                return response.json().get("value")
            return None
        except Exception as e:
            logger.debug(f"Memory retrieve failed, using local: {e}")
            return self._local_store.get(key)
    
    async def store(
        self,
        key: str,
        value: Any,
        memory_type: str = "working",
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Persist agent state to shared memory.
        
        Args:
            key: Memory key
            value: Value to store (will be JSON serialized)
            memory_type: Type of memory (working, semantic, episodic, procedural)
            ttl: Time-to-live in seconds (optional)
            
        Returns:
            True if store succeeded
        """
        # Use local store for development
        if self._use_local:
            self._local_store[key] = value
            logger.debug(f"Memory store (local): {key}")
            return True
        
        client = await self._ensure_client()
        try:
            payload = {
                "key": key,
                "value": value,
                "memory_type": memory_type,
            }
            if ttl:
                payload["ttl"] = ttl
            
            response = await client.post(
                f"{self.base_url}/v1/memory",
                json=payload,
                timeout=10.0,
            )
            return response.status_code in (200, 201)
        except Exception as e:
            logger.debug(f"Memory store failed, using local: {e}")
            self._local_store[key] = value
            return True
    
    async def search(
        self,
        query: str,
        memory_type: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Semantic memory lookup.
        
        Args:
            query: Natural language search query
            memory_type: Filter by memory type (optional)
            limit: Maximum results to return
            
        Returns:
            List of matching memory entries with similarity scores
        """
        # Local store doesn't support semantic search
        if self._use_local:
            logger.debug(f"Memory search (local): '{query}' - semantic search not available in dev mode")
            return []
        
        client = await self._ensure_client()
        try:
            params = {"q": query, "limit": limit}
            if memory_type:
                params["type"] = memory_type
            
            response = await client.get(
                f"{self.base_url}/v1/memory/search",
                params=params,
                timeout=10.0,
            )
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            logger.debug(f"Memory search failed: {e}")
            return []
    
    async def delete(self, key: str) -> bool:
        """
        Delete a memory entry.
        
        Args:
            key: Memory key to delete
            
        Returns:
            True if deletion succeeded
        """
        # Use local store for development
        if self._use_local:
            self._local_store.pop(key, None)
            logger.debug(f"Memory delete (local): {key}")
            return True
        
        client = await self._ensure_client()
        try:
            response = await client.delete(
                f"{self.base_url}/v1/memory/{key}",
                timeout=10.0,
            )
            return response.status_code in (200, 204)
        except Exception as e:
            logger.debug(f"Memory delete failed, using local: {e}")
            self._local_store.pop(key, None)
            return True
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None


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
