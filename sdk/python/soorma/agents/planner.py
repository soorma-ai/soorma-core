"""
Planner Agent - Strategic reasoning engine.

The Planner is the "brain" of the DisCo architecture. It:
- Receives high-level goals from clients
- Decomposes goals into actionable tasks
- Assigns tasks to Worker agents
- Monitors plan execution progress

Usage:
    from soorma.agents import Planner

    planner = Planner(
        name="research-planner",
        description="Plans research tasks",
        capabilities=["research_planning", "task_decomposition"],
    )

    @planner.on_goal("research.goal")
    async def plan_research(goal, context):
        # Define state machine
        state_machine = {
            "start": StateConfig(
                state_name="start",
                default_next="search",
            ),
            "search": StateConfig(
                state_name="search",
                action=StateAction(
                    event_type="search.requested",
                    response_event="search.completed",
                    data={"query": "{{goal_data.topic}}"},
                ),
                transitions=[
                    StateTransition(on_event="search.completed", to_state="done")
                ],
            ),
            "done": StateConfig(
                state_name="done",
                is_terminal=True,
            ),
        }

        # Create and persist the plan
        plan = await PlanContext.create_from_goal(
            goal=goal,
            context=context,
            state_machine=state_machine,
            current_state="start",
            status="pending",
        )
        await plan.execute_next()

    planner.run()
"""
import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional
from uuid import uuid4

from soorma_common.events import EventEnvelope, EventTopic

from .base import Agent
from ..context import PlatformContext
from ..plan_context import PlanContext

logger = logging.getLogger(__name__)


@dataclass
class GoalContext:
    """
    Wrapper for goal events passed to on_goal handlers.
    
    Provides structured access to goal data and request metadata.
    
    Attributes:
        event_type: Goal event type (e.g., "research.goal")
        data: Goal parameters
        correlation_id: Correlation ID for tracking
        response_event: Event type for final result (from original request)
        session_id: Optional session identifier
        user_id: User authentication context
        tenant_id: Tenant isolation context
        _raw_event: Original EventEnvelope
        _context: PlatformContext for service access
    """
    event_type: str
    data: Dict[str, Any]
    correlation_id: str
    response_event: str
    session_id: Optional[str]
    user_id: str
    tenant_id: str
    _raw_event: EventEnvelope
    _context: PlatformContext
    
    @classmethod
    def from_event(cls, event: EventEnvelope, context: PlatformContext) -> 'GoalContext':
        """
        Create GoalContext from event envelope.
        
        Args:
            event: EventEnvelope containing goal
            context: PlatformContext for service access
            
        Returns:
            GoalContext instance
        """
        return cls(
            event_type=event.type,  # EventEnvelope uses 'type' not 'event_type'
            data=event.data or {},
            correlation_id=event.correlation_id or "",
            response_event=event.response_event or "",  # Direct field, not metadata
            session_id=event.session_id,
            user_id=event.user_id or "",
            tenant_id=event.tenant_id or "",
            _raw_event=event,
            _context=context,
        )



@dataclass
class Task:
    """
    A single task in a plan.
    
    Tasks are atomic units of work assigned to Worker agents.
    
    Attributes:
        name: Task identifier (e.g., "search_papers")
        assigned_to: Capability or agent name to execute this task
        data: Task input data
        depends_on: List of task names this depends on
        timeout: Timeout in seconds (None = no timeout)
        priority: Task priority (higher = more urgent)
    """
    name: str
    assigned_to: str
    data: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    timeout: Optional[float] = None
    priority: int = 0
    
    # Runtime fields (set by Planner)
    task_id: str = field(default_factory=lambda: str(uuid4()))
    status: str = "pending"  # pending, running, completed, failed
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class Goal:
    """
    A goal submitted by a client.
    
    Goals are high-level objectives that the Planner decomposes into tasks.
    
    Attributes:
        goal_type: Type of goal (e.g., "research.goal")
        data: Goal parameters
        correlation_id: Tracking ID
        session_id: Client session
        tenant_id: Multi-tenant isolation
    """
    goal_type: str
    data: Dict[str, Any]
    goal_id: str = field(default_factory=lambda: str(uuid4()))
    correlation_id: Optional[str] = None
    session_id: Optional[str] = None
    tenant_id: Optional[str] = None


@dataclass
class Plan:
    """
    A plan to achieve a goal.
    
    Plans contain ordered lists of tasks with dependencies.
    The Planner creates plans, and the platform tracks their execution.
    
    Attributes:
        goal: The goal this plan achieves
        tasks: Ordered list of tasks
        plan_id: Unique plan identifier
        metadata: Additional plan metadata
    """
    goal: Goal
    tasks: List[Task]
    plan_id: str = field(default_factory=lambda: str(uuid4()))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Runtime state
    status: str = "pending"  # pending, running, completed, failed, paused


# Type aliases for handlers
GoalHandler = Callable[[Goal, PlatformContext], Awaitable[Plan]]
TransitionHandler = Callable[
    [EventEnvelope, PlatformContext, PlanContext, str],
    Awaitable[None],
]


class Planner(Agent):
    """
    Strategic reasoning engine that breaks goals into tasks.
    
    The Planner is responsible for:
    1. Receiving high-level goals from clients
    2. Understanding available Worker capabilities (via Registry)
    3. Decomposing goals into executable tasks
    4. Creating execution plans with dependencies
    5. Publishing tasks as action-requests
    6. Monitoring plan progress (via Tracker)
    
    Planners typically use LLMs for reasoning about goal decomposition.
    
    Attributes:
        All Agent attributes, plus:
        on_goal: Decorator for registering goal handlers
    
    Usage:
        planner = Planner(
            name="fleet-planner",
            description="Plans fleet maintenance workflows",
        )
        
        @planner.on_goal("maintenance.goal")
        async def plan_maintenance(goal: Goal, context: PlatformContext) -> Plan:
            # Query available workers (placeholder - needs proper capability search endpoint)
            # mechanics = await context.registry.query_agents(...)
            
            # Create plan
            return Plan(
                goal=goal,
                tasks=[
                    Task(name="diagnose", assigned_to="diagnostic-worker", data=goal.data),
                    Task(name="repair", assigned_to="repair-worker", depends_on=["diagnose"]),
                    Task(name="verify", assigned_to="qa-worker", depends_on=["repair"]),
                ],
            )
        
        planner.run()
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
        Initialize the Planner.
        
        Args:
            name: Planner name
            description: What this planner does
            version: Version string
            capabilities: Planning capabilities offered (strings or AgentCapability objects)
            **kwargs: Additional Agent arguments
        """
        # Events produced are event types (not topics)
        # Do not add topic names here
        events_produced = kwargs.pop("events_produced", [])
        
        super().__init__(
            name=name,
            description=description,
            version=version,
            agent_type="planner",
            capabilities=capabilities or ["planning"],
            events_produced=events_produced,
            **kwargs,
        )
        
        # Goal handlers: goal_type -> handler
        self._goal_handlers: Dict[str, GoalHandler] = {}
        
        # Transition handler (optional)
        self._transition_handler: Optional[TransitionHandler] = None
    
    def on_goal(self, goal_type: str) -> Callable:
        """
        Decorator to register a goal handler.
        
        Goal handlers receive a GoalContext and PlatformContext.
        Use PlanContext for state machine-based orchestration.
        
        Usage:
            @planner.on_goal("research.goal")
            async def plan_research(goal: GoalContext, context: PlatformContext):
                # Create state machine
                state_machine = {...}
                plan = PlanContext(...)
                await plan.save()
                await plan.execute_next()
        
        Args:
            goal_type: The goal type to handle (e.g., "research.goal")
        
        Returns:
            Decorator function
        """
        def decorator(func: Callable) -> Callable:
            self._goal_handlers[goal_type] = func
            
            # RF-SDK-023: Register event as consumed (not topics)
            if goal_type not in self.config.events_consumed:
                self.config.events_consumed.append(goal_type)
            
            # Register underlying event handler
            @self.on_event(goal_type, topic=EventTopic.ACTION_REQUESTS)
            async def wrapper(event: EventEnvelope, context: PlatformContext) -> None:
                # Convert event to GoalContext
                goal = GoalContext.from_event(event, context)
                await func(goal, context)
            
            logger.debug(f"Registered goal handler: {goal_type}")
            return func
        return decorator
    
    def on_transition(self) -> Callable:
        """
        Register handler for ALL state transitions.
        
        This handler is called for action-results events that match a known
        plan transition (based on the plan's current state machine).
        
        RF-SDK-023: This uses wildcard subscriptions but does NOT add topics
        to events_consumed (topics are not event types).
        
        Usage:
            @planner.on_transition()
            async def handle_transition(event, context, plan, next_state):
                # plan and next_state are provided when available
                plan.current_state = next_state
                await plan.execute_next(trigger_event=event)
        
        Returns:
            Decorator function
        """
        def decorator(func: TransitionHandler) -> TransitionHandler:
            self._transition_handler = func
            
            # Subscribe to ALL events on action-results only.
            # NOTE: We don't add these topics to events_consumed (RF-SDK-023)
            # because topics are not event types.
            @self.on_event("*", topic=EventTopic.ACTION_RESULTS)
            async def wrapper(event: EventEnvelope, context: PlatformContext) -> None:
                # Require tenant/user context to restore plans.
                if not event.tenant_id or not event.user_id:
                    logger.warning(
                        "Skipping transition event without tenant_id/user_id"
                    )
                    return

                plan = await PlanContext.restore_by_correlation(
                    correlation_id=event.correlation_id,
                    context=context,
                    tenant_id=event.tenant_id,
                    user_id=event.user_id,
                )
                if not plan:
                    return

                next_state = plan.get_next_state(event)
                if not next_state:
                    return

                await func(event, context, plan, next_state)
            
            # RF-SDK-023: Remove wildcard from events_consumed
            # Wildcard subscriptions are implementation details, not consumed events
            if "*" in self.config.events_consumed:
                self.config.events_consumed.remove("*")
            
            logger.debug("Registered transition handler for all events")
            return func
        return decorator
    
    async def _handle_goal_event(
        self,
        goal_type: str,
        event: EventEnvelope,
        context: PlatformContext,
    ) -> None:
        """Handle an incoming goal event."""
        handler = self._goal_handlers.get(goal_type)
        if not handler:
            logger.warning(f"No handler for goal type: {goal_type}")
            return
        
        # Create Goal from event
        goal = Goal(
            goal_type=goal_type,
            data=event.data or {},
            goal_id=event.id,
            correlation_id=event.correlation_id,
            session_id=event.session_id,
            tenant_id=event.tenant_id,
        )
        
        try:
            # Generate plan
            plan = await handler(goal, context)
            
            # Track plan in Tracker service
            await context.tracker.start_plan(
                plan_id=plan.plan_id,
                agent_id=self.agent_id,
                goal=goal_type,
                tasks=[
                    {
                        "task_id": t.task_id,
                        "name": t.name,
                        "assigned_to": t.assigned_to,
                        "depends_on": t.depends_on,
                    }
                    for t in plan.tasks
                ],
                metadata={
                    "goal_id": goal.goal_id,
                    "correlation_id": goal.correlation_id,
                    **plan.metadata,
                },
            )
            
            # Publish tasks as action-requests
            await self._publish_tasks(plan, context)
            
            logger.info(f"Created plan {plan.plan_id} with {len(plan.tasks)} tasks")
            
        except Exception as e:
            logger.error(f"Goal handling failed: {e}")
            # Emit failure event
            await context.bus.publish(
                event_type=f"{goal_type}.failed",
                data={
                    "goal_id": goal.goal_id,
                    "error": str(e),
                },
                correlation_id=goal.correlation_id,
            )
    
    async def _publish_tasks(self, plan: Plan, context: PlatformContext) -> None:
        """Publish tasks as action-request events."""
        for task in plan.tasks:
            # Only publish tasks with no unmet dependencies
            if not task.depends_on:
                await self._publish_task(plan, task, context)
    
    async def _publish_task(
        self,
        plan: Plan,
        task: Task,
        context: PlatformContext,
    ) -> None:
        """Publish a single task as an action-request."""
        await context.bus.publish(
            event_type="action.request",
            data={
                "task_id": task.task_id,
                "task_name": task.name,
                "assigned_to": task.assigned_to,
                "plan_id": plan.plan_id,
                "goal_id": plan.goal.goal_id,
                "data": task.data,
                "timeout": task.timeout,
                "priority": task.priority,
            },
            topic="action-requests",
            correlation_id=plan.goal.correlation_id,
        )
        logger.debug(f"Published task: {task.name} ({task.task_id})")
    
    async def create_plan(
        self,
        goal_type: str,
        goal_data: Dict[str, Any],
        correlation_id: Optional[str] = None,
    ) -> Plan:
        """
        Programmatically create and execute a plan.
        
        This method allows creating plans without going through the event bus,
        useful for integrating with existing systems.
        
        Args:
            goal_type: Type of goal
            goal_data: Goal parameters
            correlation_id: Optional correlation ID
        
        Returns:
            The created Plan
        
        Raises:
            ValueError: If no handler for goal_type
        """
        handler = self._goal_handlers.get(goal_type)
        if not handler:
            raise ValueError(f"No handler for goal type: {goal_type}")
        
        goal = Goal(
            goal_type=goal_type,
            data=goal_data,
            correlation_id=correlation_id or str(uuid4()),
        )
        
        plan = await handler(goal, self.context)
        
        # Track and publish
        await self.context.tracker.start_plan(
            plan_id=plan.plan_id,
            agent_id=self.agent_id,
            goal=goal_type,
            tasks=[
                {
                    "task_id": t.task_id,
                    "name": t.name,
                    "assigned_to": t.assigned_to,
                    "depends_on": t.depends_on,
                }
                for t in plan.tasks
            ],
        )
        
        await self._publish_tasks(plan, self.context)
        
        return plan
