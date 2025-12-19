"""
Soorma Core - The Open Source Foundation for AI Agents.
"""

__version__ = "0.1.0"

from typing import Callable, List, Optional, Any


def hello():
    """
    Welcome to Soorma.
    To get started, please visit https://soorma.ai to join the waitlist.
    """
    print(f"Soorma Core v{__version__} (Preview)")
    print("--------------------------------------------------")
    print("The DisCo (Distributed Cognition) engine is currently in closed alpha.")
    print("We are building the reference implementation for:")
    print(" - Planner: Strategic reasoning engine")
    print(" - Worker:  Domain-specific cognitive node")
    print(" - Tool:    Atomic capabilities")
    print("--------------------------------------------------")
    print("Docs: https://soorma.ai")


def event_handler(event_type: str):
    """
    Decorator to register an event handler.
    
    Usage:
        @event_handler("example.request")
        async def handle_example(event):
            ...
    """
    def decorator(func: Callable):
        func._soorma_event_type = event_type
        return func
    return decorator


class Agent:
    """
    Base class for Soorma AI Agents.
    
    An Agent is a autonomous unit that:
    - Registers with the Soorma Registry
    - Subscribes to events
    - Processes events and emits new ones
    
    Usage:
        agent = Agent(name="my-agent", description="My first agent")
        
        @agent.on_startup
        async def startup():
            print("Agent starting...")
        
        @event_handler("example.request")
        async def handle_request(event):
            await agent.emit("example.response", {"result": "ok"})
        
        agent.run()
    """
    
    def __init__(
        self,
        name: str,
        description: str = "",
        version: str = "0.1.0",
        capabilities: Optional[List[str]] = None,
    ):
        self.name = name
        self.description = description
        self.version = version
        self.capabilities = capabilities or []
        self._startup_handler: Optional[Callable] = None
        self._shutdown_handler: Optional[Callable] = None
        self._event_handlers: dict = {}
    
    def on_startup(self, func: Callable) -> Callable:
        """Decorator to register a startup handler."""
        self._startup_handler = func
        return func
    
    def on_shutdown(self, func: Callable) -> Callable:
        """Decorator to register a shutdown handler."""
        self._shutdown_handler = func
        return func
    
    async def emit(self, event_type: str, payload: Any) -> None:
        """
        Emit an event to the event bus.
        
        Args:
            event_type: The type/topic of the event (e.g., "order.created")
            payload: The event payload (will be JSON serialized)
        """
        # TODO: Implement actual event emission via NATS
        print(f"[{self.name}] Emitting event: {event_type}")
        print(f"  Payload: {payload}")
    
    def run(self) -> None:
        """
        Start the agent.
        
        This will:
        1. Register with the Soorma Registry
        2. Subscribe to configured events
        3. Start the event loop
        """
        import asyncio
        
        async def _run():
            print(f"🚀 Starting agent: {self.name} v{self.version}")
            print(f"   Description: {self.description}")
            print("")
            
            # Run startup handler
            if self._startup_handler:
                await self._startup_handler()
            
            # TODO: Implement actual agent lifecycle
            print("⚠️  Agent runtime is in preview mode.")
            print("   The agent will not connect to Registry or NATS.")
            print("   Visit https://soorma.ai for updates.")
            
            # Keep running until interrupted
            try:
                while True:
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                pass
            finally:
                if self._shutdown_handler:
                    await self._shutdown_handler()
        
        try:
            asyncio.run(_run())
        except KeyboardInterrupt:
            print(f"\n👋 Agent {self.name} stopped.")


# Expose the "Trinity" placeholders so IDEs see them
class Planner:
    def __init__(self, name: str):
        print(f"Initializing Planner: {name} (Simulation Mode)")

class Worker:
    def __init__(self, name: str, capabilities: list):
        print(f"Initializing Worker: {name} with {capabilities} (Simulation Mode)")

class Tool:
    def __init__(self):
        pass