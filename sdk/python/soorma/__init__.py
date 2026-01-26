"""
Soorma Core - The Open Source Foundation for AI Agents.

The DisCo (Distributed Cognition) SDK for building production-grade AI agents.

Core Concepts:
- Agent: Base class for all autonomous agents
- Planner: Strategic reasoning engine that breaks goals into tasks
- Worker: Domain-specific cognitive node that executes tasks
- Tool: Atomic, stateless capability micro-service

Platform Context (available in all handlers):
- context.registry: Service discovery & capabilities
- context.memory: Distributed state management
- context.bus: Event choreography (pub/sub)
- context.tracker: Observability & state machines

Usage:
    from soorma import Worker, PlatformContext

    worker = Worker(
        name="research-worker",
        description="Searches and analyzes research papers",
        capabilities=["paper_search", "citation_analysis"],
    )

    @worker.on_task("search_papers")
    async def search_papers(task, context: PlatformContext):
        # Access shared memory
        prefs = await context.memory.retrieve(f"user:{task.session_id}:preferences")
        
        # Perform the task
        results = await search_papers(task.data["query"], prefs)
        
        # Store results for other workers
        await context.memory.store(f"results:{task.task_id}", results)
        
        return {"papers": results}

    worker.run()
"""

__version__ = "0.7.3"

# Core imports
from soorma_common.events import EventTopic, EventEnvelope
from .events import EventClient
from .context import (
    PlatformContext,
    RegistryClient,
    MemoryClient,
    BusClient,
    TrackerClient,
)
from .agents import Agent, Planner, Worker, Tool
from .agents.planner import Goal, Plan, Task
from .agents.worker import TaskContext
from .agents.tool import ToolRequest, ToolResponse
from .workflow import WorkflowState

# Public API
__all__ = [
    # Version
    "__version__",
    # Core classes
    "Agent",
    "Planner",
    "Worker", 
    "Tool",
    # Context
    "PlatformContext",
    "RegistryClient",
    "MemoryClient",
    "BusClient",
    "TrackerClient",
    # Events
    "EventClient",
    "EventTopic",
    "EventEnvelope",
    # Data classes
    "Goal",
    "Plan",
    "Task",
    "TaskContext",
    "ToolRequest",
    "ToolResponse",
    # Helpers
    "WorkflowState",
    # Functions
    "hello",
    "event_handler",
]


def hello():
    """
    Welcome to Soorma.
    
    Displays version info and links to documentation.
    """
    print(f"Soorma Core v{__version__}")
    print("=" * 50)
    print("The DisCo (Distributed Cognition) SDK")
    print("")
    print("Domain Services (The Trinity):")
    print("  • Planner: Strategic reasoning engine")
    print("  • Worker:  Domain-specific cognitive node")
    print("  • Tool:    Atomic, stateless capability")
    print("")
    print("Platform Context:")
    print("  • context.registry - Service discovery")
    print("  • context.memory   - Distributed state")
    print("  • context.bus      - Event choreography")
    print("  • context.tracker  - Observability")
    print("")
    print("Quick Start:")
    print("  soorma init my-agent    # Create new agent")
    print("  soorma dev              # Start local stack")
    print("  soorma deploy           # Deploy to cloud")
    print("")
    print("Docs: https://soorma.ai")


def event_handler(event_type: str):
    """
    Decorator to register an event handler.
    
    This is a legacy/convenience decorator. For new code, use:
    - @agent.on_event("event.type") for generic agents
    - @planner.on_goal("goal.type") for planners
    - @worker.on_task("task_name") for workers
    - @tool.on_invoke("operation") for tools
    
    Usage:
        @event_handler("example.request")
        async def handle_example(event, context):
            ...
    """
    from typing import Callable
    
    def decorator(func: Callable) -> Callable:
        func._soorma_event_type = event_type
        return func
    return decorator