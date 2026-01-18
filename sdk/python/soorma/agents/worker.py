"""
Worker Agent - Domain-specific cognitive node.

Workers are specialized agents that handle domain-specific cognitive tasks.
They:
- Subscribe to action-requests for their capabilities
- Execute tasks using domain knowledge (often with LLMs)
- Report progress and results
- Emit action-results when complete

Workers are discoverable via the Registry service based on their capabilities.

Usage:
    from soorma.agents import Worker

    worker = Worker(
        name="research-worker",
        description="Searches and analyzes research papers",
        capabilities=["paper_search", "citation_analysis"],
    )

    @worker.on_task("search_papers")
    async def search_papers(task, context):
        # Access shared memory
        preferences = await context.memory.retrieve(f"user:{task.session_id}:preferences")
        
        # Use LLM for intelligent search
        results = await search_with_llm(task.data["query"], preferences)
        
        # Store results in memory for other workers
        await context.memory.store(f"search_results:{task.task_id}", results)
        
        return {"papers": results, "count": len(results)}

    worker.run()
"""
import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional
from uuid import uuid4

from .base import Agent
from ..context import PlatformContext

logger = logging.getLogger(__name__)


@dataclass
class TaskContext:
    """
    Context for a task being executed by a Worker.
    
    Provides all the information needed to execute a task,
    plus methods for reporting progress.
    
    Attributes:
        task_id: Unique task identifier
        task_name: Name of the task
        plan_id: Parent plan ID
        goal_id: Original goal ID
        data: Task input data
        correlation_id: Tracking ID
        session_id: Client session
        tenant_id: Multi-tenant isolation
        timeout: Task timeout in seconds
        priority: Task priority
    """
    task_id: str
    task_name: str
    plan_id: str
    goal_id: str
    data: Dict[str, Any]
    correlation_id: Optional[str] = None
    session_id: Optional[str] = None
    tenant_id: Optional[str] = None
    timeout: Optional[float] = None
    priority: int = 0
    
    # Internal reference to platform context
    _platform_context: Optional[PlatformContext] = field(default=None, repr=False)
    
    async def report_progress(
        self,
        progress: float,
        message: Optional[str] = None,
    ) -> None:
        """
        Report task progress.
        
        Args:
            progress: Progress percentage (0.0 to 1.0)
            message: Optional status message
        """
        if self._platform_context:
            await self._platform_context.tracker.emit_progress(
                plan_id=self.plan_id,
                task_id=self.task_id,
                status="running",
                progress=progress,
                message=message,
            )


# Type alias for task handlers
TaskHandler = Callable[[TaskContext, PlatformContext], Awaitable[Dict[str, Any]]]


class Worker(Agent):
    """
    Domain-specific cognitive node that executes tasks.
    
    Workers are the "hands" of the DisCo architecture. They:
    1. Register capabilities with the Registry
    2. Subscribe to action-requests matching their capabilities
    3. Execute tasks with domain expertise (often using LLMs)
    4. Report progress to the Tracker
    5. Emit action-results when complete
    
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
        
        @worker.on_task("summarize_document")
        async def summarize(task: TaskContext, context: PlatformContext) -> Dict:
            # Report progress
            await task.report_progress(0.1, "Loading document")
            
            doc = await context.memory.retrieve(f"doc:{task.data['doc_id']}")
            
            await task.report_progress(0.5, "Summarizing")
            summary = await llm_summarize(doc)
            
            return {"summary": summary, "length": len(summary)}
        
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
        # Workers consume action-requests and produce action-results by default
        events_consumed = list(events_consumed or [])
        if "action.request" not in events_consumed:
            events_consumed.append("action.request")
        
        events_produced = list(events_produced or [])
        if "action.result" not in events_produced:
            events_produced.append("action.result")
        
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
        
        # Task handlers: task_name -> handler
        self._task_handlers: Dict[str, TaskHandler] = {}
        
        # Also register the main action.request handler
        self._register_action_request_handler()
    
    def _register_action_request_handler(self) -> None:
        """Register the main action.request event handler."""
        @self.on_event("action.request", topic="action-requests")
        async def handle_action_request(event: Dict[str, Any], context: PlatformContext) -> None:
            await self._handle_action_request(event, context)
    
    def on_task(self, task_name: str) -> Callable[[TaskHandler], TaskHandler]:
        """
        Decorator to register a task handler.
        
        Task handlers receive a TaskContext and PlatformContext,
        and return a result dictionary.
        
        Usage:
            @worker.on_task("process_data")
            async def process(task: TaskContext, context: PlatformContext) -> Dict:
                result = await do_processing(task.data)
                return {"processed": True, "output": result}
        
        Args:
            task_name: The task name to handle
        
        Returns:
            Decorator function
        """
        def decorator(func: TaskHandler) -> TaskHandler:
            self._task_handlers[task_name] = func
            
            # Add to capabilities if not already there
            if task_name not in self.config.capabilities:
                self.config.capabilities.append(task_name)
            
            logger.debug(f"Registered task handler: {task_name}")
            return func
        return decorator
    
    async def _handle_action_request(
        self,
        event: Dict[str, Any],
        context: PlatformContext,
    ) -> None:
        """Handle an incoming action.request event."""
        data = event.get("data", {})
        
        task_name = data.get("task_name")
        assigned_to = data.get("assigned_to")
        
        # Check if this task is assigned to us
        if not self._should_handle_task(assigned_to):
            return
        
        handler = self._task_handlers.get(task_name)
        if not handler:
            logger.debug(f"No handler for task: {task_name}")
            return
        
        # Create TaskContext
        task = TaskContext(
            task_id=data.get("task_id", str(uuid4())),
            task_name=task_name,
            plan_id=data.get("plan_id", ""),
            goal_id=data.get("goal_id", ""),
            data=data.get("data", {}),
            correlation_id=event.get("correlation_id"),
            session_id=event.get("session_id"),
            tenant_id=event.get("tenant_id"),
            timeout=data.get("timeout"),
            priority=data.get("priority", 0),
            _platform_context=context,
        )
        
        # Report task started
        await context.tracker.emit_progress(
            plan_id=task.plan_id,
            task_id=task.task_id,
            status="running",
            progress=0.0,
        )
        
        try:
            # Execute task
            logger.info(f"Executing task: {task_name} ({task.task_id})")
            result = await handler(task, context)
            
            # Report completion
            await context.tracker.complete_task(
                plan_id=task.plan_id,
                task_id=task.task_id,
                result=result,
            )
            
            # Emit action.result
            await context.bus.publish(
                event_type="action.result",
                data={
                    "task_id": task.task_id,
                    "task_name": task_name,
                    "plan_id": task.plan_id,
                    "goal_id": task.goal_id,
                    "status": "completed",
                    "result": result,
                },
                topic="action-results",
                correlation_id=task.correlation_id,
            )
            
            logger.info(f"Completed task: {task_name} ({task.task_id})")
            
        except Exception as e:
            logger.error(f"Task failed: {task_name} - {e}")
            
            # Report failure
            await context.tracker.fail_task(
                plan_id=task.plan_id,
                task_id=task.task_id,
                error=str(e),
            )
            
            # Emit failure result
            await context.bus.publish(
                event_type="action.result",
                data={
                    "task_id": task.task_id,
                    "task_name": task_name,
                    "plan_id": task.plan_id,
                    "goal_id": task.goal_id,
                    "status": "failed",
                    "error": str(e),
                },
                topic="action-results",
                correlation_id=task.correlation_id,
            )
    
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
    ) -> Dict[str, Any]:
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
            task_name=task_name,
            plan_id=plan_id or "",
            goal_id=goal_id or "",
            data=data,
            _platform_context=self.context,
        )
        
        return await handler(task, self.context)
