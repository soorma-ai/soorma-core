# Agent Patterns: Technical Architecture

**Status:** ✅ Stage 4 Complete (Planner & ChoreographyPlanner)  
**Last Updated:** February 23, 2026  
**Related Stages:** Stage 3 (RF-SDK-004, RF-SDK-005, RF-SDK-022), Stage 4 (RF-SDK-006, RF-SDK-015, RF-SDK-016)

---

## Design Principles

### DisCo (Distributed Cognition) Pattern

Soorma is built on the **Distributed Cognition (DisCo)** pattern. You MUST respect the "Trinity" of entities:

- **Planner:** Strategic reasoning (Task breakdown & orchestration)
- **Worker:** Domain-specific cognition (Event-reactive logic)
- **Tool:** Atomic, stateless capabilities

**Key Insight:** Intelligence is distributed across specialized components that communicate through events, rather than concentrated in a single monolithic agent.

### Progressive Complexity

Agent models follow a progression from simple to complex:

```
Agent (Base) → Tool (Sync) → Worker (Async) → Planner (Orchestration)
```

Each level adds capabilities:
- **Agent:** Event subscription and publishing
- **Tool:** Synchronous request/response with auto-completion
- **Worker:** Asynchronous task handling with state persistence and delegation
- **Planner:** Goal decomposition and state machine orchestration

### Event-Driven Choreography

Agents communicate exclusively through events:
- No direct method calls between agents
- Loose coupling through event topics
- Async by default (no blocking)
- Correlation tracking for multi-step workflows

---

## Agent Base Class

### Registration Lifecycle

```python
class Agent:
    def __init__(
        self,
        name: str,
        capabilities: List[str],
        events_consumed: List[str] = None,
        events_produced: List[str] = None,
    ):
        self.name = name
        self.capabilities = capabilities
        self.events_consumed = events_consumed or []
        self.events_produced = events_produced or []
        self._event_handlers = {}
    
    def on_event(self, topic: str, event_type: str):
        """Register event handler with explicit topic."""
        def decorator(func):
            handler_key = (topic, event_type)
            self._event_handlers[handler_key] = func
            return func
        return decorator
    
    async def run(self):
        """Start agent and register with platform."""
        # 1. Connect to Event Service
        # 2. Register with Registry Service
        # 3. Subscribe to topics
        # 4. Start event loop
```

### Event Subscription Model

Agents subscribe to topics and filter by event_type:

```python
# Subscribe to topic
await context.bus.subscribe(
    topics=["action-requests"],
)

# Handler filters by event_type
@agent.on_event(topic="action-requests", event_type="calculate.requested")
async def handle(event, context):
    # Only receives events matching this event_type
    pass
```

### Context Injection

All handlers receive `PlatformContext`:

```python
class PlatformContext:
    bus: BusClient           # Event publishing/subscribing
    memory: MemoryClient     # Memory operations
    registry: RegistryClient # Service discovery
    tenant_id: str           # Multi-tenant context
    user_id: str             # User/agent identity
    agent_id: str            # Current agent ID
```

---

## Tool Model (RF-SDK-005)

**Status:** ✅ Complete (Stage 3 Phase 1, January 2026)

### Design Goals

- Simplest agent type: synchronous request/response
- Stateless operations
- Handler returns result directly
- SDK auto-publishes response to caller's `response_event`

### InvocationContext

```python
@dataclass
class InvocationContext:
    """Lightweight context for tool invocations."""
    request_id: str
    event_type: str
    correlation_id: str
    data: Dict[str, Any]
    response_event: str    # Caller-specified
    response_topic: str    # Usually "action-results"
    
    # Auth context
    tenant_id: str
    user_id: str
    
    @classmethod
    def from_event(cls, event: EventEnvelope, context: PlatformContext):
        return cls(
            request_id=event.data.get("request_id", str(uuid4())),
            event_type=event.event_type,
            correlation_id=event.correlation_id,
            data=event.data,
            response_event=event.data.get("response_event"),
            response_topic=event.data.get("response_topic", "action-results"),
            tenant_id=context.tenant_id,
            user_id=context.user_id,
        )
```

### on_invoke() Decorator

```python
class Tool(Agent):
    def on_invoke(self, event_type: str):
        """
        Register handler for tool invocations.
        
        Handler model:
        - Receives InvocationContext
        - Returns result dict
        - Decorator auto-publishes to response_event
        """
        def decorator(func):
            @self.on_event(topic="action-requests", event_type=event_type)
            async def wrapper(event, context):
                request = InvocationContext.from_event(event, context)
                
                try:
                    result = await func(request, context)
                    
                    # Auto-publish result
                    await context.bus.respond(
                        event_type=request.response_event,
                        data={
                            "request_id": request.request_id,
                            "success": True,
                            "result": result,
                        },
                        correlation_id=request.correlation_id,
                        topic=request.response_topic,
                    )
                except Exception as e:
                    # Auto-publish error
                    await context.bus.respond(
                        event_type=request.response_event,
                        data={
                            "request_id": request.request_id,
                            "success": False,
                            "error": str(e),
                        },
                        correlation_id=request.correlation_id,
                        topic=request.response_topic,
                    )
            return func
        return decorator
```

### Usage Example

```python
tool = Tool(name="calculator", capabilities=["math"])

@tool.on_invoke(event_type="calculate.requested")
async def calculate(request: InvocationContext, context: PlatformContext):
    """Handler returns result directly - decorator publishes."""
    expr = request.data["expression"]
    result = eval(expr)  # In real code, use safe evaluation
    return {"result": result}  # Auto-published to response_event
```

### Schema Ownership Pattern

| Element | Owner | Notes |
|---------|-------|-------|
| Request event name | Caller | Caller chooses event name |
| Response event name | Caller | Via `response_event` field |
| Request payload schema | Tool | Defined at registration |
| Response payload schema | Tool | Defined at registration |

**Key Insight:** Caller chooses event names, Tool defines payload schemas.

---

## Worker Model (RF-SDK-004, RF-SDK-022)

**Status:** ✅ Complete (Stage 3 Phase 2, February 2026 - 90% done, test expansion planned)

### Design Goals

- Asynchronous task handling with delegation
- State persistence across event boundaries
- Sequential and parallel sub-task delegation
- Manual completion (not auto-published)
- Handler-only event registration (RF-SDK-022)

### TaskContext Model

**File:** `sdk/python/soorma/task_context.py` (863 lines)

```python
@dataclass
class TaskContext:
    """Persistent state for async task execution."""
    task_id: str
    event_type: str
    plan_id: str
    data: Dict[str, Any]
    response_event: str
    response_topic: str
    sub_tasks: Dict[str, SubTaskInfo]  # Track delegations
    state: Dict[str, Any]              # Task-specific state
    
    # Auth context
    tenant_id: str
    user_id: str
    agent_id: str
    
    async def save(self):
        """Persist to Memory Service for async resume."""
        await self._context.memory.save_task_context(
            task_id=self.task_id,
            plan_id=self.plan_id,
            context=self.to_dict(),
        )
    
    @classmethod
    async def restore(cls, sub_task_id: str, context: PlatformContext):
        """Restore parent task by sub-task correlation ID."""
        task_data = await context.memory.get_task_by_subtask(sub_task_id)
        return cls.from_dict(task_data, context)
    
    async def delegate(
        self,
        event_type: str,
        data: Dict[str, Any],
        response_event: str,
        assigned_to: str = None,
    ) -> str:
        """
        Sequential delegation to sub-agent.
        
        Returns sub_task_id for tracking.
        """
        sub_task_id = str(uuid4())
        self.sub_tasks[sub_task_id] = SubTaskInfo(
            sub_task_id=sub_task_id,
            event_type=event_type,
            response_event=response_event,
            status="pending",
        )
        await self.save()  # CRITICAL: Save before publish
        
        await self._context.bus.request(
            event_type=event_type,
            data=data,
            response_event=response_event,
            correlation_id=sub_task_id,
            assigned_to=assigned_to,  # Optional routing
        )
        return sub_task_id
    
    async def delegate_parallel(
        self,
        sub_tasks: List[DelegationSpec],
    ) -> str:
        """
        Parallel delegation (fan-out).
        
        Returns parallel_group_id for aggregation.
        """
        parallel_group_id = str(uuid4())
        
        # Track all sub-tasks
        for spec in sub_tasks:
            sub_task_id = str(uuid4())
            self.sub_tasks[sub_task_id] = SubTaskInfo(
                sub_task_id=sub_task_id,
                event_type=spec.event_type,
                response_event=spec.response_event,
                status="pending",
                parallel_group_id=parallel_group_id,
            )
        
        await self.save()  # Save all before publishing
        
        # Publish all in parallel
        for sub_task_id, info in self.sub_tasks.items():
            if info.parallel_group_id == parallel_group_id:
                spec = next(s for s in sub_tasks if s.event_type == info.event_type)
                await self._context.bus.request(
                    event_type=info.event_type,
                    data=spec.data,
                    response_event=info.response_event,
                    correlation_id=sub_task_id,
                )
        
        return parallel_group_id
    
    async def aggregate_parallel_results(self, parallel_group_id: str) -> Optional[Dict]:
        """Check if all parallel tasks completed (fan-in)."""
        group_tasks = [
            info for info in self.sub_tasks.values()
            if info.parallel_group_id == parallel_group_id
        ]
        
        if all(t.status == "completed" for t in group_tasks):
            return {t.sub_task_id: t.result for t in group_tasks}
        return None
    
    async def complete(self, result: Dict[str, Any]):
        """Explicitly complete task and publish result."""
        await self._context.bus.respond(
            event_type=self.response_event,
            data={
                "task_id": self.task_id,
                "status": "completed",
                "result": result,
            },
            correlation_id=self.task_id,
            topic=self.response_topic,
        )
        # Cleanup
        await self._context.memory.delete_task_context(self.task_id)
```

### Worker Class with Decorators

**File:** `sdk/python/soorma/agents/worker.py` (281 lines)

```python
class Worker(Agent):
    def on_task(self, event_type: str):
        """
        Register async task handler.
        
        Handler receives TaskContext, not raw event.
        Handler does NOT return result (manual completion).
        """
        def decorator(func):
            @self.on_event(topic="action-requests", event_type=event_type)
            async def wrapper(event, context):
                # Create TaskContext from event
                task = TaskContext.from_event(event, context)
                
                # Call handler (no result expected)
                await func(task, context)
                
                # Handler must call task.save(), task.delegate(), or task.complete()
            
            # Register event for discovery
            if event_type not in self.events_consumed:
                self.events_consumed.append(event_type)
            
            return func
        return decorator
    
    def on_result(self, event_type: str):
        """
        Register result handler for delegated sub-tasks.
        
        Handler receives ResultContext with restore_task() method.
        """
        def decorator(func):
            @self.on_event(topic="action-results", event_type=event_type)
            async def wrapper(event, context):
                # Create ResultContext
                result = ResultContext.from_event(event, context)
                
                # Call handler
                await func(result, context)
            
            # Register event for discovery
            if event_type not in self.events_consumed:
                self.events_consumed.append(event_type)
            
            return func
        return decorator
    
    async def execute_task(
        self,
        task_name: str,
        data: Dict[str, Any],
        plan_id: str,
        goal_id: str,
    ) -> str:
        """Programmatic task execution (for testing/direct calls)."""
        task_id = str(uuid4())
        
        # Create event
        event = EventEnvelope(
            id=str(uuid4()),
            event_type=task_name,
            data=data,
            correlation_id=task_id,
            # ... other fields
        )
        
        # Invoke handler directly
        await self._handle_event(event)
        
        return task_id
```

### ResultContext

```python
@dataclass
class ResultContext:
    """Context for result events from delegated sub-tasks."""
    sub_task_id: str
    event_type: str
    data: Dict[str, Any]
    success: bool
    
    async def restore_task(self) -> TaskContext:
        """Restore parent task by sub-task correlation ID."""
        return await TaskContext.restore(
            sub_task_id=self.sub_task_id,
            context=self._context,
        )
```

### Usage Example: Sequential Delegation

```python
worker = Worker(name="order-processor", capabilities=["orders"])

@worker.on_task(event_type="order.process.requested")
async def handle_order(task: TaskContext, context: PlatformContext):
    # Save state for async resume
    await task.save()
    
    # Delegate to inventory service
    await task.delegate(
        event_type="inventory.reserve.requested",
        data={"order_id": task.data["order_id"]},
        response_event="inventory.reserved"
    )
    # Handler returns - completion happens in on_result

@worker.on_result(event_type="inventory.reserved")
async def handle_inventory_result(result: ResultContext, context: PlatformContext):
    # Restore original task
    task = await result.restore_task()
    
    if result.success:
        # Complete successfully
        await task.complete({"status": "processed"})
    else:
        # Handle error
        await task.complete({"status": "failed", "error": result.data["error"]})
```

### Usage Example: Parallel Delegation

```python
from soorma.task_context import DelegationSpec

@worker.on_task(event_type="order.fulfill.requested")
async def handle_fulfill(task: TaskContext, context: PlatformContext):
    await task.save()
    
    # Fan-out: delegate to multiple services in parallel
    group_id = await task.delegate_parallel([
        DelegationSpec(
            event_type="inventory.reserve.requested",
            data={"order_id": task.data["order_id"]},
            response_event="inventory.done"
        ),
        DelegationSpec(
            event_type="payment.process.requested",
            data={"amount": task.data["total"]},
            response_event="payment.done"
        )
    ])
    
    # Store group_id for aggregation
    task.state["parallel_group"] = group_id
    await task.save()

@worker.on_result(event_type="inventory.done")
@worker.on_result(event_type="payment.done")
async def handle_parallel_result(result: ResultContext, context: PlatformContext):
    task = await result.restore_task()
    
    # Update sub-task status
    task.update_sub_task_result(result.sub_task_id, result.data)
    await task.save()
    
    # Fan-in: check if all completed
    group_id = task.state["parallel_group"]
    all_results = await task.aggregate_parallel_results(group_id)
    
    if all_results:
        # All parallel tasks done
        await task.complete({"results": all_results})
```

### Handler-Only Event Registration (RF-SDK-022)

**Problem:** Workers previously tracked events without handlers, causing subscription issues.

**Solution:** Only register events that have actual handlers.

```python
def on_task(self, event_type: str):
    def decorator(func):
        # ... handler wrapper ...
        
        # Only add to events_consumed when handler registered
        if event_type not in self.events_consumed:
            self.events_consumed.append(event_type)
        
        return func
    return decorator
```

**Validation:**
- `events_consumed` contains only task/result event types with handlers
- `events_produced` contains only response event types actually emitted
- Topics never appear in event lists (`action-requests`, `action-results` are topics, not events)

---

## Planner Pattern (RF-SDK-006)

**Status:** ✅ Complete (Stage 4 Phase 1, February 2026)

### Design Goals

- State machine orchestration for multi-step workflows
- Event-driven state transitions
- Plan persistence and restoration across restarts
- Clean handler signatures (SDK auto-restores plans)
- Manual control vs autonomous decision-making

### PlanContext State Machine

**File:** `sdk/python/soorma/plan_context.py`

```python
@dataclass
class PlanContext:
    """State machine for plan execution."""
    plan_id: str
    goal_id: str
    goal_event: str
    goal_data: Dict[str, Any]
    state_machine: Dict[str, StateConfig]
    current_state: str
    status: str  # "pending", "running", "completed", "failed"
    results: Dict[str, Any]  # Store results by event_type
    response_event: Optional[str]
    correlation_id: str
    
    # Auth context
    tenant_id: str
    user_id: str
    
    @classmethod
    async def create_from_goal(
        cls,
        goal: GoalContext,
        context: PlatformContext,
        state_machine: Dict[str, StateConfig],
        current_state: str,
        status: str = "pending",
    ) -> "PlanContext":
        """Create plan from goal event."""
        plan_id = str(uuid4())
        plan = cls(
            plan_id=plan_id,
            goal_id=goal.goal_id,
            goal_event=goal.event_type,
            goal_data=goal.data,
            state_machine=state_machine,
            current_state=current_state,
            status=status,
            results={},
            response_event=goal.response_event,
            correlation_id=goal.correlation_id,
            tenant_id=goal.tenant_id,
            user_id=goal.user_id,
        )
        await plan.save()
        return plan
    
    async def save(self):
        """Persist plan to Memory Service."""
        await self._context.memory.save_plan_context(
            plan_id=self.plan_id,
            goal_id=self.goal_id,
            context=self.to_dict(),
        )
    
    @classmethod
    async def restore(cls, plan_id: str, context: PlatformContext) -> "PlanContext":
        """Restore plan from Memory Service."""
        plan_data = await context.memory.get_plan_context(plan_id)
        return cls.from_dict(plan_data, context)
    
    async def execute_next(self, trigger_event: Optional[EventEnvelope] = None):
        """Execute next state action."""
        state = self.state_machine[self.current_state]
        
        # Auto-transition if default_next specified
        if state.default_next:
            self.current_state = state.default_next
            await self.save()
            # Recursively execute new state
            return await self.execute_next(trigger_event)
        
        # Execute state action (if any)
        if state.action:
            # Interpolate templates in action data
            action_data = self._interpolate_data(state.action.data)
            
            # Publish action event
            await self._context.bus.request(
                event_type=state.action.event_type,
                data=action_data,
                response_event=state.action.response_event,
                correlation_id=self.plan_id,  # Use plan_id for correlation
            )
        
        await self.save()
    
    def is_complete(self) -> bool:
        """Check if current state is terminal."""
        state = self.state_machine.get(self.current_state)
        return state.is_terminal if state else False
    
    async def finalize(self, result: Dict[str, Any]):
        """Complete plan and publish result to goal's response_event."""
        self.status = "completed"
        await self.save()
        
        if self.response_event:
            await self._context.bus.respond(
                event_type=self.response_event,
                data=result,
                correlation_id=self.correlation_id,
            )
    
    def _interpolate_data(self, template_data: Dict) -> Dict:
        """Replace {{goal_data.field}} templates with actual values."""
        # Simple template engine: {{goal_data.topic}} → self.goal_data["topic"]
        import json
        json_str = json.dumps(template_data)
        
        # Replace goal_data references
        for key, value in self.goal_data.items():
            json_str = json_str.replace(f"{{{{goal_data.{key}}}}}", str(value))
        
        return json.loads(json_str)
```

### StateConfig Model

**File:** `libs/soorma-common/src/soorma_common/state.py`

```python
@dataclass
class StateConfig:
    """Configuration for a single state in the state machine."""
    state_name: str
    description: Optional[str] = None
    default_next: Optional[str] = None  # Auto-transition
    action: Optional[StateAction] = None
    transitions: List[StateTransition] = field(default_factory=list)
    is_terminal: bool = False

@dataclass
class StateAction:
    """Action to execute when entering a state."""
    event_type: str
    response_event: str
    data: Dict[str, Any] = field(default_factory=dict)

@dataclass
class StateTransition:
    """Transition from one state to another based on event."""
    on_event: str  # Event type that triggers transition
    to_state: str  # Target state name
    condition: Optional[str] = None  # Future: conditional transitions
```

### Planner Class Decorators

**File:** `sdk/python/soorma/agents/planner.py`

```python
class Planner(Agent):
    def on_goal(self, event_type: str):
        """
        Register goal handler - initial workflow trigger.
        
        Handler receives GoalContext wrapper (not raw event).
        Handler creates PlanContext and executes initial state.
        """
        def decorator(func):
            @self.on_event(topic="action-requests", event_type=event_type)
            async def wrapper(event, context):
                goal = GoalContext.from_event(event)
                await func(goal, context)
            
            if event_type not in self.events_consumed:
                self.events_consumed.append(event_type)
            
            return func
        return decorator
    
    def on_transition(self):
        """
        Register transition handler for all action-results.
        
        SDK behavior:
        - Subscribes to action-results topic
        - Filters by correlation_id == plan_id
        - Auto-restores PlanContext from Memory Service
        - Validates transition exists in state machine
        - Only invokes handler if plan and transition valid
        
        Handler signature:
        - event: EventEnvelope (triggering event)
        - context: PlatformContext
        - plan: PlanContext (auto-restored)
        - next_state: str (target state from state machine)
        """
        def decorator(func):
            @self.on_event(topic="action-results", event_type="*")
            async def wrapper(event, context):
                # SDK auto-restores plan by correlation_id
                try:
                    plan = await PlanContext.restore(event.correlation_id, context)
                except Exception:
                    # Not a plan correlation_id, ignore
                    return
                
                # Find transition for this event
                state = plan.state_machine.get(plan.current_state)
                if not state:
                    return
                
                transition = next(
                    (t for t in state.transitions if t.on_event == event.type),
                    None
                )
                if not transition:
                    return
                
                # Call handler with auto-restored plan
                await func(
                    event=event,
                    context=context,
                    plan=plan,
                    next_state=transition.to_state,
                )
            
            return func
        return decorator
```

### GoalContext Wrapper

```python
@dataclass
class GoalContext:
    """Wrapper for clean goal access in on_goal handlers."""
    event_type: str
    data: Dict[str, Any]
    correlation_id: str
    response_event: str
    response_schema_name: Optional[str]   # Schema the caller expects for the response
    session_id: Optional[str]
    user_id: str
    tenant_id: str
    _raw_event: EventEnvelope
    _context: PlatformContext

    @classmethod
    def from_event(cls, event: EventEnvelope, context: PlatformContext) -> "GoalContext":
        return cls(
            event_type=event.type,
            data=event.data or {},
            correlation_id=event.correlation_id or "",
            response_event=event.response_event or "",
            response_schema_name=event.response_schema_name,
            session_id=event.session_id,
            user_id=event.user_id or "",
            tenant_id=event.tenant_id or "",
            _raw_event=event,
            _context=context,
        )

    async def dispatch(
        self,
        event_type: str,
        data: Dict[str, Any],
        response_event: str,
        response_topic: str = "action-results",
    ) -> str:
        """Dispatch a worker request, auto-propagating tenant/user context.

        Planner-side mirror of TaskContext.delegate().
        Never use context.bus.request() directly in an on_goal handler.
        """
        return await self._context.bus.request(
            event_type=event_type,
            data=data,
            response_event=response_event,
            correlation_id=self.correlation_id,
            response_topic=response_topic,
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            session_id=self.session_id,
        )
```

**`on_goal` hook: auto-save goal metadata**

Before calling your `@on_goal` handler, the SDK automatically stores goal routing
metadata (`response_event`, `response_schema_name`, `tenant_id`, `user_id`) to
working memory under `key=_soorma:goal:{correlation_id}`, `plan_id=correlation_id`.
This lets result handlers call `context.memory.get_goal_metadata()` without any
manual boilerplate in the goal handler.

### Usage Example (09-planner-basic)

```python
from soorma.agents.planner import Planner, GoalContext
from soorma.plan_context import PlanContext
from soorma.context import PlatformContext
from soorma_common.state import StateConfig, StateAction, StateTransition

planner = Planner(
    name="basic-planner",
    capabilities=["planning", "research_orchestration"],
)

@planner.on_goal("research.goal")
async def handle_research_goal(goal: GoalContext, context: PlatformContext):
    """Create state machine and execute."""
    
    # Define state machine
    states = {
        "start": StateConfig(
            state_name="start",
            default_next="research",  # Auto-transition
        ),
        "research": StateConfig(
            state_name="research",
            action=StateAction(
                event_type="research.task",
                response_event="research.complete",
                data={"query": "{{goal_data.topic}}"}  # Template interpolation
            ),
            transitions=[
                StateTransition(on_event="research.complete", to_state="complete")
            ],
        ),
        "complete": StateConfig(
            state_name="complete",
            is_terminal=True,
        )
    }
    
    # Create plan and execute
    plan = await PlanContext.create_from_goal(
        goal=goal,
        context=context,
        state_machine=states,
        current_state="start",
        status="pending",
    )
    await plan.execute_next()

@planner.on_transition()
async def handle_transition(
    event: EventEnvelope,
    context: PlatformContext,
    plan: PlanContext,
    next_state: str,
) -> None:
    """SDK auto-filters and restores plan."""
    
    # Update state
    plan.current_state = next_state
    plan.results[event.type] = event.data
    
    # Execute or finalize
    if plan.is_complete():
        await plan.finalize(result=event.data)
    else:
        await plan.execute_next(event)
```

### Authentication Context Requirement

**Critical:** Workers MUST propagate authentication in responses for plan restoration:

```python
@worker.on_task(event_type="research.task")
async def handle_research(task: TaskContext, context: PlatformContext):
    result = {"findings": "..."}
    
    # MUST include tenant_id/user_id for Planner to restore plan
    await context.bus.respond(
        event_type=task.response_event,
        data=result,
        correlation_id=task.correlation_id,
        tenant_id=task.tenant_id,      # Required
        user_id=task.user_id,          # Required
        session_id=task.session_id,    # Recommended
    )
```

**Why:** PlanContext.restore() requires tenant_id/user_id for RLS policy enforcement in Memory Service.

### Pause/Resume Pattern

Plans can pause and resume across restarts:

```python
# Plan pauses waiting for worker response
await plan.execute_next()  # Publishes action, returns immediately

# Later (different process/restart): Worker responds
# SDK receives response, restores plan, invokes on_transition()
# Plan continues from current state
```

**Use Cases:**
- Long-running workflows (hours/days)
- Human-in-the-loop approvals
- External API callbacks
- Multi-stage pipelines

---

## ChoreographyPlanner Pattern (RF-SDK-015, RF-SDK-016)

**Status:** ✅ Complete (Stage 4 Phase 2, February 2026)

### Design Goals

- Autonomous LLM-based decision making
- Event discovery from Registry at runtime
- Adaptive planning based on intermediate results
- Business rules injection via system instructions
- Circuit breakers for safety (max_actions)

### ChoreographyPlanner Class

**File:** `sdk/python/soorma/ai/choreography.py`

```python
class ChoreographyPlanner(Planner):
    """LLM-driven autonomous orchestration."""
    
    def __init__(
        self,
        name: str,
        reasoning_model: str,  # "gpt-4o", "gpt-4o-mini", "claude-3-5-sonnet"
        system_instructions: str = "",  # Business rules
        max_actions: int = 20,  # Circuit breaker
        capabilities: List[str] = None,
    ):
        super().__init__(name=name, capabilities=capabilities or ["choreography"])
        self.reasoning_model = reasoning_model
        self.system_instructions = system_instructions
        self.max_actions = max_actions
        self._llm_client = None  # Initialized on first use
    
    async def reason_next_action(
        self,
        trigger: str,
        context: PlatformContext,
        plan_id: str,
        custom_context: Optional[Dict] = None,
    ) -> PlannerDecision:
        """
        Use LLM to decide next action.
        
        Args:
            trigger: What prompted this decision (goal, event)
            context: PlatformContext for Registry/Memory access
            plan_id: Current plan ID
            custom_context: Runtime data for LLM reasoning
        
        Returns:
            PlannerDecision with action (PUBLISH/COMPLETE/WAIT/DELEGATE)
        """
        # 1. Discover available events from Registry
        available_events = await context.registry.list_events()
        
        # 2. Get plan history from Memory
        plan_state = await context.memory.get_workflow_state(plan_id)
        
        # 3. Build LLM prompt
        prompt = self._build_prompt(
            trigger=trigger,
            available_events=available_events,
            plan_history=plan_state.get("history", []),
            custom_context=custom_context or {},
        )
        
        # 4. Call LLM
        response = await self._llm_client.call(
            model=self.reasoning_model,
            messages=[
                {"role": "system", "content": self.system_instructions},
                {"role": "user", "content": prompt}
            ],
            response_format=PlannerDecision,  # Structured output
        )
        
        decision = PlannerDecision.model_validate_json(response)
        
        # 5. Validate event exists (prevent hallucinations)
        if decision.next_action.action == PlanAction.PUBLISH:
            if not self._validate_event_exists(
                decision.next_action.event_type,
                available_events
            ):
                raise ValueError(
                    f"LLM hallucinated event: {decision.next_action.event_type}"
                )
        
        # 6. Circuit breaker
        action_count = len(plan_state.get("history", []))
        if action_count >= self.max_actions:
            # Force completion
            decision.next_action = CompleteAction(
                reason="Max actions reached (circuit breaker)",
                result={"status": "max_actions_reached"},
            )
        
        return decision
    
    async def execute_decision(
        self,
        decision: PlannerDecision,
        context: PlatformContext,
        goal_event: EventEnvelope,
        plan: PlanContext,
    ):
        """Execute decision returned by LLM."""
        action = decision.next_action
        
        if action.action == PlanAction.PUBLISH:
            # Publish event to trigger worker
            await context.bus.request(
                event_type=action.event_type,
                data=action.data,
                response_event=action.response_event,
                correlation_id=plan.plan_id,
            )
        
        elif action.action == PlanAction.COMPLETE:
            # Finalize plan
            await plan.finalize(result=action.result)
        
        elif action.action == PlanAction.WAIT:
            # Pause plan (waiting for external event)
            plan.status = "waiting"
            plan.results["waiting_for"] = action.expected_event
            await plan.save()
        
        elif action.action == PlanAction.DELEGATE:
            # Forward to another planner
            await context.bus.publish(
                topic="action-requests",
                event_type=action.target_planner_goal,
                data=action.data,
            )
        
        # Update plan history
        await self._record_action(plan.plan_id, decision, context)
```

### PlannerDecision Model

**File:** `libs/soorma-common/src/soorma_common/decisions.py`

```python
class PlanAction(str, Enum):
    """Action types for planner decisions."""
    PUBLISH = "PUBLISH"      # Publish event to worker
    COMPLETE = "COMPLETE"    # Finalize plan
    WAIT = "WAIT"            # Pause for external input
    DELEGATE = "DELEGATE"    # Forward to another planner

@dataclass
class PublishAction:
    action: Literal[PlanAction.PUBLISH] = PlanAction.PUBLISH
    event_type: str
    data: Dict[str, Any]
    response_event: str
    reason: str

@dataclass
class CompleteAction:
    action: Literal[PlanAction.COMPLETE] = PlanAction.COMPLETE
    result: Dict[str, Any]
    reason: str

@dataclass
class WaitAction:
    action: Literal[PlanAction.WAIT] = PlanAction.WAIT
    expected_event: str
    reason: str
    timeout_seconds: int = 3600

@dataclass
class DelegateAction:
    action: Literal[PlanAction.DELEGATE] = PlanAction.DELEGATE
    target_planner_goal: str
    data: Dict[str, Any]
    reason: str

@dataclass
class PlannerDecision:
    """LLM decision response."""
    next_action: Union[PublishAction, CompleteAction, WaitAction, DelegateAction]
    current_state: str  # LLM's state description
    reasoning: str      # Explain decision
```

### Usage Example (10-choreography-basic)

```python
from soorma.ai.choreography import ChoreographyPlanner
from soorma.agents.planner import GoalContext
from soorma.plan_context import PlanContext

planner = ChoreographyPlanner(
    name="feedback-orchestrator",
    reasoning_model="gpt-4o",
    system_instructions=(
        "You are a feedback analysis orchestrator.\n\n"
        "WORKFLOW:\n"
        "1. DATA RETRIEVAL: Get raw feedback from datastore\n"
        "2. ANALYSIS: Extract sentiment and insights\n"
        "3. REPORTING: Format as human-readable report\n"
        "4. COMPLETION: Return final report\n\n"
        "Choose events based on CAPABILITY descriptions, not names."
    ),
)

@planner.on_goal("analyze.feedback")
async def handle_goal(goal: GoalContext, context: PlatformContext) -> None:
    """Handle feedback analysis goals."""
    
    # Create plan (no state machine - LLM decides)
    plan = await PlanContext.create_from_goal(
        goal=goal,
        context=context,
        state_machine={},  # Empty - ChoreographyPlanner uses LLM
        current_state="reasoning",
        status="running",
    )
    
    # Let LLM decide first action
    decision = await planner.reason_next_action(
        trigger=f"New goal: {goal.data.get('objective')}",
        context=context,
        plan_id=plan.plan_id,
        custom_context={"goal": goal.data},
    )
    
    # Update and execute
    plan.current_state = decision.current_state
    await plan.save()
    await planner.execute_decision(decision, context, goal, plan)

@planner.on_transition()
async def handle_transition(
    event: EventEnvelope,
    context: PlatformContext,
    plan: PlanContext,
    next_state: str,
) -> None:
    """Handle worker responses and continue."""
    
    # Store result
    plan.results[event.type] = event.data
    
    # Let LLM decide next action based on result
    decision = await planner.reason_next_action(
        trigger=f"Event: {event.type}",
        context=context,
        plan_id=plan.plan_id,
        custom_context={"last_event": event.type, "event_data": event.data},
    )
    
    plan.current_state = decision.current_state
    await plan.save()
    await planner.execute_decision(decision, context, event, plan)
```

### BYO Model Credentials

ChoreographyPlanner supports multiple LLM providers:

```python
# OpenAI
import os
os.environ["OPENAI_API_KEY"] = "sk-..."
planner = ChoreographyPlanner(..., reasoning_model="gpt-4o")

# Azure OpenAI
os.environ["AZURE_OPENAI_API_KEY"] = "..."
os.environ["AZURE_OPENAI_ENDPOINT"] = "https://..."
planner = ChoreographyPlanner(..., reasoning_model="azure/gpt-4")

# Anthropic Claude
os.environ["ANTHROPIC_API_KEY"] = "sk-ant-..."
planner = ChoreographyPlanner(..., reasoning_model="claude-3-5-sonnet-20241022")

# Ollama (local)
planner = ChoreographyPlanner(..., reasoning_model="ollama/llama3")
```

**Implementation:** Uses LiteLLM for unified interface across providers.

### Event Discovery Pattern

LLM discovers available events at runtime from Registry Service:

```python
# Inside reason_next_action()
available_events = await context.registry.list_events()
# Returns: [
#   {"event_type": "feedback.fetch", "capability": "retrieve raw feedback from datastore"},
#   {"event_type": "sentiment.analyze", "capability": "extract sentiment insights"},
#   {"event_type": "report.generate", "capability": "format data as report"},
# ]

# LLM chooses event based on capability match to current step
# Validation: Rejects event if not in available_events (prevents hallucinations)
```

### System Instructions Pattern

Inject business rules and constraints:

```python
system_instructions = """
You are an order processor.

BUSINESS RULES:
- Orders <$100: Auto-approve
- Orders $100-$5000: Manager approval required
- Orders >$5000: Executive approval required

WORKFLOW CONSTRAINTS:
- Always check inventory BEFORE payment
- If inventory insufficient, cancel order immediately
- Payment failures require 3 retries before cancellation

AVAILABLE EVENTS (discovered from Registry):
- inventory.check (capability: verify stock availability)
- payment.process (capability: charge customer)
- approval.request (capability: send approval notification)
- order.cancel (capability: cancel order and notify customer)

Choose events based on current step and business rules.
"""
```

### Custom Context Injection

Pass runtime data to LLM:

```python
decision = await planner.reason_next_action(
    trigger="Order received",
    context=context,
    plan_id=plan.plan_id,
    custom_context={
        "order_amount": 6500.00,
        "customer_tier": "gold",
        "inventory_status": {"widget": 50, "gadget": 0},
        "policy": "Gold customers get priority",
    },
)
# LLM uses custom_context to make informed decisions
# Example: "Amount $6500 requires executive approval per business rules"
```

### Circuit Breaker Pattern

Prevent infinite loops:

```python
MAX_ACTIONS = 20  # Configurable

action_count = len(plan_state.get("history", []))
if action_count >= MAX_ACTIONS:
    # Force completion
    decision.next_action = CompleteAction(
        reason="Max actions reached (circuit breaker)",
        result={"status": "incomplete", "reason": "action_limit"},
    )
```

**Logging:**
```python
if action_count >= MAX_ACTIONS:
    logger.warning(
        f"Circuit breaker activated for plan {plan_id}: "
        f"{action_count}/{MAX_ACTIONS} actions"
    )
```

### WAIT Action (Human-in-the-Loop)

Pause plans for external input:

```python
# LLM decides: WAIT for approval
decision = PlannerDecision(
    next_action=WaitAction(
        reason="Transaction >$5k requires manager approval",
        expected_event="approval.granted",
        timeout_seconds=3600,
    )
)

# Plan pauses with status="waiting"
# External system (approval UI, webhook) publishes approval.granted event
# SDK receives event, restores plan, continues workflow
```

**See:** [WAIT_ACTION_GUIDE.md](./WAIT_ACTION_GUIDE.md) for complete guide with examples and troubleshooting.

### Tracker Integration

ChoreographyPlanner integrates with Tracker Service for observability:

```python
@planner.on_transition()
async def handle_transition(event, context, plan, next_state):
    # Query plan progress
    progress = await context.tracker.get_plan_progress(
        plan.plan_id,
        tenant_id=event.tenant_id,
        user_id=event.user_id,
    )
    if progress:
        print(f"Completed {progress.completed_tasks}/{progress.task_count} tasks")
        print(f"Status: {progress.status}")
```

**See:** Platform Services > Tracker Service section for full API.

---

## Platform Services

### Tracker Service (RF-ARCH-010, RF-ARCH-011)

**Status:** ✅ Complete (Stage 4 Phase 3, February 2026)  
**Purpose:** Event-driven observability for agent workflows

#### Design Principles

1. **Passive Consumer** - Subscribes to events, no write APIs
2. **Multi-User Isolation** - Per-user observability with admin override
3. **Event-Driven** - No SDK instrumentation required
4. **Query-Only Interface** - Read-only REST APIs

#### Use Cases

**User-Scoped Observability:**
- "Show MY workflow execution history"
- "What tasks did MY research plan execute?"
- "Why did MY workflow fail?"
- User dashboards showing personal agent activity

**Tenant-Scoped Analytics (Admin):**
- "Which users are running the most workflows?"
- "What's our tenant-wide success rate?"
- "Platform usage metrics across all users"
- Resource quota enforcement

**Debugging & Auditing:**
- Event timeline for failed workflows
- State transition history
- Task execution traces
- Performance bottleneck identification

**Billing & Quotas:**
- Per-user task execution counts
- Agent performance metrics per user
- Usage-based billing calculations
- Fair-use quota enforcement

#### Event Subscriptions

Tracker subscribes to:
- `system-events` topic: `task.progress`, `task.state_changed`, `plan.started`, `plan.completed`
- `action-requests` topic: All events (record task starts)
- `action-results` topic: All events (record task completions)

#### Database Schema

All tables include `tenant_id` AND `user_id` for multi-user isolation:

```sql
-- User-scoped task execution records
CREATE TABLE tracker.task_executions (
    tenant_id UUID NOT NULL,
    user_id UUID NOT NULL,  -- Enables per-user queries
    task_id VARCHAR(100) NOT NULL,
    plan_id VARCHAR(100),
    state VARCHAR(50) NOT NULL,
    ...
);

-- RLS: Users see only their own executions
CREATE POLICY task_executions_user_isolation 
ON tracker.task_executions
USING (
    tenant_id = current_setting('app.tenant_id')::UUID
    AND user_id = current_setting('app.user_id')::UUID
);

-- RLS: Admins see all tenant executions
CREATE POLICY task_executions_admin_view
ON tracker.task_executions
USING (
    current_setting('app.role', true) = 'admin'
    AND tenant_id = current_setting('app.tenant_id')::UUID
);
```

#### Query APIs

```python
# User queries their own workflows
context = PlatformContext()  # user_id from JWT/session
progress = await context.tracker.get_plan_progress(plan_id)
# Returns: Only plans belonging to this user

# Admin queries all tenant workflows
admin_context = PlatformContext(role="admin")
all_plans = await admin_context.tracker.query_tenant_plans()
# Returns: All plans for the tenant (all users)
```

#### SDK Integration (Two-Layer Pattern)

**Layer 1:** TrackerServiceClient (low-level HTTP client)  
**Layer 2:** TrackerClient wrapper in PlatformContext

```python
@dataclass
class TrackerClient:
    """High-level Tracker Service wrapper."""
    
    async def get_plan_progress(self, plan_id: str) -> Optional[PlanProgress]:
        """Get plan execution status.
        
        Automatically scoped to current user via X-User-ID header.
        Admins can bypass with elevated permissions.
        """
        client = await self._ensure_client()
        # tenant_id/user_id extracted from context (NOT parameters)
        return await client.get_plan_progress(plan_id, tenant_id, user_id)
```

**Examples MUST use:** `context.tracker.*` (NOT `TrackerServiceClient` directly)

#### Future Enhancements (Deferred)

See [DEFERRED_WORK.md](../refactoring/DEFERRED_WORK.md#tracker-service-enhancements):
- Tracker Service UI (visualization dashboard)
- Advanced metrics aggregation (hourly/daily rollups)
- Alerting on failures (webhooks, email)
- Tracker Service dedicated feature area (`docs/tracker/`)
- SLA monitoring and anomaly detection

---

## Implementation Status

### Stage 3: Tool & Worker Models

**Completion Date:** February 12, 2026  
**Status:** ✅ 90% Complete (test expansion planned)

#### Phase 1: Tool Model (✅ Complete)
- ✅ InvocationContext model (lightweight)
- ✅ on_invoke() decorator
- ✅ Auto-response publishing
- ✅ Error handling
- ✅ Examples updated
- ✅ Tests passing

#### Phase 2: Worker Model (✅ Complete - Core Functionality)
- ✅ TaskContext model (863 lines)
  - save() / restore() persistence
  - Sequential delegation
  - Parallel delegation (fan-out/fan-in)
  - Result aggregation
  - Explicit completion
- ✅ Worker class (281 lines)
  - on_task() decorator
  - on_result() decorator
  - Auto-subscription to action-requests/results
  - Assignment filtering
  - Programmatic execution
- ✅ ResultContext model
  - restore_task() method
  - Success/failure detection
- ✅ Example implementation (08-worker-basic)
  - Sequential delegation
  - Parallel delegation
  - Result aggregation
- ✅ Infrastructure updates
  - Migration 006: task_context.user_id FK
  - Migration 007: plan_context.plan_id UUID FK
  - All 126 Memory Service tests passing
  - All 254 SDK tests passing
- 🟡 Test coverage (5 core tests, expansion planned)
  - Need 20+ tests for comprehensive coverage
  - Error handling scenarios
  - Multi-handler scenarios

#### Phase 3: Integration & Docs
- ✅ Documentation (this file)
- ✅ ARCHITECTURE.md updates
- ✅ Pattern selection framework
- ✅ Examples catalog updates

### Stage 4: Planner Model

**Status:** ✅ Complete (February 2026)

#### Phase 1: PlanContext Foundation (✅ Complete)
- ✅ PlanContext state machine model
- ✅ StateConfig, StateAction, StateTransition models
- ✅ on_goal() and on_transition() decorators
- ✅ GoalContext wrapper
- ✅ Plan persistence and restoration
- ✅ Template interpolation
- ✅ 09-planner-basic example
- ✅ Tests passing

#### Phase 2: ChoreographyPlanner (✅ Complete)
- ✅ ChoreographyPlanner class
- ✅ PlannerDecision types (PUBLISH, COMPLETE, WAIT, DELEGATE)
- ✅ LLM integration (OpenAI, Azure, Anthropic, Ollama)
- ✅ Event discovery from Registry
- ✅ Business rules via system_instructions
- ✅ Runtime context injection
- ✅ Circuit breaker (max_actions)
- ✅ Event validation (hallucination prevention)
- ✅ 10-choreography-basic example
- ✅ Tests passing

#### Phase 3: Tracker Service Integration (✅ Complete)
- ✅ TrackerServiceClient (service layer)
- ✅ TrackerClient wrapper (PlatformContext layer)
- ✅ Plan progress tracking
- ✅ Action history timeline
- ✅ Integration in choreography example
- ✅ Tests passing

#### Phase 4: Documentation & Release (✅ Complete)
- ✅ Agent patterns README with selection framework
- ✅ ARCHITECTURE.md with Planner sections
- ✅ Pattern comparison tables
- ✅ Examples catalog
- ✅ Tracker service documentation

---

## Test Coverage

### Tool Tests
**File:** `sdk/python/tests/agents/test_tool.py`

- ✅ InvocationContext creation
- ✅ on_invoke() handler registration
- ✅ Auto-response publishing
- ✅ Error handling
- ✅ Correlation ID preservation

### Worker Tests
**File:** `sdk/python/tests/agents/test_worker_phase3.py`

- ✅ TaskContext save calls memory
- ✅ TaskContext delegate publishes request
- ✅ ResultContext restore_task
- ✅ on_task() wrapper passes TaskContext
- ✅ on_result() wrapper passes ResultContext
- 🟡 Parallel delegation scenarios (planned)
- 🟡 Error handling (planned)
- 🟡 Assignment filtering (planned)

**Current:** 5 core tests passing  
**Target:** 20+ comprehensive tests

---

## Related Documentation

### Pattern Guides
- [README.md](./README.md) - User guide and patterns
- [WAIT_ACTION_GUIDE.md](./WAIT_ACTION_GUIDE.md) - Human-in-the-loop workflows with ChoreographyPlanner

### Architecture References
- [Event System Architecture](../event_system/ARCHITECTURE.md) - Event model details
- [Memory System Architecture](../memory_system/ARCHITECTURE.md) - Persistence layer

### Design Documents
- [Tool Model Design](../refactoring/sdk/04-TOOL-MODEL.md) - RF-SDK-005
- [Worker Model Design](../refactoring/sdk/05-WORKER-MODEL.md) - RF-SDK-004
- [Planner Model Design](../refactoring/sdk/06-PLANNER-MODEL.md) - RF-SDK-006

### Implementation Plans
- [Stage 3 Working Plan](../refactoring/STAGE_3_WORKING_PLAN.md) - Tool & Worker implementation
- [Stage 4 Master Plan](./plans/MASTER_PLAN_Stage4_Planner.md) - Planner implementation
