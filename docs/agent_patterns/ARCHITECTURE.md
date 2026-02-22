# Agent Patterns: Technical Architecture

**Status:** ✅ Stage 3 Complete (Tool & Worker) | 🟡 Stage 4 Planned (Planner)  
**Last Updated:** February 15, 2026  
**Related Stages:** Stage 3 (RF-SDK-004, RF-SDK-005, RF-SDK-022)

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

## Planner Model (RF-SDK-006, RF-SDK-015, RF-SDK-016)

**Status:** 🟡 Stage 4 Planned

### Design Goals

- Goal decomposition and orchestration
- State machine for workflow tracking
- LLM-based reasoning for next action selection
- ChoreographyPlanner for autonomous orchestration

### Decorators

```python
class Planner(Agent):
    def on_goal(self, event_type: str):
        """Handle goal events - initial workflow trigger."""
        pass
    
    def on_transition(self):
        """Handle state transitions in workflow."""
        pass
```

### PlanContext (State Machine)

```python
@dataclass
class PlanContext:
    plan_id: str
    goal_event: str
    goal_data: Dict[str, Any]
    state_machine: StateMachine
    current_state: str
    transitions: List[StateTransition]
    
    @classmethod
    async def create_from_goal(...)
    async def save()
    async def restore()
    async def execute_next()
    async def finalize()
```

### ChoreographyPlanner (RF-SDK-016)

Autonomous orchestration class that uses LLM reasoning for decision-making:

```python
from soorma.ai.choreography import ChoreographyPlanner
from soorma.plan_context import PlanContext

planner = ChoreographyPlanner(
    name="orchestrator",
    reasoning_model="gpt-4o",
    system_instructions="""Business rules and constraints...""",  # Custom logic
    max_actions=20,  # Circuit breaker
)

@planner.on_goal("order.received")
async def handle_goal(goal, context):
    plan = await PlanContext.create_from_goal(
        goal=goal,
        context=context,
        state_machine={},  # ChoreographyPlanner uses LLM, not state machine
        current_state="reasoning",
        status="running",
    )
    # LLM discovers available events from Registry
    # LLM reasons about next action
    # SDK validates event exists before publishing
    decision = await planner.reason_next_action(
        trigger=f"Order: ${goal.data['amount']}",
        context=context,
        custom_context={"policy": "Orders >$5k need approval"},  # Runtime context
    )
    await planner.execute_decision(decision, context, goal_event=goal, plan=plan)
```

**Key Features:**
- **LLM Reasoning:** Autonomous decision-making based on available events
- **Business Logic:** Inject rules via `system_instructions` parameter
- **Runtime Context:** Pass dynamic data via `custom_context` parameter
- **Event Validation:** Prevents LLM hallucinations by validating events exist
- **WAIT Action:** Pause/resume for human-in-the-loop workflows (see guide below)

**Decision Types:**
- **PUBLISH:** Publish event to trigger workers
- **COMPLETE:** Finalize plan with response
- **WAIT:** Pause for external input (approval, upload, callback)
- **DELEGATE:** Forward to another planner

#### WAIT Action for Human-in-the-Loop

ChoreographyPlanner supports pausing plans to wait for external input:

```python
# LLM decides to WAIT for approval
decision = PlannerDecision(
    next_action=WaitAction(
        reason="Order >$5k requires manager approval",
        expected_event="approval.granted",
        timeout_seconds=3600,
    )
)

# Plan pauses, external system provides input
# Plan auto-resumes when expected_event arrives
```

**Common Use Cases:**
- Financial approvals (transactions >threshold)
- Document uploads (user must provide file)
- External API callbacks (payment verification)
- User clarification (ambiguous requests)

**See:** [WAIT_ACTION_GUIDE.md](./WAIT_ACTION_GUIDE.md) for complete examples, testing, and troubleshooting.

**Design:** [06-PLANNER-MODEL.md](../refactoring/sdk/06-PLANNER-MODEL.md) for detailed architecture.

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
- 🟡 Documentation (this file)
- 🟡 ARCHITECTURE.md updates
- 🟡 Migration guide

### Stage 4: Planner Model

**Status:** ⬛ Planned

- ⬛ on_goal() and on_transition() decorators
- ⬛ PlanContext state machine
- ⬛ PlannerDecision types
- ⬛ ChoreographyPlanner class
- ⬛ EventSelector utility
- ⬛ research-advisor example

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
