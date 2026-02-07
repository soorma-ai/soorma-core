"""
Tool Service - Atomic, stateless capability (Stage 3 Refactored).

Tools are specialized micro-services that perform atomic, stateless operations.
They:
- Expose specific capabilities (e.g., calculator, API search, file parser)
- Handle synchronous request/response operations (via on_invoke decorator)
- Are stateless - no memory of previous calls
- Often wrap external APIs or perform deterministic computations

Key differences from Workers:
- Stateless (no TaskContext or state persistence)
- Synchronous handlers (return result directly)
- Auto-publish to caller-specified response_event
- Support multiple event types via multiple @on_invoke() decorators

Design (RF-SDK-005):
- Uses action-requests and action-results topics (standard)
- InvocationContext provides lightweight request context
- response_event specified by caller (in request data)
- Return type validated against optional schema
- Correlation IDs preserved for tracing

Usage:
    from soorma.agents import Tool

    tool = Tool(
        name="calculator-tool",
        description="Performs mathematical calculations",
        capabilities=["arithmetic"],
    )

    @tool.on_invoke("calculate")
    async def calculate(request: InvocationContext, context: PlatformContext):
        expression = request.data["expression"]
        result = eval(expression)  # Use safe_eval in production!
        return {"result": result, "expression": expression}

    @tool.on_invoke("convert_units")
    async def convert_units(request: InvocationContext, context: PlatformContext):
        value = request.data["value"]
        from_unit = request.data["from"]
        to_unit = request.data["to"]
        converted = perform_conversion(value, from_unit, to_unit)
        return {"result": converted, "from": from_unit, "to": to_unit}

    tool.run()
"""
import logging
import json
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional
from uuid import uuid4

from soorma_common.events import EventEnvelope, EventTopic

from .base import Agent
from ..context import PlatformContext

logger = logging.getLogger(__name__)


@dataclass
class InvocationContext:
    """
    Lightweight context for tool invocations (RF-SDK-005).
    
    Provided to all tool handlers via @on_invoke() decorator.
    Contains the request data, event context, and response routing info.
    
    Attributes:
        request_id: Unique request identifier (auto-generated if not provided)
        event_type: The event type being handled (e.g., "calculate.requested")
        correlation_id: Tracking ID for distributed tracing
        data: Request payload/parameters
        response_event: Caller-specified response event name (optional, tool can provide default)
        response_topic: Topic for response (usually "action-results")
        tenant_id: Multi-tenancy identifier
        user_id: User/caller identifier
    """
    request_id: str
    event_type: str
    correlation_id: Optional[str]
    data: Dict[str, Any]
    response_event: Optional[str]
    response_topic: str
    tenant_id: str
    user_id: str
    
    @classmethod
    def from_event(cls, event: EventEnvelope, context: PlatformContext) -> "InvocationContext":
        """
        Create InvocationContext from EventEnvelope and PlatformContext.
        
        Extracts request metadata from event data, using defaults where needed.
        
        Args:
            event: The incoming event (from action-requests topic)
            context: Platform context (reserved for future use)
            
        Returns:
            InvocationContext for use by handler
        """
        data = event.data or {}

        return cls(
            request_id=data.get("request_id", str(uuid4())),
            event_type=event.type,  # Use event.type, not event.event_type
            correlation_id=event.correlation_id or data.get("correlation_id"),
            data=data,
            response_event=event.response_event,
            response_topic=event.response_topic or "action-results",
            tenant_id=event.tenant_id,
            user_id=event.user_id,
        )


# Type alias for tool handlers
# Handlers receive InvocationContext and PlatformContext, return result dict
ToolHandler = Callable[[InvocationContext, PlatformContext], Awaitable[Dict[str, Any]]]


class Tool(Agent):
    """
    Atomic, stateless capability micro-service (RF-SDK-005 refactored).
    
    Tools are the "utilities" of the DisCo architecture that execute synchronously:
    1. Receive invocation on action-requests topic with event_type
    2. Handler executes synchronously, returns result dict
    3. Decorator auto-publishes to caller's response_event on action-results topic
    4. No state persistence, no delegation, no async completion
    
    Features:
    - Multiple @on_invoke() handlers for different event types (Q3)
    - response_event optional (caller provides, tool has default) (Q2)
    - Return type validation against optional schema (Q6)
    - Registry includes all supported event types (Q4)
    - Correlation IDs preserved for tracing
    - Proper error handling with error response publishing
    
    Attributes:
        _operation_handlers: Dict mapping event_type → handler function
        _response_schemas: Dict mapping event_type → response schema (for validation)
        default_response_event: Tool's default response event if caller doesn't provide
    
    Usage:
        tool = Tool(
            name="weather-api",
            description="Fetches weather data",
            capabilities=["current_weather", "forecast"],
            default_response_event="weather.response",
        )
        
        @tool.on_invoke("get_weather")
        async def get_weather(request: InvocationContext, context: PlatformContext) -> Dict:
            location = request.data["location"]
            weather = await fetch_weather_api(location)
            return {"temperature": weather.temp, "conditions": weather.conditions}
        
        tool.run()
    """
    
    def __init__(
        self,
        name: str,
        description: str = "",
        version: str = "0.1.0",
        capabilities: Optional[List[Any]] = None,
        default_response_event: Optional[str] = None,
        **kwargs,
    ):
        """
        Initialize the Tool.
        
        Args:
            name: Tool name
            description: What this tool does
            version: Version string
            capabilities: Operations this tool provides (strings or AgentCapability objects)
            default_response_event: Default response event if caller doesn't specify
            **kwargs: Additional Agent arguments
        """
        # Events consumed/produced are populated dynamically via @on_invoke() decorators
        # Topics (action-requests/action-results) are specified in the decorator, not here
        events_consumed = kwargs.pop("events_consumed", [])
        events_produced = kwargs.pop("events_produced", [])
        
        # Add default response event to produced events if specified
        if default_response_event and default_response_event not in events_produced:
            events_produced.append(default_response_event)
        
        super().__init__(
            name=name,
            description=description,
            version=version,
            agent_type="tool",
            capabilities=capabilities or [],
            events_consumed=events_consumed,
            events_produced=events_produced,
            **kwargs,
        )
        
        # Event handlers: event_type -> handler function
        self._operation_handlers: Dict[str, ToolHandler] = {}
        
        # Response schemas for validation: event_type -> schema dict
        self._response_schemas: Dict[str, Dict[str, Any]] = {}
        
        # Default response event if not provided by caller
        self.default_response_event = default_response_event
    
    def on_invoke(
        self,
        event_type: str,
        response_schema: Optional[Dict[str, Any]] = None,
    ) -> Callable[[ToolHandler], ToolHandler]:
        """
        Decorator to register a handler for a specific event type (RF-SDK-005).
        
        Supports multiple @on_invoke() decorators for different event types (Q3).
        Requires event_type parameter (Q5).
        Optional response_schema for return type validation (Q6).
        
        Handler signature:
            async def handler(request: InvocationContext, context: PlatformContext) -> Dict:
                return {"result": ...}
        
        Decorator:
            - Registers handler for event_type
            - Auto-publishes result to caller's response_event
            - Validates return type if schema provided
            - Publishes error if exception occurs
            - Preserves correlation_id in response
        
        Args:
            event_type: Event type to handle (e.g., "calculate.requested")
                       Required parameter (Q5)
            response_schema: Optional JSON schema for validating return value (Q6)
                            If provided, handler result must match schema
        
        Returns:
            Decorator function that registers the handler
            
        Raises:
            TypeError: If event_type not provided
        """
        def decorator(func: ToolHandler) -> ToolHandler:
            # Register handler
            self._operation_handlers[event_type] = func
            
            # Store schema if provided (for validation)
            if response_schema:
                self._response_schemas[event_type] = response_schema
            
            # Add to capabilities if not already there
            self._add_capability(event_type)
            
            # Add event_type to events_consumed (actual event names, not topics)
            if event_type not in self.config.events_consumed:
                self.config.events_consumed.append(event_type)
            
            logger.debug(f"Tool '{self.name}' registered handler for event: {event_type}")
            
            # Subscribe to this event on action-requests topic
            @self.on_event(event_type, topic=EventTopic.ACTION_REQUESTS)
            async def event_handler(event: EventEnvelope, context: PlatformContext) -> None:
                await self._handle_invocation(event, context, event_type)
            
            return func
        
        return decorator
    
    def _add_capability(self, event_type: str) -> None:
        """Add event_type to capabilities if not already present."""
        exists = False
        for cap in self.config.capabilities:
            if isinstance(cap, str) and cap == event_type:
                exists = True
                break
            elif hasattr(cap, "name") and cap.name == event_type:
                exists = True
                break
            elif isinstance(cap, dict) and cap.get("taskName") == event_type:
                exists = True
                break
        
        if not exists:
            self.config.capabilities.append(event_type)
    
    async def _handle_invocation(
        self,
        event: EventEnvelope,
        context: PlatformContext,
        event_type: str,
    ) -> None:
        """
        Handle an incoming invocation on action-requests.
        
        Creates InvocationContext from event, calls handler, publishes response.
        
        Args:
            event: The incoming event
            context: Platform context
            event_type: The event type being handled
        """
        try:
            # Create InvocationContext from event (Q1: same class as Tool)
            invocation = InvocationContext.from_event(event, context)
            
            # Get handler for this event type
            handler = self._operation_handlers.get(event_type)
            if not handler:
                logger.warning(f"No handler for event type: {event_type}")
                return
            
            # Execute handler (synchronous logic)
            logger.info(
                f"Tool '{self.name}' executing {event_type} "
                f"(request_id={invocation.request_id})"
            )
            
            result = await handler(invocation, context)
            
            # Validate return type if schema provided (Q6)
            if event_type in self._response_schemas:
                self._validate_response(result, self._response_schemas[event_type])
            
            # Determine response event (Q2: optional, use default if not provided)
            response_event = (
                invocation.response_event or 
                self.default_response_event or 
                f"{event_type}.completed"
            )
            
            # Track response event in events_produced (if not already tracked)
            if response_event not in self.config.events_produced:
                self.config.events_produced.append(response_event)
            
            # Publish success response to caller's response_event
            await context.bus.respond(
                event_type=response_event,
                data={
                    "request_id": invocation.request_id,
                    "success": True,
                    "result": result,
                },
                correlation_id=invocation.correlation_id,
                topic=invocation.response_topic,
                tenant_id=invocation.tenant_id,
                user_id=invocation.user_id,
            )
            
            logger.info(
                f"Tool '{self.name}' completed {event_type} "
                f"(request_id={invocation.request_id})"
            )
            
        except Exception as e:
            logger.error(
                f"Tool '{self.name}' failed on {event_type}: {e}",
                exc_info=True,
            )
            
            # Publish error response
            invocation = InvocationContext.from_event(event, context)
            response_event = (
                invocation.response_event or 
                self.default_response_event or 
                f"{event_type}.completed"
            )
            
            await context.bus.respond(
                event_type=response_event,
                data={
                    "request_id": invocation.request_id,
                    "success": False,
                    "error": str(e),
                },
                correlation_id=invocation.correlation_id,
                topic=invocation.response_topic,
                tenant_id=invocation.tenant_id,
                user_id=invocation.user_id,
            )
    
    def _validate_response(self, result: Dict[str, Any], schema: Dict[str, Any]) -> None:
        """
        Validate response against schema (Q6).
        
        Args:
            result: The handler's return value
            schema: JSON schema for validation
            
        Raises:
            ValueError: If response doesn't match schema
        """
        try:
            # Import jsonschema for validation
            import jsonschema
            
            jsonschema.validate(instance=result, schema=schema)
            logger.debug(f"Response validation passed for schema: {schema}")
            
        except ImportError:
            logger.warning(
                "jsonschema not installed - skipping response validation. "
                "Install with: pip install jsonschema"
            )
        except Exception as e:
            raise ValueError(f"Response validation failed: {e}")
    
    async def invoke(
        self,
        event_type: str,
        data: Dict[str, Any],
        response_event: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Programmatically invoke a tool operation (direct, no event bus).
        
        Useful for testing or direct integration without event routing.
        
        Args:
            event_type: Event type to handle
            data: Request payload
            response_event: Optional response event name
        
        Returns:
            Handler result dictionary
        
        Raises:
            ValueError: If no handler for event_type
        """
        handler = self._operation_handlers.get(event_type)
        if not handler:
            raise ValueError(f"No handler for event_type: {event_type}")
        
        invocation = InvocationContext(
            request_id=str(uuid4()),
            event_type=event_type,
            correlation_id=None,
            data=data,
            response_event=response_event,
            response_topic="action-results",
            tenant_id=self.config.registry_url.split("://")[1].split(":")[0],  # Dummy
            user_id="system",  # System user for direct invocation
        )
        
        return await handler(invocation, self.context)

