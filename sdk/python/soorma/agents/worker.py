"""
Worker Agent - Domain-specific cognitive node.

Workers are specialized agents that handle domain-specific cognitive tasks.
They:
- Subscribe to action-requests for event types they handle
- Execute tasks using domain knowledge (often with LLMs)
- Report progress and results
- Emit action-results explicitly via task.complete()

Workers are discoverable via the Registry service based on their capabilities.

Usage:
    from soorma.agents import Worker

    worker = Worker(
        name="research-worker",
        description="Searches and analyzes research papers",
        capabilities=["paper_search", "citation_analysis"],
    )

    @worker.on_task("search.requested")
    async def search_papers(task, context):
        # Access shared memory
        preferences = await context.memory.retrieve(f"user:{task.session_id}:preferences")
        
        # Use LLM for intelligent search
        results = await search_with_llm(task.data["query"], preferences)
        
        # Store results in memory for other workers
        await context.memory.store(f"search_results:{task.task_id}", results)
        
        await task.complete({"papers": results, "count": len(results)})

    worker.run()
"""
import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional
from uuid import uuid4

from soorma_common.events import EventEnvelope, EventTopic

from .base import Agent
from ..context import PlatformContext
from ..task_context import TaskContext, ResultContext

logger = logging.getLogger(__name__)


# Type aliases for handlers
TaskHandler = Callable[[TaskContext, PlatformContext], Awaitable[Any]]
ResultHandler = Callable[[ResultContext, PlatformContext], Awaitable[Any]]


class Worker(Agent):
    """
    Domain-specific cognitive node that executes tasks.
    
    Workers are the "hands" of the DisCo architecture. They:
    1. Register capabilities with the Registry
    2. Subscribe to action-requests for event types they handle
    3. Execute tasks with domain expertise (often using LLMs)
    4. Report progress to the Tracker
    5. Emit action-results explicitly via task.complete()
    
    Workers are designed to be:
    - Specialized: Each worker handles specific domain tasks
    - Discoverable: Found via Registry by capability
    - Stateless: All state is stored in Memory service
    - Observable: Progress tracked automatically
    
    Attributes:
        All Agent attributes, plus:
        on_task: Decorator for registering task handlers
    
    Usage:
        worker = Worker(
            name="summarizer",
            description="Summarizes documents",
            capabilities=["text_summarization", "key_extraction"],
        )
        
        @worker.on_task("summarize.requested")
        async def summarize(task: TaskContext, context: PlatformContext) -> None:
            # Report progress
            await task.report_progress(0.1, "Loading document")
            
            doc = await context.memory.retrieve(f"doc:{task.data['doc_id']}")
            
            await task.report_progress(0.5, "Summarizing")
            summary = await llm_summarize(doc)
            
            await task.complete({"summary": summary, "length": len(summary)})
        
        worker.run()
    """
    
    def __init__(
        self,
        name: str,
        description: str = "",
        version: str = "0.1.0",
        capabilities: Optional[List[Any]] = None,
        events_consumed: Optional[List[str]] = None,
        events_produced: Optional[List[str]] = None,
        **kwargs,
    ):
        """
        Initialize the Worker.
        
        Args:
            name: Worker name
            description: What this worker does
            version: Version string
            capabilities: Task capabilities offered (strings or AgentCapability objects)
            events_consumed: List of event types this worker consumes
            events_produced: List of event types this worker produces
            **kwargs: Additional Agent arguments
        """
        # Events consumed/produced are event types (not topics)
        # Do not add topic names here
        events_consumed = list(events_consumed or [])
        events_produced = list(events_produced or [])
        
        super().__init__(
            name=name,
            description=description,
            version=version,
            agent_type="worker",
            capabilities=capabilities or [],
            events_consumed=events_consumed,
            events_produced=events_produced,
            **kwargs,
        )
        
        # Task handlers: event_type -> handler
        self._task_handlers: Dict[str, TaskHandler] = {}

        # Result handlers: event_type -> handler
        self._result_handlers: Dict[str, ResultHandler] = {}

    def on_task(self, event_type: str) -> Callable[[TaskHandler], TaskHandler]:
        """
        Decorator to register a task handler.
        
        Task handlers receive a TaskContext and PlatformContext,
        and manage completion asynchronously.
        
        Usage:
            @worker.on_task("data.process.requested")
            async def process(task: TaskContext, context: PlatformContext) -> None:
                await task.save()
                await task.delegate(...)
        
        Args:
            event_type: The event type to handle
        
        Returns:
            Decorator function
        """
        def decorator(func: TaskHandler) -> TaskHandler:
            self._task_handlers[event_type] = func

            @self.on_event(event_type, topic=EventTopic.ACTION_REQUESTS)
            async def wrapper(event: EventEnvelope, context: PlatformContext) -> None:
                data = event.data or {}
                assigned_to = data.get("assigned_to")
                if assigned_to and not self._should_handle_task(assigned_to):
                    return
                task = TaskContext.from_event(
                    event,
                    context,
                    agent_id=self.agent_id,
                    register_produced_event=self._register_produced_event,
                )
                await func(task, context)

            # Add to capabilities if not already there
            if event_type not in self.config.capabilities:
                self.config.capabilities.append(event_type)

            logger.debug(f"Registered task handler: {event_type}")
            return func
        return decorator

    def on_result(self, event_type: str) -> Callable[[ResultHandler], ResultHandler]:
        """
        Decorator to register a sub-task result handler.

        Result handlers receive a ResultContext and PlatformContext,
        and should restore task state before deciding to complete.

        Args:
            event_type: The event type to handle

        Returns:
            Decorator function
        """
        def decorator(func: ResultHandler) -> ResultHandler:
            self._result_handlers[event_type] = func

            @self.on_event(event_type, topic=EventTopic.ACTION_RESULTS)
            async def wrapper(event: EventEnvelope, context: PlatformContext) -> None:
                result = ResultContext.from_event(
                    event,
                    context,
                    register_produced_event=self._register_produced_event,
                )
                await func(result, context)

            logger.debug(f"Registered result handler: {event_type}")
            return func
        return decorator

    def _register_produced_event(self, event_type: str) -> None:
        if event_type not in self.config.events_produced:
            self.config.events_produced.append(event_type)
    
    def _should_handle_task(self, assigned_to: str) -> bool:
        """Check if this worker should handle a task based on assigned_to."""
        if not assigned_to:
            return False
        
        # Match by name
        if assigned_to == self.name:
            return True
        
        # Match by agent_id
        if assigned_to == self.agent_id:
            return True
        
        # Match by capability
        if assigned_to in self.config.capabilities:
            return True
        
        return False
    
    async def execute_task(
        self,
        task_name: str,
        data: Dict[str, Any],
        plan_id: Optional[str] = None,
        goal_id: Optional[str] = None,
    ) -> Any:
        """
        Programmatically execute a task.
        
        This method allows executing tasks without going through the event bus,
        useful for testing or direct integration.
        
        Args:
            task_name: Name of the task to execute
            data: Task input data
            plan_id: Optional plan ID
            goal_id: Optional goal ID
        
        Returns:
            Task result dictionary
        
        Raises:
            ValueError: If no handler for task_name
        """
        handler = self._task_handlers.get(task_name)
        if not handler:
            raise ValueError(f"No handler for task: {task_name}")

        task = TaskContext(
            task_id=str(uuid4()),
            event_type=task_name,
            plan_id=plan_id,
            data=data,
            response_event=None,
            response_topic="action-results",
            agent_id=self.agent_id,
            task_name=task_name,
            _context=self.context,
            _register_produced_event=self._register_produced_event,
        )

        return await handler(task, self.context)
