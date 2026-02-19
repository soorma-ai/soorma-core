# Action Plan: Stage 4 Phase 1 - Planner Foundation (SOOR-PLAN-001-P1)

**Status:** 📋 Planning  
**Created:** February 17, 2026  
**Phase:** 1 of 4 (Foundation - State Machine & DTOs)  
**Estimated Duration:** 4 days  
**Parent Plan:** [MASTER_PLAN_Stage4_Planner.md](MASTER_PLAN_Stage4_Planner.md)

---

## 1. Requirements & Core Objective

### Summary

Implement the foundational components for Planner state machine orchestration:

1. **PlanContext class** - State machine container with persistence
2. **Planner decorators** - `on_goal()` and `on_transition()` handlers
3. **Handler-only registration** - Event registration from handlers only (RF-SDK-023)

This phase enables Planners to create, persist, restore, and execute state machine-based plans WITHOUT LLM reasoning (that comes in Phase 2).

### Acceptance Criteria

- [ ] PlanContext can be created, saved, and restored from Memory Service
- [ ] PlanContext executes state machines with event-driven transitions
- [ ] `@planner.on_goal()` decorator creates PlanContext and starts execution
- [ ] `@planner.on_transition()` decorator routes events to plans by correlation_id
- [ ] Planner only registers events that have actual handlers (RF-SDK-023)
- [ ] Plans support pause/resume for HITL workflows
- [ ] Plans publish final results using explicit `response_event` from goal
- [ ] All unit tests pass (15+ tests)
- [ ] Integration test demonstrates end-to-end goal → plan → tasks → completion

### Success Metrics

**Code Quality:**
- 90%+ test coverage on new code
- All type hints present (args + return values)
- Google-style docstrings on all public methods
- Passes mypy strict type checking

**Functionality:**
- State transitions work correctly based on incoming events
- Memory Service integration persists plan state
- Correlation tracking works across plan lifecycle

---

## 2. Technical Design

### Component: SDK (Python)

### Data Models

**New File:** `sdk/python/soorma/plan_context.py`

```python
@dataclass
class PlanContext:
    """
    State machine context for a plan execution.
    
    Manages plan lifecycle:
    - Creation from goal events
    - State persistence via Memory Service
    - Event-driven state transitions
    - Task execution based on state actions
    - Completion with response publication
    
    Attributes:
        plan_id: Unique plan identifier
        goal_event: Original goal event type
        goal_data: Goal parameters
        response_event: Event type for final result (from original request)
        status: Plan execution status (pending|running|completed|failed|paused)
        state_machine: State definitions (state_name -> StateConfig)
        current_state: Current state name
        results: Aggregated results from completed steps
        parent_plan_id: Optional parent plan for nested workflows
        session_id: Optional session for conversation context
        user_id: User authentication context
        tenant_id: Tenant isolation
        _context: PlatformContext for service access (not persisted)
    """
    
    plan_id: str
    goal_event: str
    goal_data: Dict[str, Any]
    response_event: str
    status: str  # pending, running, completed, failed, paused
    state_machine: Dict[str, StateConfig]
    current_state: str
    results: Dict[str, Any]
    parent_plan_id: Optional[str] = None
    session_id: Optional[str] = None
    user_id: str = ""
    tenant_id: str = ""
    _context: Optional[PlatformContext] = None
    
    # Methods (see implementation details below)
    async def save()
    @classmethod async def restore()
    @classmethod async def restore_by_correlation()
    def get_next_state(event: EventContext) -> Optional[str]
    async def execute_next(trigger_event: Optional[EventContext] = None)
    def is_complete() -> bool
    async def finalize(result: Optional[Dict[str, Any]] = None)
    async def pause(reason: str = "user_input_required")
    async def resume(input_data: Dict[str, Any])
    def to_dict() -> Dict[str, Any]
    @classmethod def from_dict(data: Dict[str, Any], context: PlatformContext)
```

**Modified File:** `sdk/python/soorma/agents/planner.py`

```python
class Planner(Agent):
    """
    Strategic reasoning engine that breaks goals into tasks.
    
    NEW in Phase 1:
    - on_goal() decorator for goal handling
    - on_transition() decorator for state transitions
    - Handler-only event registration (RF-SDK-023)
    """
    
    def __init__(self, name: str, **kwargs):
        super().__init__(name, **kwargs)
        self._goal_handlers = {}  # event_type -> handler
        self._transition_handler = None
        self.config.agent_type = "planner"
    
    def on_goal(self, event_type: str):
        """
        Register handler for goal events.
        
        Goal events trigger plan creation and initial execution.
        
        Args:
            event_type: Goal event type (e.g., "research.goal")
        
        Returns:
            Decorator function
            
        Example:
            @planner.on_goal("research.goal")
            async def plan_research(goal, context):
                # Create state machine
                state_machine = {...}
                plan = PlanContext.create_from_goal(goal, state_machine)
                await plan.save()
                await plan.execute_next()
        """
        def decorator(func):
            self._goal_handlers[event_type] = func
            # Register event as consumed (RF-SDK-023)
            if event_type not in self.config.events_consumed:
                self.config.events_consumed.append(event_type)
            # Register underlying event handler
            @self.on_event(event_type, topic=EventTopic.ACTION_REQUESTS)
            async def wrapper(event, context):
                # Convert event to GoalContext
                goal = GoalContext.from_event(event, context)
                await func(goal, context)
            return func
        return decorator
    
    def on_transition(self):
        """
        Register handler for ALL state transitions.
        
        This handler is called for ANY event on action-requests or action-results
        where the correlation_id matches a known plan.
        
        Returns:
            Decorator function
            
        Example:
            @planner.on_transition()
            async def handle_transition(event, context):
                # Restore plan by correlation_id
                plan = await PlanContext.restore_by_correlation(
                    event.correlation_id, context
                )
                if not plan:
                    return  # Not a plan-related event
                
                # Determine next state based on event
                next_state = plan.get_next_state(event)
                if next_state:
                    await plan.execute_next(trigger_event=event)
                elif plan.is_complete():
                    await plan.finalize()
        """
        def decorator(func):
            self._transition_handler = func
            
            # Subscribe to ALL events on both topics
            # NOTE: We don't add these topics to events_consumed (RF-SDK-023)
            # because topics are not event types
            
            @self.on_event("*", topic=EventTopic.ACTION_REQUESTS)
            @self.on_event("*", topic=EventTopic.ACTION_RESULTS)
            async def wrapper(event, context):
                await func(event, context)
            
            return func
        return decorator


@dataclass
class GoalContext:
    """
    Wrapper for goal events passed to on_goal handlers.
    
    Provides structured access to goal data and request metadata.
    """
    event_type: str
    data: Dict[str, Any]
    correlation_id: str
    response_event: str  # From original request
    session_id: Optional[str]
    user_id: str
    tenant_id: str
    _raw_event: EventEnvelope
    _context: PlatformContext
    
    @classmethod
    def from_event(cls, event: EventEnvelope, context: PlatformContext):
        """Create GoalContext from event envelope."""
        return cls(
            event_type=event.event_type,
            data=event.data,
            correlation_id=event.correlation_id,
            response_event=event.metadata.get("response_event", ""),
            session_id=event.metadata.get("session_id"),
            user_id=event.user_id,
            tenant_id=event.tenant_id,
            _raw_event=event,
            _context=context,
        )
```

### Event Schema

**Consumed Events:**
- Topic: `action-requests`
- Event types: Goal event types registered via `@planner.on_goal()` (e.g., `research.goal`)
- Transitions: ALL events on `action-requests` and `action-results` (filtered by correlation_id)

**Published Events:**
- Topic: `action-requests`
- Event types: Task events from `StateAction.event_type` (e.g., `search.requested`)
- Response events: Uses `response_event` from original goal request

**Critical Design Point (RF-SDK-023):**
- **Only goal event types** appear in `events_consumed` (from `@on_goal()` handlers)
- **Topics are NOT event types** - never register "action-requests" or "action-results" as event types
- **Wildcard transitions** use `"*"` but don't add to events registry

---

## 3. Task Tracking Matrix

### Day 1: Design & Setup

- [x] **Task 1.1:** Review Master Plan and refactoring docs ✅ (Status: Completed)
- [x] **Task 1.2:** Create this Action Plan ✅ (Status: Completed)
- [x] **Task 1.3:** Verify MemoryServiceClient plan context methods exist ✅ (Status: Completed)
  - ✅ Verify `MemoryServiceClient.store_plan_context()` exists at [client.py:704](../../sdk/python/soorma/memory/client.py#L704)
  - ✅ Verify `MemoryServiceClient.get_plan_context()` exists at [client.py:751](../../sdk/python/soorma/memory/client.py#L751)
  - ✅ Verify `MemoryServiceClient.get_plan_by_correlation()` exists at [client.py:806](../../sdk/python/soorma/memory/client.py#L806)
  - ✅ Method signatures match PlanContext needs
- [x] **Task 1.4:** Add plan context wrapper methods to MemoryClient ✅ (Status: Completed - CRITICAL)
  - ✅ Added `store_plan_context()` wrapper in [context.py](../../sdk/python/soorma/context.py) MemoryClient class
  - ✅ Added `get_plan_context()` wrapper
  - ✅ Added `get_plan_by_correlation()` wrapper
  - ✅ All delegate to `self._client` (MemoryServiceClient) after `_ensure_client()`
  - ✅ PlanContext can now use `context.memory.store_plan_context()`
- [x] **Task 1.5:** Set up `plan_context.py` file structure ✅ (Status: Completed)
- [x] **Task 1.6:** Import StateConfig DTOs from soorma-common ✅ (Status: Completed)
- [x] **Task 1.7:** Define PlanContext dataclass skeleton ✅ (Status: Completed)

**Deliverables:**
- `sdk/python/soorma/plan_context.py` (skeleton, ~50 lines)
- `sdk/python/soorma/context.py` (add 3 plan context wrapper methods, ~60 lines added)
- Action Plan committed to docs/
- Verification notes on Memory Client methods

---

### Day 2: PlanContext Implementation (TDD)

#### RED: Write Failing Tests

- [x] **Task 2.1:** Write test for `PlanContext.to_dict()` and `from_dict()` ✅ (Status: Completed)
- [x] **Task 2.2:** Write test for `PlanContext.save()` calls Memory Service ✅ (Status: Completed)
- [x] **Task 2.3:** Write test for `PlanContext.restore()` from Memory ✅ (Status: Completed)
- [x] **Task 2.4:** Write test for `PlanContext.restore_by_correlation()` ✅ (Status: Completed)
- [x] **Task 2.5:** Write test for `get_next_state()` with transitions ✅ (Status: Completed)

#### GREEN: Implement PlanContext Core

- [x] **Task 2.6:** Implement `to_dict()` and `from_dict()` methods ✅ (Status: Completed)
- [x] **Task 2.7:** Implement `save()` using `context.memory.store_plan_context()` ✅ (Status: Completed)
- [x] **Task 2.8:** Implement `restore()` class method ✅ (Status: Completed)
- [x] **Task 2.9:** Implement `restore_by_correlation()` class method ✅ (Status: Completed)
- [x] **Task 2.10:** Implement `get_next_state(event)` with transition matching ✅ (Status: Completed)

**Deliverables:**
- ✅ `sdk/python/tests/agents/test_plan_context.py` (11 passing tests)
- ✅ `sdk/python/soorma/plan_context.py` (core methods implemented)

---

### Day 3: PlanContext State Machine (TDD)

#### RED: Write Failing Tests

- [x] **Task 3.1:** Write test for `execute_next()` initial state ✅ (Status: Completed)
- [x] **Task 3.2:** Write test for `execute_next()` with trigger_event ✅ (Status: Completed)
- [x] **Task 3.3:** Write test for `is_complete()` terminal state check ✅ (Status: Completed)
- [x] **Task 3.4:** Write test for `finalize()` uses response_event ✅ (Status: Completed)
- [x] **Task 3.5:** Write test for `pause()` and `resume()` ✅ (Status: Completed)

#### GREEN: Implement State Machine Logic

- [x] **Task 3.6:** Implement `execute_next()` for initial and transition states ✅ (Status: Completed)
- [x] **Task 3.7:** Implement `is_complete()` terminal state check ✅ (Status: Completed)
- [x] **Task 3.8:** Implement `finalize()` with response_event publication ✅ (Status: Completed)
- [x] **Task 3.9:** Implement `pause()` status update ✅ (Status: Completed)
- [x] **Task 3.10:** Implement `resume()` with input_data ✅ (Status: Completed)

**Deliverables:**
- ✅ `sdk/python/tests/agents/test_plan_context.py` (19 passing tests)
- ✅ `sdk/python/soorma/plan_context.py` (complete, ~450 lines total)

---

### Day 4: Planner Decorators & Integration (TDD)

#### RED: Write Failing Tests

- [ ] **Task 4.1:** Write test for `@planner.on_goal()` decorator registration ✅ (Status: Not Started)
- [ ] **Task 4.2:** Write test for `on_goal()` creates GoalContext ✅ (Status: Not Started)
- [ ] **Task 4.3:** Write test for `@planner.on_transition()` decorator ✅ (Status: Not Started)
- [ ] **Task 4.4:** Write test for transition handler routes by correlation_id ✅ (Status: Not Started)
- [ ] **Task 4.5:** Write test for handler-only event registration (RF-SDK-023) ✅ (Status: Not Started)

#### GREEN: Implement Planner Decorators

- [ ] **Task 4.6:** Implement `on_goal()` decorator in planner.py ✅ (Status: Not Started)
- [ ] **Task 4.7:** Implement `GoalContext` class ✅ (Status: Not Started)
- [ ] **Task 4.8:** Implement `on_transition()` decorator ✅ (Status: Not Started)
- [ ] **Task 4.9:** Update Planner `__init__` for handler tracking ✅ (Status: Not Started)
- [ ] **Task 4.10:** Verify handler-only registration (RF-SDK-023) ✅ (Status: Not Started)

#### Integration Testing

- [ ] **Task 4.11:** Write integration test: goal → plan → tasks → completion ✅ (Status: Not Started)
- [ ] **Task 4.12:** Write integration test: pause/resume workflow ✅ (Status: Not Started)
- [ ] **Task 4.13:** Write integration test: nested plans with parent_plan_id ✅ (Status: Not Started)

**Deliverables:**
- `sdk/python/tests/test_planner.py` (~150 lines)
- `sdk/python/soorma/agents/planner.py` (updated, ~550 lines total)
- `sdk/python/tests/agents/test_planner_integration.py` (~150 lines)

---

### Final Tasks (End of Day 4)

- [ ] **Task 4.14:** Update `CHANGELOG.md` in SDK with Phase 1 changes ✅ (Status: Not Started)
- [ ] **Task 4.15:** Run full test suite and verify 90%+ coverage ✅ (Status: Not Started)
- [ ] **Task 4.16:** Commit with message: `feat(sdk): Implement PlanContext state machine (RF-SDK-006)` ✅ (Status: Not Started)
- [ ] **Task 4.17:** Update Master Plan Phase 1 status to ✅ Complete ✅ (Status: Not Started)

---

## 4. TDD Strategy

### Unit Tests

**File:** `sdk/python/tests/agents/test_plan_context.py`

```python
"""
Tests for PlanContext state machine.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from soorma.plan_context import PlanContext
from soorma_common.state import StateConfig, StateTransition, StateAction


class TestPlanContextPersistence:
    """Tests for plan persistence and restoration."""
    
    async def test_plan_context_to_dict(self):
        """PlanContext.to_dict() should serialize all fields."""
        # Create plan with state machine
        plan = PlanContext(
            plan_id="plan-123",
            goal_event="research.goal",
            goal_data={"topic": "AI"},
            response_event="research.completed",
            status="pending",
            state_machine={"start": StateConfig(...)},
            current_state="start",
            results={},
            user_id="user-1",
            tenant_id="tenant-1",
        )
        
        # Serialize
        data = plan.to_dict()
        
        # Verify
        assert data["plan_id"] == "plan-123"
        assert data["goal_event"] == "research.goal"
        assert data["state_machine"]["start"]["state_name"] == "start"
    
    async def test_plan_context_from_dict(self):
        """PlanContext.from_dict() should restore from serialized data."""
        # Mock context
        context = MagicMock()
        
        # Serialized data
        data = {
            "plan_id": "plan-123",
            "goal_event": "research.goal",
            "goal_data": {"topic": "AI"},
            "response_event": "research.completed",
            "status": "pending",
            "state_machine": {...},
            "current_state": "start",
            "results": {},
            "user_id": "user-1",
            "tenant_id": "tenant-1",
        }
        
        # Restore
        plan = PlanContext.from_dict(data, context)
        
        # Verify
        assert plan.plan_id == "plan-123"
        assert plan._context is context
    
    async def test_plan_context_save_calls_memory(self):
        """save() should call memory.store_plan_context()."""
        # Mock context
        context = MagicMock()
        context.memory.store_plan_context = AsyncMock()
        
        # Create plan
        plan = PlanContext(
            plan_id="plan-123",
            ...,
            _context=context,
        )
        
        # Save
        await plan.save()
        
        # Verify Memory Service called
        context.memory.store_plan_context.assert_called_once()
        call_args = context.memory.store_plan_context.call_args[1]
        assert call_args["plan_id"] == "plan-123"
    
    async def test_plan_context_restore(self):
        """restore() should load from Memory Service."""
        # Mock context
        context = MagicMock()
        context.memory.get_plan_context = AsyncMock(return_value={
            "plan_id": "plan-123",
            ...serialized data...
        })
        
        # Restore
        plan = await PlanContext.restore("plan-123", context)
        
        # Verify
        assert plan.plan_id == "plan-123"
        context.memory.get_plan_context.assert_called_once_with("plan-123")
    
    async def test_plan_context_restore_by_correlation(self):
        """restore_by_correlation() should find plan by correlation_id."""
        # Mock context
        context = MagicMock()
        context.memory.get_plan_by_correlation = AsyncMock(return_value={
            "plan_id": "plan-123",
            ...
        })
        
        # Restore
        plan = await PlanContext.restore_by_correlation("corr-456", context)
        
        # Verify
        assert plan.plan_id == "plan-123"
        context.memory.get_plan_by_correlation.assert_called_once_with("corr-456")
    
    async def test_restore_by_correlation_not_found(self):
        """restore_by_correlation() should return None if not found."""
        context = MagicMock()
        context.memory.get_plan_by_correlation = AsyncMock(return_value=None)
        
        plan = await PlanContext.restore_by_correlation("unknown", context)
        
        assert plan is None


class TestPlanContextStateTransitions:
    """Tests for state machine transitions."""
    
    async def test_get_next_state_with_matching_event(self):
        """get_next_state() should return target state for matching event."""
        # State machine: start -> search (on search.requested)
        state_machine = {
            "start": StateConfig(
                state_name="start",
                description="Initial",
                transitions=[
                    StateTransition(on_event="search.requested", to_state="searching")
                ],
            ),
            "searching": StateConfig(state_name="searching", ...),
        }
        
        plan = PlanContext(
            current_state="start",
            state_machine=state_machine,
            ...
        )
        
        # Mock event
        event = MagicMock()
        event.event_type = "search.requested"
        
        # Get next state
        next_state = plan.get_next_state(event)
        
        assert next_state == "searching"
    
    async def test_get_next_state_no_matching_transition(self):
        """get_next_state() should return None for unrecognized events."""
        state_machine = {
            "start": StateConfig(
                state_name="start",
                transitions=[
                    StateTransition(on_event="search.requested", to_state="searching")
                ],
            ),
        }
        
        plan = PlanContext(current_state="start", state_machine=state_machine, ...)
        
        event = MagicMock()
        event.event_type="unknown.event"
        
        next_state = plan.get_next_state(event)
        
        assert next_state is None
    
    async def test_get_next_state_multiple_transition(self):
        """State can have multiple transitions based on different events."""
        state_machine = {
            "processing": StateConfig(
                state_name="processing",
                transitions=[
                    StateTransition(on_event="task.succeeded", to_state="success"),
                    StateTransition(on_event="task.failed", to_state="retry"),
                ],
            ),
        }
        
        plan = PlanContext(current_state="processing", state_machine=state_machine, ...)
        
        # Test success path
        success_event = MagicMock(event_type="task.succeeded")
        assert plan.get_next_state(success_event) == "success"
        
        # Test failure path
        failure_event = MagicMock(event_type="task.failed")
        assert plan.get_next_state(failure_event) == "retry"


class TestPlanContextExecution:
    """Tests for state execution."""
    
    async def test_execute_next_initial_state(self):
        """execute_next() should start from initial state when no trigger_event."""
        # State machine
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
                    data={"query": "AI research"},
                ),
            ),
        }
        
        # Mock context
        context = MagicMock()
        context.bus.request = AsyncMock()
        context.memory.store_plan_context = AsyncMock()
        
        plan = PlanContext(
            plan_id="plan-123",
            current_state="start",
            state_machine=state_machine,
            _context=context,
            ...
        )
        
        # Execute
        await plan.execute_next()
        
        # Verify: published action event
        context.bus.request.assert_called_once()
        call_args = context.bus.request.call_args[1]
        assert call_args["event_type"] == "search.requested"
        assert call_args["response_event"] == "search.completed"
        
        # Verify: state updated
        assert plan.current_state == "search"
        assert plan.status == "running"
        
        # Verify: saved
        context.memory.store_plan_context.assert_called_once()
    
    async def test_execute_next_with_trigger_event(self):
        """execute_next() should transition based on trigger_event."""
        state_machine = {
            "search": StateConfig(
                state_name="search",
                transitions=[
                    StateTransition(on_event="search.completed", to_state="summarize")
                ],
            ),
            "summarize": StateConfig(
                state_name="summarize",
                action=StateAction(
                    event_type="summarize.requested",
                    response_event="summarize.completed",
                ),
            ),
        }
        
        context = MagicMock()
        context.bus.request = AsyncMock()
        context.memory.store_plan_context = AsyncMock()
        
        plan = PlanContext(
            current_state="search",
            state_machine=state_machine,
            _context=context,
            ...
        )
        
        # Trigger event
        trigger = MagicMock(event_type="search.completed")
        
        # Execute
        await plan.execute_next(trigger_event=trigger)
        
        # Verify transitioned to summarize
        assert plan.current_state == "summarize"
        context.bus.request.assert_called_once()
        assert context.bus.request.call_args[1]["event_type"] == "summarize.requested"
    
    async def test_is_complete_terminal_state(self):
        """is_complete() should return True for terminal states."""
        state_machine = {
            "done": StateConfig(
                state_name="done",
                is_terminal=True,
            ),
        }
        
        plan = PlanContext(
            current_state="done",
            state_machine=state_machine,
            ...
        )
        
        assert plan.is_complete() is True
    
    async def test_is_complete_non_terminal_state(self):
        """is_complete() should return False for non-terminal states."""
        state_machine = {
            "running": StateConfig(
                state_name="running",
                is_terminal=False,
            ),
        }
        
        plan = PlanContext(
            current_state="running",
            state_machine=state_machine,
            ...
        )
        
        assert plan.is_complete() is False
    
    async def test_finalize_uses_response_event(self):
        """finalize() should publish result to explicit response_event."""
        context = MagicMock()
        context.bus.respond = AsyncMock()
        context.memory.store_plan_context = AsyncMock()
        
        plan = PlanContext(
            plan_id="plan-123",
            response_event="research.completed",  # Explicit from goal
            _context=context,
            ...
        )
        
        # Finalize
        result = {"summary": "AI is evolving"}
        await plan.finalize(result)
        
        # Verify published to response_event
        context.bus.respond.assert_called_once()
        call_args = context.bus.respond.call_args[1]
        assert call_args["event_type"] == "research.completed"
        assert call_args["data"]["result"] == result
        
        # Verify status updated
        assert plan.status == "completed"


class TestPlanContextPauseResume:
    """Tests for pause/resume HITL workflows."""
    
    async def test_pause_sets_status(self):
        """pause() should update status to paused."""
        context = MagicMock()
        context.memory.store_plan_context = AsyncMock()
        
        plan = PlanContext(
            status="running",
            _context=context,
            ...
        )
        
        await plan.pause(reason="user_approval_required")
        
        assert plan.status == "paused"
        context.memory.store_plan_context.assert_called_once()
    
    async def test_resume_continues_execution(self):
        """resume() should update status and call execute_next()."""
        context = MagicMock()
        context.bus.request = AsyncMock()
        context.memory.store_plan_context = AsyncMock()
        
        state_machine = {
            "waiting": StateConfig(
                state_name="waiting",
                default_next="process",
            ),
            "process": StateConfig(
                state_name="process",
                action=StateAction(
                    event_type="process.requested",
                    response_event="process.completed",
                ),
            ),
        }
        
        plan = PlanContext(
            status="paused",
            current_state="waiting",
            state_machine=state_machine,
            results={},
            _context=context,
            ...
        )
        
        # Resume
        await plan.resume({"user_input": "approved"})
        
        # Verify status updated
        assert plan.status == "running"
        assert plan.results["user_input"] == {"user_input": "approved"}
        
        # Verify execute_next called (state transitioned)
        assert plan.current_state == "process"
        context.bus.request.assert_called_once()
```

**File:** `sdk/python/tests/test_planner.py`

```python
"""
Tests for Planner decorators and handler registration.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from soorma import Planner
from soorma.plan_context import PlanContext
from soorma.agents.planner import GoalContext


class TestPlannerOnGoalDecorator:
    """Tests for @planner.on_goal() decorator."""
    
    def test_on_goal_registers_handler(self):
        """on_goal() should register goal handler."""
        planner = Planner(name="test-planner")
        
        @planner.on_goal("research.goal")
        async def handle_goal(goal, context):
            pass
        
        assert "research.goal" in planner._goal_handlers
    
    def test_on_goal_registers_event_consumed(self):
        """on_goal() should add event to events_consumed (RF-SDK-023)."""
        planner = Planner(name="test-planner")
        
        @planner.on_goal("research.goal")
        async def handle_goal(goal, context):
            pass
        
        # RF-SDK-023: Only goal event types registered, not topics
        assert "research.goal" in planner.config.events_consumed
        assert "action-requests" not in planner.config.events_consumed
    
    async def test_on_goal_creates_goal_context(self):
        """on_goal handler should receive GoalContext."""
        planner = Planner(name="test-planner")
        
        received_goal = None
        
        @planner.on_goal("research.goal")
        async def handle_goal(goal, context):
            nonlocal received_goal
            received_goal = goal
        
        # Simulate event
        event = MagicMock()
        event.event_type = "research.goal"
        event.data = {"topic": "AI"}
        event.correlation_id = "corr-123"
        event.metadata = {"response_event": "research.completed"}
        
        context = MagicMock()
        
        # Call handler
        await planner._goal_handlers["research.goal"](
            GoalContext.from_event(event, context), context
        )
        
        # Verify GoalContext created
        assert received_goal is not None
        assert received_goal.event_type == "research.goal"
        assert received_goal.data == {"topic": "AI"}


class TestPlannerOnTransitionDecorator:
    """Tests for @planner.on_transition() decorator."""
    
    def test_on_transition_registers_handler(self):
        """on_transition() should register transition handler."""
        planner = Planner(name="test-planner")
        
        @planner.on_transition()
        async def handle_transition(event, context):
            pass
        
        assert planner._transition_handler is not None
    
    def test_on_transition_no_topics_in_events(self):
        """on_transition() should NOT add topics to events (RF-SDK-023)."""
        planner = Planner(name="test-planner")
        
        @planner.on_transition()
        async def handle_transition(event, context):
            pass
        
        # RF-SDK-023: Topics are not event types
        assert "action-requests" not in planner.config.events_consumed
        assert "action-results" not in planner.config.events_consumed
    
    async def test_transition_routes_by_correlation_id(self):
        """Transition handler should restore plan by correlation_id."""
        planner = Planner(name="test-planner")
        
        restored_plan = None
        
        # Mock PlanContext.restore_by_correlation
        async def mock_restore(correlation_id, context):
            if correlation_id == "plan-123":
                return MagicMock(plan_id="plan-123")
            return None
        
        @planner.on_transition()
        async def handle_transition(event, context):
            nonlocal restored_plan
            restored_plan = await PlanContext.restore_by_correlation(
                event.correlation_id, context
            )
        
        # Mock event
        event = MagicMock()
        event.correlation_id = "plan-123"
        event.event_type = "search.completed"
        
        context = MagicMock()
        
        # Call with mock
        with pytest.mock.patch.object(
            PlanContext, "restore_by_correlation", mock_restore
        ):
            await planner._transition_handler(event, context)
        
        # Verify plan restored
        assert restored_plan is not None
        assert restored_plan.plan_id == "plan-123"


class TestHandlerOnlyRegistration:
    """Tests for RF-SDK-023: Handler-only event registration."""
    
    def test_no_events_without_handlers(self):
        """Planner with no handlers should have empty events_consumed."""
        planner = Planner(
            name="test-planner",
            capabilities=["planning", "research"],
        )
        
        # RF-SDK-023: Capabilities don't generate events
        assert len(planner.config.events_consumed) == 0
    
    def test_only_goal_events_registered(self):
        """Only events with @on_goal handlers should be in events_consumed."""
        planner = Planner(name="test-planner")
        
        @planner.on_goal("research.goal")
        async def handle_research(goal, context):
            pass
        
        @planner.on_goal("analysis.goal")
        async def handle_analysis(goal, context):
            pass
        
        # Should have exactly 2 events
        assert len(planner.config.events_consumed) == 2
        assert "research.goal" in planner.config.events_consumed
        assert "analysis.goal" in planner.config.events_consumed
```

**File:** `sdk/python/tests/agents/test_planner_integration.py`

```python
"""
Integration tests for Planner end-to-end workflows.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from soorma import Planner
from soorma.plan_context import PlanContext
from soorma_common.state import StateConfig, StateAction, StateTransition


@pytest.mark.integration
class TestPlannerEndToEnd:
    """End-to-end workflow tests."""
    
    async def test_goal_to_completion_flow(self):
        """
        Test complete flow: goal → plan creation → task execution → completion.
        """
        # Setup planner
        planner = Planner(name="research-planner")
        
        # Define state machine
        state_machine = {
            "start": StateConfig(
                state_name="start",
                default_next="search",
            ),
            "search": StateConfig(
                state_name="search",
                description="Search for papers",
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
                description="Complete",
                is_terminal=True,
            ),
        }
        
        # Mock context
        context = MagicMock()
        context.bus.request = AsyncMock()
        context.bus.respond = AsyncMock()
        context.memory.store_plan_context = AsyncMock()
        
        # Setup goal handler
        @planner.on_goal("research.goal")
        async def handle_goal(goal, context):
            plan = PlanContext(
                plan_id=goal.correlation_id,
                goal_event=goal.event_type,
                goal_data=goal.data,
                response_event=goal.response_event,
                status="pending",
                state_machine=state_machine,
                current_state="start",
                results={},
                user_id=goal.user_id,
                tenant_id=goal.tenant_id,
                _context=context,
            )
            await plan.save()
            await plan.execute_next()
        
        # Setup transition handler
        @planner.on_transition()
        async def handle_transition(event, context):
            plan = await PlanContext.restore_by_correlation(
                event.correlation_id, context
            )
            if not plan:
                return
            
            next_state = plan.get_next_state(event)
            if next_state:
                await plan.execute_next(trigger_event=event)
            elif plan.is_complete():
                await plan.finalize({"summary": "Papers found"})
        
        # STEP 1: Simulate goal event
        goal_event = MagicMock()
        goal_event.event_type = "research.goal"
        goal_event.data = {"topic": "AI agents"}
        goal_event.correlation_id = "plan-001"
        goal_event.metadata = {"response_event": "research.completed"}
        goal_event.user_id = "user-1"
        goal_event.tenant_id = "tenant-1"
        
        from soorma.agents.planner import GoalContext
        goal_ctx = GoalContext.from_event(goal_event, context)
        
        await handle_goal(goal_ctx, context)
        
        # Verify: Task published
        assert context.bus.request.call_count == 1
        call_args = context.bus.request.call_args[1]
        assert call_args["event_type"] == "search.requested"
        
        # STEP 2: Simulate search.completed event
        result_event = MagicMock()
        result_event.event_type = "search.completed"
        result_event.correlation_id = "plan-001"
        result_event.data = {"papers": ["Paper1", "Paper2"]}
        
        # Mock restore
        saved_plan = None
        
        async def mock_restore(correlation_id, ctx):
            if correlation_id == "plan-001":
                return PlanContext(
                    plan_id="plan-001",
                    goal_event="research.goal",
                    goal_data={"topic": "AI agents"},
                    response_event="research.completed",
                    status="running",
                    state_machine=state_machine,
                    current_state="search",
                    results={},
                    user_id="user-1",
                    tenant_id="tenant-1",
                    _context=ctx,
                )
            return None
        
        with pytest.mock.patch.object(
            PlanContext, "restore_by_correlation", mock_restore
        ):
            await handle_transition(result_event, context)
        
        # Verify: Plan completed
        assert context.bus.respond.call_count == 1
        respond_args = context.bus.respond.call_args[1]
        assert respond_args["event_type"] == "research.completed"
        assert respond_args["data"]["result"]["summary"] == "Papers found"
    
    async def test_pause_resume_hitl_workflow(self):
        """Test pause/resume for human-in-the-loop workflows."""
        # State machine with approval step
        state_machine = {
            "start": StateConfig(state_name="start", default_next="approval"),
            "approval": StateConfig(
                state_name="approval",
                description="Wait for approval",
                transitions=[
                    StateTransition(on_event="approval.granted", to_state="execute")
                ],
            ),
            "execute": StateConfig(
                state_name="execute",
                action=StateAction(
                    event_type="task.execute",
                    response_event="task.completed",
                ),
                transitions=[
                    StateTransition(on_event="task.completed", to_state="done")
                ],
            ),
            "done": StateConfig(state_name="done", is_terminal=True),
        }
        
        context = MagicMock()
        context.bus.request = AsyncMock()
        context.memory.store_plan_context = AsyncMock()
        
        plan = PlanContext(
            plan_id="plan-hitl",
            state_machine=state_machine,
            current_state="approval",
            status="running",
            _context=context,
            ...
        )
        
        # STEP 1: Pause for approval
        await plan.pause(reason="awaiting_user_approval")
        
        assert plan.status == "paused"
        context.memory.store_plan_context.assert_called()
        
        # STEP 2: Resume with approval
        approval_event = MagicMock(event_type="approval.granted")
        await plan.resume({"approved_by": "user-123"})
        
        # Should transition to execute and publish task
        # (this would happen in execute_next called by resume)
        assert plan.status == "running"
        assert plan.results["user_input"]["approved_by"] == "user-123"
```

### Integration Tests

Integration tests will use mocked Memory Service and Event Bus to verify:
- Goal event → PlanContext creation → first state execution
- Result event → plan restoration → state transition → next action
- Terminal state → finalize → response publication
- Pause/resume HITL workflow

---

## 5. Forward Deployed Logic Decision

### Decision: Use Full Memory Service Integration

**Rationale:**
- Memory Service already exists and is fully functional (Stage 2 complete)
- PlanContext persistence is critical for multi-step workflows
- Plan restoration by correlation_id is essential for event-driven state machines
- No FDE needed - Memory Service is production-ready

### What We're NOT Building (FDE)

- ✅ **Tracker Service** - Deferred to Phase 3 (use logs for now)
- ✅ **LLM reasoning** - Deferred to Phase 2 (manual state machines for now)
- ✅ **Conditional transitions** - Deferred to Stage 5 (simple event-based transitions only)
- ✅ **EventSelector utility** - Deferred to Stage 5 (manual event discovery for now)

### 48-Hour Filter Applied

Phase 1 focuses on:
- ✅ Core state machine (event-driven transitions)
- ✅ Persistence (Memory Service integration)
- ✅ Decorators (on_goal, on_transition)

**Estimate:** 4 days (within 48-hour per-component limit)

---

## 6. Implementation Notes

### Memory Service Integration (Two-Layer Architecture)

**IMPORTANT Discovery:** Memory Service has plan context methods, but they're not exposed through the PlatformContext wrapper!

**Architecture:**
1. **MemoryServiceClient** ([memory/client.py](../../sdk/python/soorma/memory/client.py)) - Low-level HTTP client
   - ✅ Has `store_plan_context()` at line 704
   - ✅ Has `get_plan_context()` at line 751  
   - ✅ Has `get_plan_by_correlation()` at line 806

2. **MemoryClient wrapper** ([context.py](../../sdk/python/soorma/context.py)) - High-level API in PlatformContext
   - ✅ Has task context methods (`store_task_context()`, `get_task_context()`, etc.)
   - ❌ **MISSING** plan context wrapper methods
   - **Task 1.4 adds these wrappers**

**Why This Matters:**
- PlanContext receives `PlatformContext` in handlers
- PlanContext calls `context.memory.store_plan_context()`
- But `context.memory` is the MemoryClient wrapper, not MemoryServiceClient directly
- We must add wrapper methods that delegate to the underlying client

**Wrapper Implementation Pattern:**

```python
# In sdk/python/soorma/context.py - MemoryClient class

async def store_plan_context(
    self,
    plan_id: str,
    session_id: Optional[str],
    goal_event: str,
    goal_data: Dict[str, Any],
    response_event: Optional[str] = None,
    state: Optional[Dict[str, Any]] = None,
    current_state: Optional[str] = None,
    correlation_ids: Optional[List[str]] = None,
) -> 'PlanContextResponse':
    """
    Store plan context (delegates to MemoryServiceClient).
    
    Called by PlanContext.save() after state transitions.
    """
    client = await self._ensure_client()
    return await client.store_plan_context(
        plan_id=plan_id,
        session_id=session_id,
        goal_event=goal_event,
        goal_data=goal_data,
        response_event=response_event,
        state=state,
        current_state=current_state,
        correlation_ids=correlation_ids,
    )

async def get_plan_context(self, plan_id: str) -> Optional['PlanContextResponse']:
    """
    Retrieve plan context (delegates to MemoryServiceClient).
    
    Called by PlanContext.restore() to resume plan execution.
    """
    client = await self._ensure_client()
    return await client.get_plan_context(plan_id)

async def get_plan_by_correlation(self, correlation_id: str) -> Optional['PlanContextResponse']:
    """
    Find plan by correlation ID (delegates to MemoryServiceClient).
    
    Called by on_transition() handlers to route events to plans.
    """
    client = await self._ensure_client()
    return await client.get_plan_by_correlation(correlation_id)
```

**PlanContext Usage (After Wrappers Added):**

```python
# Save
await context.memory.store_plan_context(
    plan_id=self.plan_id,
    session_id=self.session_id,
    goal_event=self.goal_event,
    goal_data=self.goal_data,
    response_event=self.response_event,
    state=self.to_dict(),
    current_state=self.current_state,
    correlation_ids=[self.plan_id],  # Track plan's correlation
)

# Restore by plan_id
data = await context.memory.get_plan_context(plan_id)

# Restore by correlation_id (for transition routing)
data = await context.memory.get_plan_by_correlation(correlation_id)
```

### Event Bus Integration

State actions use `bus.request()` for task dispatch:

```python
await self._context.bus.request(
    event_type=state_config.action.event_type,
    data=self._interpolate_data(state_config.action.data),
    response_event=state_config.action.response_event,
    correlation_id=self.plan_id,
)
```

Completion uses `bus.respond()` with explicit `response_event`:

```python
await self._context.bus.respond(
    event_type=self.response_event,  # From original goal request
    data={"plan_id": self.plan_id, "result": result},
    correlation_id=self.correlation_id,
)
```

### StateConfig DTOs

Import from soorma-common (already implemented in Stage 2):

```python
from soorma_common.state import StateConfig, StateTransition, StateAction
```

These DTOs are Pydantic models - use `.model_dump()` for serialization.

### Data Interpolation

`_interpolate_data()` helper for template substitution in state actions:

```python
def _interpolate_data(self, template: Dict[str, Any]) -> Dict[str, Any]:
    """
    Replace {{goal_data.field}} placeholders with actual values.
    
    Example:
        template: {"query": "{{goal_data.topic}}"}
        goal_data: {"topic": "AI agents"}
        result: {"query": "AI agents"}
    """
    import json
    import re
    
    json_str = json.dumps(template)
    
    # Replace {{goal_data.field}}
    for match in re.finditer(r'\{\{goal_data\.(\w+)\}\}', json_str):
        field = match.group(1)
        value = self.goal_data.get(field, "")
        json_str = json_str.replace(match.group(0), str(value))
    
    return json.loads(json_str)
```

---

## 7. Success Criteria Checklist

### Functionality

- [ ] PlanContext can be created from goal events
- [ ] PlanContext persists to Memory Service
- [ ] PlanContext restores from Memory Service by plan_id
- [ ] PlanContext restores by correlation_id (for transition routing)
- [ ] State transitions work based on incoming events
- [ ] State actions publish events via bus.request()
- [ ] Terminal states trigger finalize() with result publication
- [ ] finalize() uses explicit response_event from goal
- [ ] pause() updates status and persists
- [ ] resume() continues execution from paused state
- [ ] @planner.on_goal() creates GoalContext wrapper
- [ ] @planner.on_goal() registers event in events_consumed
- [ ] @planner.on_transition() routes by correlation_id
- [ ] Handler-only registration works (RF-SDK-023)

### Testing

- [ ] 90%+ test coverage on new code
- [ ] All unit tests pass (15+ tests)
- [ ] Integration tests pass (3+ tests)
- [ ] No regression in existing tests

### Code Quality

- [ ] All functions have type hints (args + returns)
- [ ] All public methods have Google-style docstrings
- [ ] Code passes mypy strict type checking
- [ ] Code follows PEP 8 style guide
- [ ] No TODOs or FIXMEs in committed code

### Documentation

- [ ] CHANGELOG.md updated with Phase 1 changes
- [ ] Inline comments explain "why" for complex logic
- [ ] Module docstrings updated

---

## 8. Files Created/Modified

### New Files

- `sdk/python/soorma/plan_context.py` (~300 lines)
- `sdk/python/tests/agents/test_plan_context.py` (~200 lines)
- `sdk/python/tests/test_planner.py` (~150 lines)
- `sdk/python/tests/agents/test_planner_integration.py` (~150 lines)

### Modified Files

- `sdk/python/soorma/context.py` (+60 lines: plan context wrapper methods in MemoryClient)
- `sdk/python/soorma/agents/planner.py` (+150 lines: decorators, GoalContext)
- `sdk/python/CHANGELOG.md` (+20 lines: Phase 1 release notes)

### Total Lines: ~1030 new/modified lines

---

## 9. Dependencies

### Upstream (Must be complete)

- ✅ Stage 1: Event System (bus.request, bus.respond, response_event)
- ✅ Stage 2: Memory SDK plan context methods **VERIFIED**:
  - `context.memory.store_plan_context()` - [client.py:704](../../sdk/python/soorma/memory/client.py#L704)
  - `context.memory.get_plan_context()` - [client.py:751](../../sdk/python/soorma/memory/client.py#L751)
  - `context.memory.update_plan_context()` - [client.py:775](../../sdk/python/soorma/memory/client.py#L775)
  - `context.memory.get_plan_by_correlation()` - [client.py:806](../../sdk/python/soorma/memory/client.py#L806)
- ✅ Stage 2: StateConfig DTOs in soorma-common
- ✅ Memory Service API endpoints `/v1/memory/plan-context/*` - [plan_context.py](../../services/memory/src/memory_service/api/v1/plan_context.py)

### Downstream (Unblocks)

- Phase 2: PlannerDecision types and ChoreographyPlanner (depends on PlanContext)
- Phase 3: Tracker Service (depends on plan state events)
- Phase 4: Documentation and migration guides

---

## 10. Risk Mitigation

### Risk: Memory Service performance with complex state machines

**Likelihood:** Low  
**Impact:** Medium  
**Mitigation:**
- State machines stored as JSON (efficient serialization)
- Use indexes on plan_id and correlation_ids
- Monitor query performance in integration tests

### Risk: Event routing complexity with wildcard subscriptions

**Likelihood:** Medium  
**Impact:** Medium  
**Mitigation:**
- Test correlation_id filtering thoroughly
- Use mock events in unit tests to verify routing
- Integration tests cover multiple concurrent plans

### Risk: State machine serialization/deserialization bugs

**Likelihood:** Medium  
**Impact:** High  
**Mitigation:**
- TDD approach with to_dict/from_dict tests first
- Verify StateConfig DTOs serialize correctly (Pydantic)
- Test edge cases (empty transitions, missing states)

---

## 11. Next Steps After Phase 1

Once Phase 1 is complete:

1. **Update Master Plan** - Mark Phase 1 ✅ Complete
2. **Create Phase 2 Action Plan** - PlannerDecision types and ChoreographyPlanner
3. **Developer Review** - Demo state machine functionality
4. **Proceed to Phase 2** - LLM-based autonomous orchestration

---

## 12. Commit Strategy

### Commit 1: Memory Client Wrappers + PlanContext Skeleton (Day 1)
```
feat(sdk): Add plan context wrappers and PlanContext skeleton

- Add store_plan_context(), get_plan_context(), get_plan_by_correlation() 
  wrappers to MemoryClient in context.py (delegates to MemoryServiceClient)
- Create plan_context.py with dataclass definition
- Import StateConfig DTOs from soorma-common
- Add to_dict/from_dict methods
- No tests yet (skeleton only)

Fixes: PlatformContext.memory now exposes plan context methods
Part of RF-SDK-006 (Phase 1, Day 1)
```

### Commit 2: PlanContext Persistence (Day 2)
```
feat(sdk): Implement PlanContext persistence

- Add save() using Memory Service
- Add restore() and restore_by_correlation() class methods
- Add get_next_state() for event-driven transitions
- Tests: persistence and state transition tests

Part of RF-SDK-006 (Phase 1, Day 2)
```

### Commit 3: PlanContext Execution (Day 3)
```
feat(sdk): Implement PlanContext state machine execution

- Add execute_next() for state actions
- Add is_complete() terminal state check
- Add finalize() with response_event publication
- Add pause() and resume() for HITL
- Tests: execution and pause/resume tests

Part of RF-SDK-006 (Phase 1, Day 3)
```

### Commit 4: Planner Decorators (Day 4)
```
feat(sdk): Add Planner on_goal and on_transition decorators

- Add on_goal() decorator for goal handling
- Add GoalContext wrapper class
- Add on_transition() decorator for state transitions
- Implement handler-only registration (RF-SDK-023)
- Tests: decorator and integration tests
- Update CHANGELOG.md

Completes RF-SDK-006 (Phase 1)
```

---

## 13. Developer Notes

### Type Safety

Ensure all PlanContext methods have proper type hints:

```python
async def save(self) -> None:
    ...

@classmethod
async def restore(
    cls,
    plan_id: str,
    context: PlatformContext,
) -> Optional['PlanContext']:
    ...

def get_next_state(self, event: EventContext) -> Optional[str]:
    ...
```

### Error Handling

Add error handling for:
- Memory Service unavailable (log and raise)
- Invalid state machine (validate on creation)
- Missing transitions (log warning, no-op)
- Serialization errors (log and raise)

### Logging

Add structured logging:

```python
import logging

logger = logging.getLogger(__name__)

logger.info(
    "Plan executing state transition",
    extra={
        "plan_id": self.plan_id,
        "from_state": self.current_state,
        "to_state": next_state,
        "event_type": event.event_type,
    },
)
```

### Performance

- Use async methods throughout (no blocking I/O)
- Minimize Memory Service calls (batch where possible)
- Cache state machine config (already in memory)

---

**Status:** 📋 Ready for Implementation  
**Next Action:** Begin Day 1 tasks (create PlanContext file, import DTOs)  
**Approval Required:** Developer approval to proceed with implementation
