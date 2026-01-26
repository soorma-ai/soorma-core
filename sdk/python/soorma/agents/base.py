"""
Base Agent class for all Soorma agents.

The Agent class provides the foundation for all agent types in the DisCo architecture.
It handles:
- Platform context initialization (registry, memory, bus, tracker)
- Event subscription and publishing
- Agent lifecycle (startup, shutdown)
- Registry registration

Usage:
    from soorma.agents import Agent

    agent = Agent(
        name="my-agent",
        description="My custom agent",
        capabilities=["data_analysis"],
    )

    @agent.on_startup
    async def startup():
        print("Agent starting...")

    @agent.on_event("data.requested", topic=EventTopic.ACTION_REQUESTS)
    async def handle_data_request(event: EventEnvelope, context: PlatformContext):
        result = process_data(event.data)
        await context.bus.publish("data.completed", result)

    agent.run()
"""
import asyncio
import logging
import os
import signal
from abc import ABC
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional
from uuid import uuid4

from soorma_common.events import EventEnvelope, EventTopic

from ..context import PlatformContext
from ..events import EventClient

logger = logging.getLogger(__name__)

# Type aliases
EventHandler = Callable[[EventEnvelope, PlatformContext], Awaitable[None]]
LifecycleHandler = Callable[[], Awaitable[None]]


@dataclass
class AgentConfig:
    """Configuration for an agent."""
    # Core identity
    agent_id: str
    name: str
    description: str
    version: str
    agent_type: str  # "agent", "planner", "worker", "tool"
    
    # Capabilities and events
    capabilities: List[Any] = field(default_factory=list)  # List[str] or List[AgentCapability]
    events_consumed: List[str] = field(default_factory=list)
    events_produced: List[str] = field(default_factory=list)
    event_definitions: List[Any] = field(default_factory=list)  # List[EventDefinition]
    
    # Runtime settings
    heartbeat_interval: float = 30.0  # seconds
    auto_register: bool = True
    
    # Platform URLs (from env or defaults)
    registry_url: str = field(
        default_factory=lambda: os.getenv("SOORMA_REGISTRY_URL", "http://localhost:8081")
    )
    event_service_url: str = field(
        default_factory=lambda: os.getenv("SOORMA_EVENT_SERVICE_URL", "http://localhost:8082")
    )
    memory_url: str = field(
        default_factory=lambda: os.getenv("SOORMA_MEMORY_URL", "http://localhost:8083")
    )
    tracker_url: str = field(
        default_factory=lambda: os.getenv("SOORMA_TRACKER_URL", "http://localhost:8084")
    )


class Agent(ABC):
    """
    Base class for all Soorma agents.
    
    An Agent is an autonomous unit in the DisCo architecture that:
    - Registers with the Soorma Registry on startup
    - Subscribes to events it can handle
    - Processes events using registered handlers
    - Publishes result events
    
    The base Agent class is framework-agnostic - you can use it directly
    or through the specialized Planner, Worker, and Tool classes.
    
    Attributes:
        name: Human-readable name of the agent
        description: What this agent does
        version: Semantic version string
        capabilities: List of capabilities this agent provides
        config: Full agent configuration
        context: Platform context (registry, memory, bus, tracker)
    
    Usage:
        agent = Agent(
            name="data-processor",
            description="Processes incoming data requests",
            capabilities=["data_processing", "csv_parsing"],
        )
        
        @agent.on_event("data.requested", topic=EventTopic.ACTION_REQUESTS)
        async def handle_request(event: EventEnvelope, context: PlatformContext):
            # Process the event
            result = await process(event.data)
            # Publish result
            await context.bus.publish("data.completed", {"result": result})
        
        agent.run()
    """
    
    def __init__(
        self,
        name: str,
        description: str = "",
        version: str = "0.1.0",
        agent_type: str = "agent",
        capabilities: Optional[List[Any]] = None,
        events_consumed: Optional[List[Any]] = None,
        events_produced: Optional[List[Any]] = None,
        agent_id: Optional[str] = None,
        auto_register: bool = True,
    ):
        """
        Initialize the agent.
        
        Args:
            name: Human-readable name
            description: What this agent does
            version: Semantic version (default: "0.1.0")
            agent_type: Type of agent ("agent", "planner", "worker", "tool")
            capabilities: List of capabilities provided (strings or AgentCapability objects)
            events_consumed: Event types this agent subscribes to (strings or EventDefinition objects)
            events_produced: Event types this agent publishes (strings or EventDefinition objects)
            agent_id: Unique ID (auto-generated if not provided)
            auto_register: Whether to register with Registry on startup
        """
        # Process events to separate strings and definitions
        consumed_strings = []
        produced_strings = []
        definitions = []

        if events_consumed:
            for e in events_consumed:
                if isinstance(e, str):
                    consumed_strings.append(e)
                elif hasattr(e, "event_name"):
                    consumed_strings.append(e.event_name)
                    definitions.append(e)
                elif hasattr(e, "event_type"):
                    consumed_strings.append(e.event_type)
                    definitions.append(e)
                elif isinstance(e, dict):
                    if "event_name" in e:
                        consumed_strings.append(e["event_name"])
                        definitions.append(e)
                    elif "event_type" in e:
                        consumed_strings.append(e["event_type"])
                        definitions.append(e)

        if events_produced:
            for e in events_produced:
                if isinstance(e, str):
                    produced_strings.append(e)
                elif hasattr(e, "event_name"):
                    produced_strings.append(e.event_name)
                    definitions.append(e)
                elif hasattr(e, "event_type"):
                    produced_strings.append(e.event_type)
                    definitions.append(e)
                elif isinstance(e, dict):
                    if "event_name" in e:
                        produced_strings.append(e["event_name"])
                        definitions.append(e)
                    elif "event_type" in e:
                        produced_strings.append(e["event_type"])
                        definitions.append(e)

        self.config = AgentConfig(
            agent_id=agent_id or f"{name}-{str(uuid4())[:8]}",
            name=name,
            description=description,
            version=version,
            agent_type=agent_type,
            capabilities=capabilities or [],
            events_consumed=consumed_strings,
            events_produced=produced_strings,
            event_definitions=definitions,
            auto_register=auto_register,
        )
        
        # Convenience accessors
        self.name = name
        self.description = description
        self.version = version
        self.capabilities = self.config.capabilities
        
        # Platform context (initialized on run)
        self._context: Optional[PlatformContext] = None
        
        # Lifecycle handlers
        self._startup_handlers: List[LifecycleHandler] = []
        self._shutdown_handlers: List[LifecycleHandler] = []
        
        # Event handlers: event_type -> handler
        self._event_handlers: Dict[str, List[EventHandler]] = {}
        
        # Runtime state
        self._running = False
        self._heartbeat_task: Optional[asyncio.Task] = None
    
    @property
    def agent_id(self) -> str:
        """Get the unique agent ID."""
        return self.config.agent_id
    
    @property
    def context(self) -> PlatformContext:
        """
        Get the platform context.
        
        Raises:
            RuntimeError: If accessed before agent.run() is called
        """
        if self._context is None:
            raise RuntimeError("Platform context not initialized. Call agent.run() first.")
        return self._context
    
    # =========================================================================
    # Decorators for registering handlers
    # =========================================================================
    
    def on_startup(self, func: LifecycleHandler) -> LifecycleHandler:
        """
        Decorator to register a startup handler.
        
        Startup handlers are called after platform services connect
        but before the agent starts processing events.
        
        Usage:
            @agent.on_startup
            async def startup():
                print("Agent starting...")
        """
        self._startup_handlers.append(func)
        return func
    
    def on_shutdown(self, func: LifecycleHandler) -> LifecycleHandler:
        """
        Decorator to register a shutdown handler.
        
        Shutdown handlers are called when the agent is stopping,
        before disconnecting from platform services.
        
        Usage:
            @agent.on_shutdown
            async def shutdown():
                print("Agent shutting down...")
        """
        self._shutdown_handlers.append(func)
        return func
    
    def on_event(
        self,
        event_type: str,
        *,
        topic: EventTopic,
    ) -> Callable[[EventHandler], EventHandler]:
        """
        Decorator to register an event handler.
        
        Handlers receive the event payload and the platform context.
        Multiple handlers can be registered for the same event type + topic combination.
        
        Usage:
            @agent.on_event("data.requested", topic=EventTopic.ACTION_REQUESTS)
            async def handle_request(event: EventEnvelope, context: PlatformContext):
                result = await process(event.data)
                await context.bus.respond("data.completed", result, correlation_id=event.correlation_id)
        
        Args:
            event_type: The event type to handle
            topic: The topic to subscribe to (required EventTopic enum)
        
        Returns:
            Decorator function
        """
        def decorator(func: EventHandler) -> EventHandler:
            # Create a composite key for topic:event_type (use topic.value for string)
            handler_key = f"{topic.value}:{event_type}"
            
            if handler_key not in self._event_handlers:
                self._event_handlers[handler_key] = []
            self._event_handlers[handler_key].append(func)
            
            # Track in consumed events (just event_type for backwards compatibility)
            if event_type not in self.config.events_consumed:
                self.config.events_consumed.append(event_type)
            
            logger.debug(f"Registered handler for {topic}:{event_type}")
            return func
        return decorator
    
    # =========================================================================
    # Event Publishing (convenience methods)
    # =========================================================================
    
    async def emit(
        self,
        event_type: str,
        data: Dict[str, Any],
        topic: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> str:
        """
        Emit an event to the event bus.
        
        This is a convenience method that delegates to context.bus.publish().
        
        Args:
            event_type: Event type (e.g., "order.created")
            data: Event payload
            topic: Target topic (auto-inferred if not provided)
            correlation_id: Optional correlation ID
        
        Returns:
            The event ID
        """
        return await self.context.bus.publish(
            event_type=event_type,
            data=data,
            topic=topic,
            correlation_id=correlation_id,
        )

    async def register_event(self, event_definition: Any) -> bool:
        """
        Register a custom event schema.
        
        Args:
            event_definition: EventDefinition object or dict
            
        Returns:
            True if registration succeeded
        """
        return await self.context.registry.register_event(event_definition)
    
    # =========================================================================
    # Agent Lifecycle
    # =========================================================================
    
    async def _initialize_context(self) -> None:
        """Initialize the platform context."""
        logger.info(f"Initializing platform context for {self.name}")
        
        # Create EventClient for bus
        event_client = EventClient(
            event_service_url=self.config.event_service_url,
            agent_id=self.agent_id,
            source=self.name,
        )
        
        # Register our event handlers with the EventClient
        # Handlers are keyed by "topic:event_type" in the new model
        for handler_key, handlers in self._event_handlers.items():
            # Extract event_type from handler_key (format is "topic:event_type")
            if ":" in handler_key:
                _, event_type = handler_key.split(":", 1)
            else:
                # Backwards compatibility: if no ":", assume it's just event_type
                event_type = handler_key
            
            for handler in handlers:
                @event_client.on_event(event_type)
                async def wrapped_handler(event: EventEnvelope, h=handler) -> None:
                    # EventClient already deserializes to EventEnvelope
                    await h(event, self._context)
        
        # Create context with clients
        from ..context import RegistryClient, MemoryClient, BusClient, TrackerClient
        
        self._context = PlatformContext(
            registry=RegistryClient(base_url=self.config.registry_url),
            memory=MemoryClient(base_url=self.config.memory_url),
            bus=BusClient(event_client=event_client),
            tracker=TrackerClient(base_url=self.config.tracker_url),
        )
    
    async def _register_with_registry(self) -> bool:
        """Register the agent with the Registry service."""
        if not self.config.auto_register:
            return True
        
        logger.info(f"Registering {self.name} with Registry")
        
        # Register event definitions first
        for event_def in self.config.event_definitions:
            try:
                await self.context.registry.register_event(event_def)
                logger.debug(f"Registered event definition")
            except Exception as e:
                logger.warning(f"Failed to register event definition: {e}")

        # Build AgentDefinition from config
        from soorma_common import AgentDefinition, AgentCapability
        
        # Convert capabilities to AgentCapability objects
        structured_capabilities = []
        for cap in self.config.capabilities:
            if isinstance(cap, str):
                structured_capabilities.append(
                    AgentCapability(
                        task_name=cap,
                        description=f"Capability: {cap}",
                        consumed_event="unknown",
                        produced_events=[]
                    )
                )
            elif isinstance(cap, AgentCapability):
                structured_capabilities.append(cap)
            elif isinstance(cap, dict):
                structured_capabilities.append(AgentCapability(**cap))
        
        agent_def = AgentDefinition(
            agent_id=self.agent_id,
            name=self.name,
            description=self.description,
            version=self.version,
            capabilities=structured_capabilities,
            consumed_events=self.config.events_consumed,
            produced_events=self.config.events_produced
        )
        
        try:
            await self.context.registry.register_agent(agent_def)
            logger.info(f"✓ Registered {self.name} ({self.agent_id})")
            return True
        except Exception as e:
            logger.warning(f"⚠ Failed to register with Registry: {e} (continuing in offline mode)")
            return False
    
    async def _deregister_from_registry(self) -> None:
        """Deregister from the Registry service."""
        if not self.config.auto_register:
            return
        
        logger.info(f"Deregistering {self.name} from Registry")
        # Use DELETE endpoint directly
        try:
            response = await self.context.registry._client.delete(
                f"{self.context.registry.base_url}/v1/agents/{self.agent_id}"
            )
            if response.status_code not in (200, 204):
                logger.warning(f"Failed to deregister: HTTP {response.status_code}")
        except Exception as e:
            logger.warning(f"Failed to deregister: {e}")
    
    async def _start_heartbeat(self) -> None:
        """Start the heartbeat task."""
        async def heartbeat_loop():
            consecutive_failures = 0
            while self._running:
                try:
                    await asyncio.sleep(self.config.heartbeat_interval)
                    if self._running:
                        # Send heartbeat via PUT endpoint
                        try:
                            response = await self.context.registry._client.put(
                                f"{self.context.registry.base_url}/v1/agents/{self.agent_id}/heartbeat"
                            )
                            success = response.status_code == 200
                        except Exception:
                            success = False
                        
                        if not success:
                            consecutive_failures += 1
                            logger.error(
                                f"💔 Heartbeat failed for {self.name} ({self.agent_id}). "
                                f"Agent may be deregistered. (Failures: {consecutive_failures})"
                            )
                            
                            # Attempt to re-register after first failure
                            if consecutive_failures >= 1:
                                logger.warning(
                                    f"🔄 Attempting to re-register {self.name} ({self.agent_id})..."
                                )
                                success = await self._register_with_registry()
                                if success:
                                    logger.info(
                                        f"✅ Successfully re-registered {self.name} ({self.agent_id})"
                                    )
                                    consecutive_failures = 0
                                else:
                                    logger.error(
                                        f"❌ Failed to re-register {self.name} ({self.agent_id})"
                                    )
                        else:
                            # Reset failure counter on successful heartbeat
                            if consecutive_failures > 0:
                                logger.info(
                                    f"💚 Heartbeat restored for {self.name} ({self.agent_id})"
                                )
                            consecutive_failures = 0
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    consecutive_failures += 1
                    logger.error(f"Heartbeat exception for {self.name}: {e}")
        
        self._heartbeat_task = asyncio.create_task(heartbeat_loop())
    
    async def _stop_heartbeat(self) -> None:
        """Stop the heartbeat task."""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None
    
    async def _subscribe_to_events(self) -> None:
        """Subscribe to event topics."""
        if not self._event_handlers:
            logger.info("No event handlers registered")
            return
        
        # Extract unique topics from handler keys (format: "topic:event_type")
        topics = set()
        for handler_key in self._event_handlers.keys():
            if ":" in handler_key:
                topic, _ = handler_key.split(":", 1)
                topics.add(topic)  # Already string from handler_key
        
        if not topics:
            logger.info("No topics to subscribe to")
            return
        
        topics_list = list(topics)
        logger.info(f"Subscribing to topics: {topics_list}")
        await self.context.bus.subscribe(topics_list)
    
    def _derive_topics(self, event_types: List[str]) -> List[str]:
        """Derive topic patterns from event types."""
        topics = set()
        for event_type in event_types:
            # Support wildcards in event types
            if "*" in event_type:
                topics.add(event_type)
            elif event_type.endswith(".requested") or event_type.endswith(".request"):
                topics.add("action-requests")
            elif event_type.endswith(".completed") or event_type.endswith(".result"):
                topics.add("action-results")
            elif event_type.startswith("billing."):
                topics.add("billing")
            elif event_type.startswith("notification."):
                topics.add("notifications")
            else:
                topics.add("business-facts")
        return list(topics)
    
    async def start(self) -> None:
        """
        Start the agent.
        
        This method:
        1. Initializes the platform context
        2. Registers with the Registry
        3. Calls startup handlers
        4. Subscribes to events
        5. Starts the heartbeat
        
        For blocking execution, use agent.run() instead.
        """
        if self._running:
            logger.warning("Agent already running")
            return
        
        logger.info(f"🚀 Starting {self.name} v{self.version}")
        
        # Initialize platform context
        await self._initialize_context()
        
        # Register with Registry
        await self._register_with_registry()
        
        # Call startup handlers
        for handler in self._startup_handlers:
            await handler()
        
        # Subscribe to events
        await self._subscribe_to_events()
        
        # Start heartbeat
        await self._start_heartbeat()
        
        self._running = True
        logger.info(f"✓ {self.name} is running")
    
    async def stop(self) -> None:
        """
        Stop the agent gracefully.
        
        This method:
        1. Stops the heartbeat
        2. Calls shutdown handlers
        3. Deregisters from Registry
        4. Closes platform connections
        """
        if not self._running:
            return
        
        logger.info(f"🛑 Stopping {self.name}")
        self._running = False
        
        # Stop heartbeat
        await self._stop_heartbeat()
        
        # Call shutdown handlers
        for handler in self._shutdown_handlers:
            try:
                await handler()
            except Exception as e:
                logger.error(f"Shutdown handler error: {e}")
        
        # Deregister
        await self._deregister_from_registry()
        
        # Close context
        if self._context:
            await self._context.close()
            self._context = None
        
        logger.info(f"👋 {self.name} stopped")
    
    def run(self) -> None:
        """
        Start the agent and run until interrupted.
        
        This is the main entry point for running an agent.
        It handles signal handlers for graceful shutdown.
        
        Usage:
            if __name__ == "__main__":
                agent.run()
        """
        async def _run():
            # Setup signal handlers
            loop = asyncio.get_event_loop()
            stop_event = asyncio.Event()
            
            def signal_handler():
                stop_event.set()
            
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, signal_handler)
            
            try:
                await self.start()
                await stop_event.wait()
            finally:
                await self.stop()
        
        try:
            asyncio.run(_run())
        except KeyboardInterrupt:
            pass
