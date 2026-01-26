"""
Tool Service - Atomic, stateless capability.

Tools are specialized micro-services that perform atomic, stateless operations.
They:
- Expose specific capabilities (e.g., calculator, API search, file parser)
- Handle synchronous request/response operations
- Are stateless - no memory of previous calls
- Often wrap external APIs or perform deterministic computations

Unlike Workers (which are cognitive), Tools are rules-based and deterministic.

Usage:
    from soorma.agents import Tool

    tool = Tool(
        name="calculator-tool",
        description="Performs mathematical calculations",
        capabilities=["arithmetic", "unit_conversion"],
    )

    @tool.on_invoke("calculate")
    async def calculate(request, context):
        expression = request.data["expression"]
        result = eval(expression)  # (use safe_eval in production!)
        return {"result": result, "expression": expression}

    @tool.on_invoke("convert_units")
    async def convert_units(request, context):
        value = request.data["value"]
        from_unit = request.data["from"]
        to_unit = request.data["to"]
        converted = perform_conversion(value, from_unit, to_unit)
        return {"result": converted, "from": from_unit, "to": to_unit}

    tool.run()
"""
import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional
from uuid import uuid4

from soorma_common.events import EventEnvelope, EventTopic

from .base import Agent
from ..context import PlatformContext

logger = logging.getLogger(__name__)


@dataclass
class ToolRequest:
    """
    A request to invoke a tool operation.
    
    Attributes:
        operation: The operation to perform
        data: Input parameters
        request_id: Unique request identifier
        correlation_id: Tracking ID
        timeout: Request timeout in seconds
    """
    operation: str
    data: Dict[str, Any]
    request_id: str = field(default_factory=lambda: str(uuid4()))
    correlation_id: Optional[str] = None
    session_id: Optional[str] = None
    tenant_id: Optional[str] = None
    timeout: Optional[float] = None


@dataclass
class ToolResponse:
    """
    Response from a tool invocation.
    
    Attributes:
        request_id: Original request ID
        success: Whether the operation succeeded
        data: Result data (if successful)
        error: Error message (if failed)
    """
    request_id: str
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# Type alias for tool handlers
ToolHandler = Callable[[ToolRequest, PlatformContext], Awaitable[Dict[str, Any]]]


class Tool(Agent):
    """
    Atomic, stateless capability micro-service.
    
    Tools are the "utilities" of the DisCo architecture. They:
    1. Expose deterministic, stateless operations
    2. Handle both event-driven and synchronous requests
    3. Wrap external APIs or perform computations
    4. Are highly reusable across different workflows
    
    Key differences from Workers:
    - Tools are stateless (no memory between calls)
    - Tools are deterministic (same input = same output)
    - Tools are typically rules-based, not cognitive
    - Tools can also expose REST endpoints for sync calls
    
    Attributes:
        All Agent attributes, plus:
        on_invoke: Decorator for registering operation handlers
    
    Usage:
        tool = Tool(
            name="weather-api",
            description="Fetches weather data",
            capabilities=["current_weather", "forecast"],
        )
        
        @tool.on_invoke("get_weather")
        async def get_weather(request: ToolRequest, context: PlatformContext) -> Dict:
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
        **kwargs,
    ):
        """
        Initialize the Tool.
        
        Args:
            name: Tool name
            description: What this tool does
            version: Version string
            capabilities: Operations this tool provides (strings or AgentCapability objects)
            **kwargs: Additional Agent arguments
        """
        # Tools consume tool.request and produce tool.response
        events_consumed = kwargs.pop("events_consumed", [])
        if "tool.request" not in events_consumed:
            events_consumed.append("tool.request")
        
        events_produced = kwargs.pop("events_produced", [])
        if "tool.response" not in events_produced:
            events_produced.append("tool.response")
        
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
        
        # Operation handlers: operation_name -> handler
        self._operation_handlers: Dict[str, ToolHandler] = {}
        
        # Register the main tool.request handler
        self._register_tool_request_handler()
    
    def _register_tool_request_handler(self) -> None:
        """Register the main tool.request event handler."""
        @self.on_event("tool.request", topic=EventTopic.ACTION_REQUESTS)
        async def handle_tool_request(event: EventEnvelope, context: PlatformContext) -> None:
            await self._handle_tool_request(event, context)
    
    def on_invoke(self, operation: str) -> Callable[[ToolHandler], ToolHandler]:
        """
        Decorator to register an operation handler.
        
        Operation handlers receive a ToolRequest and PlatformContext,
        and return a result dictionary.
        
        Usage:
            @tool.on_invoke("calculate")
            async def calculate(request: ToolRequest, context: PlatformContext) -> Dict:
                result = compute(request.data["expression"])
                return {"result": result}
        
        Args:
            operation: The operation name to handle
        
        Returns:
            Decorator function
        """
        def decorator(func: ToolHandler) -> ToolHandler:
            self._operation_handlers[operation] = func
            
            # Add to capabilities if not already there
            exists = False
            for cap in self.config.capabilities:
                if isinstance(cap, str) and cap == operation:
                    exists = True
                    break
                elif hasattr(cap, "name") and cap.name == operation:
                    exists = True
                    break
                elif isinstance(cap, dict) and cap.get("taskName") == operation:
                    exists = True
                    break
            
            if not exists:
                self.config.capabilities.append(operation)
            
            logger.debug(f"Registered operation handler: {operation}")
            return func
        return decorator
    
    async def _handle_tool_request(
        self,
        event: EventEnvelope,
        context: PlatformContext,
    ) -> None:
        """Handle an incoming tool.request event."""
        data = event.data or {}
        
        operation = data.get("operation")
        target_tool = data.get("tool")
        
        # Check if this request is for us
        if not self._should_handle_request(target_tool):
            return
        
        handler = self._operation_handlers.get(operation)
        if not handler:
            logger.debug(f"No handler for operation: {operation}")
            # Emit error response
            await self._emit_error_response(
                request_id=data.get("request_id", str(uuid4())),
                error=f"Unknown operation: {operation}",
                correlation_id=event.correlation_id,
                context=context,
            )
            return
        
        # Create ToolRequest
        request = ToolRequest(
            operation=operation,
            data=data.get("data", {}),
            request_id=data.get("request_id", str(uuid4())),
            correlation_id=event.get("correlation_id"),
            session_id=event.get("session_id"),
            tenant_id=event.get("tenant_id"),
            timeout=data.get("timeout"),
        )
        
        try:
            # Execute operation
            logger.info(f"Executing operation: {operation} ({request.request_id})")
            result = await handler(request, context)
            
            # Emit tool.response
            await context.bus.publish(
                event_type="tool.response",
                data={
                    "request_id": request.request_id,
                    "operation": operation,
                    "success": True,
                    "result": result,
                },
                topic="action-results",  # Tools use action-results topic
                correlation_id=request.correlation_id,
            )
            
            logger.info(f"Completed operation: {operation} ({request.request_id})")
            
        except Exception as e:
            logger.error(f"Operation failed: {operation} - {e}")
            await self._emit_error_response(
                request_id=request.request_id,
                error=str(e),
                correlation_id=request.correlation_id,
                context=context,
            )
    
    async def _emit_error_response(
        self,
        request_id: str,
        error: str,
        correlation_id: Optional[str],
        context: PlatformContext,
    ) -> None:
        """Emit an error response."""
        await context.bus.publish(
            event_type="tool.response",
            data={
                "request_id": request_id,
                "success": False,
                "error": error,
            },
            topic="action-results",
            correlation_id=correlation_id,
        )
    
    def _should_handle_request(self, target_tool: Optional[str]) -> bool:
        """Check if this tool should handle a request."""
        if not target_tool:
            return False
        
        # Match by name
        if target_tool == self.name:
            return True
        
        # Match by agent_id
        if target_tool == self.agent_id:
            return True
        
        # Match by capability (tool name might be a capability)
        if target_tool in self.config.capabilities:
            return True
        
        return False
    
    async def invoke(
        self,
        operation: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Programmatically invoke a tool operation.
        
        This method allows invoking operations without going through the event bus,
        useful for testing or direct integration.
        
        Args:
            operation: Name of the operation
            data: Input parameters
        
        Returns:
            Operation result dictionary
        
        Raises:
            ValueError: If no handler for operation
        """
        handler = self._operation_handlers.get(operation)
        if not handler:
            raise ValueError(f"No handler for operation: {operation}")
        
        request = ToolRequest(
            operation=operation,
            data=data,
        )
        
        return await handler(request, self.context)
    
    async def invoke_remote(
        self,
        tool_name: str,
        operation: str,
        data: Dict[str, Any],
        timeout: float = 30.0,
    ) -> Optional[Dict[str, Any]]:
        """
        Invoke an operation on a remote tool.
        
        This sends a tool.request event and waits for tool.response.
        
        Args:
            tool_name: Name of the target tool
            operation: Operation to invoke
            data: Input parameters
            timeout: Timeout in seconds
        
        Returns:
            Result dictionary if successful, None on timeout
        """
        return await self.context.bus.request(
            event_type="tool.request",
            data={
                "tool": tool_name,
                "operation": operation,
                "data": data,
            },
            timeout=timeout,
        )
