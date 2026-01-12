# SDK Refactoring: Planner Model

**Document:** 06-PLANNER-MODEL.md  
**Status:** ⬜ Not Started  
**Priority:** 🟡 Medium (Phase 2)  
**Last Updated:** January 11, 2026

---

## Quick Reference

| Aspect | Details |
|--------|----------|
| **Task** | RF-SDK-006: Planner on_goal() and on_transition() |
| **Files** | `sdk/python/soorma/agents/planner.py` |
| **Dependencies** | 01-EVENT-SYSTEM, 02-MEMORY-SDK, 03-COMMON-DTOS |
| **Blocks** | None |
| **Estimated Effort** | 3-4 days |

---

## Context

### Why This Matters

Planners are the **most complex agent type** - managing goals via state machines:

1. Planner receives goal event
2. Planner creates/restores `PlanContext` with state machine
3. State machine transitions based on incoming events
4. Each state may dispatch work to Workers/Tools
5. Plan completes when reaching terminal state

### Current State

- Planner creates plan and publishes all tasks immediately (no state machine)
- No support for dynamic plan generation with LLM
- No support for event-based state transitions
- No support for pause/resume (HITL)

### Key Files

```
sdk/python/soorma/
├── context.py          # PlatformContext (memory access)
└── agents/
    └── planner.py      # Planner class, on_goal, on_transition

soorma-common/
└── state.py            # StateConfig, StateTransition, StateAction
```

### Prerequisite Concepts

From **01-EVENT-SYSTEM** (must complete first):
- `bus.request()` - Dispatch work with `response_event`
- `bus.respond()` - Complete goal with result

From **02-MEMORY-SDK** (must complete first):
- `memory.store_plan_context()` - Persist PlanContext
- `memory.get_plan_context()` - Restore PlanContext
- `memory.create_plan()` - Create plan record

From **03-COMMON-DTOS** (must complete first):
- `StateConfig`, `StateTransition`, `StateAction` DTOs from `soorma-common`

---

## Summary

This document covers the Planner state machine model:
- **RF-SDK-006:** Planner `on_goal()` and `on_transition()` decorators with PlanContext

This is the most complex agent type, enabling LLM-driven planning and state machine execution.

---

## Tasks

### RF-SDK-006: Planner on_goal() and on_transition()

**Files:** [planner.py](../../sdk/python/soorma/agents/planner.py)

#### Current Issue

Planner creates plan and publishes all tasks immediately. No support for:
- Dynamic plan generation with LLM
- Event-based state transition handling
- Result aggregation
- Re-entrant plans for long-running conversations

---

## Target Design

### 1. PlanContext with State Machine

```python
@dataclass
class PlanContext:
    plan_id: str
    goal_event: str
    goal_data: Dict[str, Any]
    response_event: str  # Explicit response event from goal request
    status: str  # pending, running, completed, failed, paused
    
    # State machine with event-based transitions
    state_machine: Dict[str, StateConfig]  # state_name -> StateConfig
    current_state: str
    results: Dict[str, Any]  # Aggregated results from steps
    
    # For re-entrant / long-running plans
    parent_plan_id: Optional[str] = None  # For nested sub-plans
    session_id: Optional[str] = None  # Conversation/session context
    
    # Authentication context
    user_id: str
    tenant_id: str
    
    async def save(self):
        """Persist plan to working memory."""
        await self._context.memory.store_plan_context(
            plan_id=self.plan_id,
            session_id=self.session_id,
            context=self.to_dict(),
        )
    
    @classmethod
    async def restore(cls, plan_id: str, context: PlatformContext):
        """Restore plan from working memory."""
        data = await context.memory.get_plan_context(plan_id)
        return cls.from_dict(data, context)
    
    @classmethod
    async def restore_by_correlation(cls, correlation_id: str, context: PlatformContext):
        """Restore plan that has a task with this correlation_id."""
        data = await context.memory.get_plan_by_correlation(correlation_id)
        return cls.from_dict(data, context) if data else None
    
    def get_next_state(self, event: EventContext) -> Optional[str]:
        """
        Determine next state based on current state AND received event.
        
        A state may have multiple outgoing transitions based on different events.
        This is the key insight: state transitions are event-driven.
        """
        current_config = self.state_machine.get(self.current_state)
        if not current_config:
            return None
        
        # Find transition matching the received event
        for transition in current_config.transitions:
            if transition.on_event == event.event_type:
                # Optionally evaluate condition
                if transition.condition:
                    if not self._evaluate_condition(transition.condition, event):
                        continue
                return transition.to_state
        
        return None
    
    async def execute_next(self, trigger_event: Optional[EventContext] = None):
        """
        Execute the next step based on current state and triggering event.
        
        Args:
            trigger_event: The event that triggered this transition (for conditional routing)
        """
        # Determine next state based on event
        if trigger_event:
            next_state = self.get_next_state(trigger_event)
        else:
            # Initial execution - get first state after 'start'
            start_config = self.state_machine.get("start")
            next_state = start_config.default_next if start_config else None
        
        if not next_state:
            return  # No valid transition
        
        state_config = self.state_machine.get(next_state)
        if not state_config:
            return
        
        # Execute the action for this state
        if state_config.action:
            await self._context.bus.request(
                event_type=state_config.action.event_type,
                data=self._interpolate_data(state_config.action.data or {}),
                response_event=state_config.action.response_event,
                correlation_id=self.plan_id,
            )
        
        self.current_state = next_state
        self.status = "running"
        await self.save()
    
    def is_complete(self) -> bool:
        """Check if plan reached a terminal state."""
        current_config = self.state_machine.get(self.current_state)
        return current_config and current_config.is_terminal
    
    async def finalize(self, result: Optional[Dict[str, Any]] = None):
        """Complete the plan and publish final result using the specified response_event."""
        self.status = "completed"
        self.results["final"] = result
        
        # Use the response_event specified in the original goal request
        # This follows our request/response pattern: requestor specifies event name
        await self._context.bus.respond(
            event_type=self.response_event,  # Use explicit response_event, not derived
            data={"plan_id": self.plan_id, "result": result},
            correlation_id=self.parent_plan_id or self.plan_id,
        )
        
        await self.save()  # Keep for history
    
    async def pause(self, reason: str = "user_input_required"):
        """Pause the plan (e.g., waiting for HITL) - indefinite/extended."""
        self.status = "paused"
        self.state["pause_reason"] = reason
        await self.save()
    
    async def resume(self, input_data: Dict[str, Any]):
        """Resume a paused plan with new input."""
        self.status = "running"
        self.results["user_input"] = input_data
        await self.save()
        await self.execute_next()
```

### 2. StateConfig DTOs (from soorma-common)

```python
@dataclass
class StateConfig:
    """Configuration for a state in the plan state machine."""
    state_name: str
    description: str
    action: Optional[StateAction] = None  # Action to execute on entering state
    transitions: List[StateTransition] = field(default_factory=list)
    default_next: Optional[str] = None  # For unconditional transitions
    is_terminal: bool = False


@dataclass
class StateTransition:
    """A transition from one state to another based on an event."""
    on_event: str  # Event type that triggers this transition
    to_state: str  # Target state
    condition: Optional[str] = None  # Optional condition expression


@dataclass
class StateAction:
    """Action to execute when entering a state."""
    event_type: str
    response_event: str
    data: Optional[Dict[str, Any]] = None
```

> **📦 Common Library Note:** `StateConfig`, `StateTransition`, and `StateAction` live in `soorma-common` as Pydantic DTOs. This allows State Tracker service to reuse the same DTOs. See [03-COMMON-DTOS.md](03-COMMON-DTOS.md).

### 3. Planner Class with Decorators

```python
class Planner(Agent):
    def on_goal(self, event_type: str):
        """Register handler for goal events."""
        def decorator(func):
            @self.on_event(topic="action-requests", event_type=event_type)
            async def wrapper(event, context):
                goal = GoalContext.from_event(event, context)
                await func(goal, context)
            return func
        return decorator
    
    def on_transition(self):
        """
        Register handler for ALL state transitions.
        Called for any event on action-requests or action-results
        where correlation_id matches a known plan.
        """
        def decorator(func):
            # Subscribe to both topics
            @self.on_event(topic="action-requests", event_type="*")
            @self.on_event(topic="action-results", event_type="*")
            async def wrapper(event, context):
                correlation_id = event.get("correlation_id")
                if not correlation_id:
                    return
                
                # Check if we have a plan for this correlation
                plan = await PlanContext.restore(correlation_id, context)
                if plan:
                    transition = TransitionContext(event=event, plan=plan)
                    await func(transition, context)
            return func
        return decorator
    
    async def create_plan(
        self,
        goal: GoalContext,
        agents: List[AgentDefinition],
        context: PlatformContext,
    ) -> PlanContext:
        """
        Create a plan using LLM reasoning.
        
        Discovers available agents, their capabilities,
        and generates a state machine for achieving the goal.
        """
        # Implementation uses AI toolkit for LLM reasoning
        pass
    
    async def reason_next_action(
        self,
        plan: PlanContext,
        event: EventContext,
        context: PlatformContext,
    ) -> Optional[str]:
        """
        Use LLM to decide next action for dynamic plans.
        
        Returns the event_type to publish, or None if plan is complete.
        """
        # Implementation uses AI toolkit for LLM reasoning
        pass
```

---

## State Machine Example

### Event-Based Transitions

```python
# State machine where transitions depend on the received event
state_machine = {
    "start": StateConfig(
        state_name="start",
        description="Initial state",
        default_next="searching",
    ),
    "searching": StateConfig(
        state_name="searching",
        description="Searching for information",
        action=StateAction(
            event_type="web.search.requested",
            response_event="web.search.completed",
            data={"query": "{goal_data.topic}"},
        ),
        transitions=[
            # Different events lead to different states
            StateTransition(on_event="web.search.completed", to_state="analyzing"),
            StateTransition(on_event="web.search.failed", to_state="retry_search"),
            StateTransition(on_event="web.search.no_results", to_state="ask_user"),
        ]
    ),
    "retry_search": StateConfig(
        state_name="retry_search",
        description="Retry with broader query",
        action=StateAction(
            event_type="web.search.requested",
            response_event="web.search.completed",
            data={"query": "{goal_data.topic}", "broad": True},
        ),
        transitions=[
            StateTransition(on_event="web.search.completed", to_state="analyzing"),
            StateTransition(on_event="web.search.failed", to_state="failed"),
        ]
    ),
    "ask_user": StateConfig(
        state_name="ask_user",
        description="Ask user for clarification",
        action=StateAction(
            event_type="notification.human_input",
            response_event="user.clarification.provided",
            data={"question": "No results found. Can you provide more details?"},
        ),
        transitions=[
            StateTransition(on_event="user.clarification.provided", to_state="searching"),
        ]
    ),
    "analyzing": StateConfig(
        state_name="analyzing",
        description="Analyzing search results",
        action=StateAction(
            event_type="content.analyze.requested",
            response_event="content.analyze.completed",
        ),
        transitions=[
            StateTransition(on_event="content.analyze.completed", to_state="done"),
        ]
    ),
    "done": StateConfig(
        state_name="done",
        description="Plan completed successfully",
        is_terminal=True,
    ),
    "failed": StateConfig(
        state_name="failed",
        description="Plan failed",
        is_terminal=True,
    ),
}
```

---

## Plan-Level Pause vs Worker-Level HITL

| Aspect | Plan-Level Pause | Worker-Level HITL |
|--------|------------------|-------------------|
| **Timeout** | Extended/indefinite (no timeout) | Time-bound (`timeout_seconds` required) |
| **Scope** | Entire plan execution halts | Single task waits, plan may continue |
| **Use Case** | External approvals, compliance gates | User input, confirmations |
| **Example** | Budget approval, legal review | "Is this correct?", "Which option?" |

### Planner Pause/Resume Example

```python
# Planner pauses plan (not individual task) for approval
async def handle_transition(transition, context):
    plan = transition.plan
    
    if plan.current_state == "awaiting_budget_approval":
        await plan.pause(reason="budget_approval_required")
        # Plan is now paused - will resume when external event arrives

# Resume is triggered by external event (e.g., webhook → event)
@planner.on_event(topic="business-facts", event_type="budget.approved")
async def handle_approval(event, context):
    plan = await PlanContext.restore_by_correlation(event.correlation_id)
    if plan and plan.status == "paused":
        await plan.resume({"approved_amount": event.data["amount"]})
```

---

## Re-Entrant Plans (Long-Running Conversations)

### Session Model

```
User (tenant_id + user_id)
├── Session A (conversation about "AI research")
│   ├── Plan A1 (goal: "find papers") - completed
│   ├── Plan A2 (goal: "summarize findings") - running
│   │   └── Sub-plan A2.1 (delegated sub-goal) - running
│   └── Plan A3 (goal: "draft report") - pending (depends on A2)
│
├── Session B (conversation about "budget planning")
│   └── Plan B1 (goal: "analyze expenses") - paused (waiting for input)
```

**Key Points:**
1. Plans can reference `parent_plan_id` for nesting
2. Plans grouped by `session_id` for conversation context
3. `status: paused` allows waiting without losing state
4. Memory service queries support filtering by session and status

---

## Tests to Add

```python
# test/test_planner.py

async def test_plan_context_save_restore():
    """PlanContext should persist and restore from memory."""
    pass

async def test_planner_on_goal_creates_plan():
    """on_goal handler should receive GoalContext."""
    pass

async def test_planner_on_transition_routes_events():
    """on_transition should match events to plans by correlation_id."""
    pass

async def test_state_machine_transition():
    """State machine should transition based on event type."""
    pass

async def test_planner_finalize_uses_response_event():
    """finalize() should publish to the explicit response_event."""
    pass

async def test_planner_pause_resume():
    """Plan should support pause/resume flow."""
    pass

async def test_nested_plans():
    """Sub-plans should link via parent_plan_id."""
    pass
```

---

## Implementation Checklist

- [ ] **Read existing code** in `planner.py`
- [ ] **Import DTOs** from `soorma-common` (StateConfig, StateTransition, StateAction)
- [ ] **Write tests first** for PlanContext persistence
- [ ] **Implement** `PlanContext` with state machine methods
- [ ] **Write tests first** for state transitions
- [ ] **Implement** `get_next_state()` and `execute_next()`
- [ ] **Write tests first** for `on_goal()` decorator
- [ ] **Implement** Planner class with `on_goal()` and `on_transition()`
- [ ] **Write tests first** for pause/resume
- [ ] **Implement** `pause()` and `resume()` methods
- [ ] **Update examples** with state machine patterns

---

## Dependencies

- **Depends on:** [01-EVENT-SYSTEM.md](01-EVENT-SYSTEM.md) (RF-SDK-001, 002, 003)
- **Depends on:** [02-MEMORY-SDK.md](02-MEMORY-SDK.md) (plan context storage)
- **Depends on:** [03-COMMON-DTOS.md](03-COMMON-DTOS.md) (StateConfig DTOs from soorma-common)
- **Blocked by:** Nothing (can mock memory initially)

---

## Open Questions

None currently - design is settled.

---

## Related Documents

- [00-OVERVIEW.md](00-OVERVIEW.md) - Agent progression model
- [05-WORKER-MODEL.md](05-WORKER-MODEL.md) - Worker async pattern
- [03-COMMON-DTOS.md](03-COMMON-DTOS.md) - Common library DTOs
