# Example 09: Basic Planner with State Machine

**Demonstrates:** Planner agent with state machine-based orchestration using Phase 1 patterns

## What This Shows

This example demonstrates the **Stage 4 Phase 1** Planner patterns:

1. **`@on_goal()` decorator** - Creates plans from goal events
2. **`PlanContext`** - State machine container with persistence
3. **`@on_transition()` decorator** - Routes events to plans via correlation_id
4. **State-driven execution** - Events trigger state transitions
5. **GoalContext wrapper** - Clean goal event handling

## Architecture

```
Client → Planner (creates PlanContext) → Worker (tasks)
           ↓                               ↓
       State Machine                    Results
       (3 states)                          ↓
           ↓                          Planner (transition)
       Complete ←───────────────────────┘
```

## State Machine

```
start → research → complete
```

- **start**: Initial state, transitions to research
- **research**: Publishes research task, waits for result
- **complete**: Terminal state, publishes final result

## Files

- `planner.py` - Planner agent with @on_goal and @on_transition
- `worker.py` - Mock research worker
- `client.py` - Sends goals and receives results
- `start.sh` - Launches agents

## Running

### Terminal 1: Start Infrastructure
```bash
# From soorma-core root
soorma dev --build
```

### Terminal 2: Start Agents
```bash
cd examples/09-planner-basic
./start.sh
```

This starts both the Planner and Worker agents.

### Terminal 3: Send Goal
```bash
cd examples/09-planner-basic
python client.py "AI agents"
```

Or with a different topic:
```bash
python client.py "quantum computing"
```

## Expected Output

**Client:**
```
📤 Sending goal: Research topic 'AI agents'
⏳ Waiting for result...
✅ Received: Research complete: Found 3 papers on AI agents
```

**Planner:**
```
📋 Received goal: research.goal
📝 Creating plan with 3 states
💾 Saved plan: plan-abc123
▶️  Executing state: start → research
📤 Publishing: research.task

📥 Transition event: research.complete
🔄 State transition: research → complete
✅ Plan complete: plan-abc123
📤 Publishing final result
```

**Worker:**
```
📥 Received: research.task
🔬 Researching: AI agents
✅ Complete: Found 3 papers on AI agents
```

## Key Patterns

### 1. Goal Handler (@on_goal)
```python
@planner.on_goal("research.goal")
async def handle_goal(goal: GoalContext, context: PlatformContext):
    # Create state machine
    states = {
        "start": StateConfig(...),
        "research": StateConfig(...),
        "complete": StateConfig(is_terminal=True)
    }
    
    # Create plan
    plan = PlanContext(
        plan_id=str(uuid4()),
        goal_event=goal.event_type,
        state_machine=states,
        ...
    )
    
    # Save and execute
    await plan.save()
    await plan.execute_next()
```

### 2. Transition Handler (@on_transition)
```python
@planner.on_transition()
async def handle_transition(
    event: EventEnvelope,
    context: PlatformContext,
    plan: PlanContext,
    next_state: str,
) -> None:
    """SDK auto-filters to action-results and restores plan."""
    # Update state
    plan.current_state = next_state
    plan.results[event.type] = event.data
    
    # Execute or finalize
    if plan.is_complete():
        await plan.finalize(result=event.data)
    else:
        await plan.execute_next(event)
```

**What the SDK Does Automatically:**
- Subscribes to `action-results` topic only (filters out action-requests)
- Requires `tenant_id` and `user_id` for multi-tenant plan restoration
- Restores plan using `PlanContext.restore_by_correlation()`
- Validates transition exists in state machine
- Only invokes handler if plan found and transition valid

**Authentication Context Propagation:**
Workers MUST propagate authentication context in responses:
```python
await context.bus.respond(
    event_type=event.response_event,
    data=result,
    correlation_id=event.correlation_id,
    tenant_id=event.tenant_id,      # Required
    user_id=event.user_id,          # Required
    session_id=event.session_id,    # Recommended
)
```

### 3. State Machine Definition
```python
states = {
    "start": StateConfig(
        state_name="start",
        description="Initial state",
        default_next="research",  # Auto-transition
    ),
    "research": StateConfig(
        state_name="research",
        description="Research phase",
        action=StateAction(
            event_type="research.task",
            response_event="research.complete",
            data={"query": "{{goal_data.topic}}"}  # Template interpolation
        ),
        transitions=[
            StateTransition(on_event="research.complete", to_state="complete")
        ]
    ),
    "complete": StateConfig(
        state_name="complete",
        description="Terminal state",
        is_terminal=True
    )
}
```

## Concepts

### GoalContext
Replaces old `Goal` class with cleaner API:
```python
@dataclass
class GoalContext:
    event_type: str
    data: Dict[str, Any]
    correlation_id: str
    response_event: Optional[str]
    session_id: Optional[str]
    user_id: Optional[str]
    tenant_id: Optional[str]
```

### PlanContext
State machine container with:
- `save()`, `restore()`, `restore_by_correlation()` - Persistence
- `execute_next()` - Execute current state action
- `get_next_state()` - Event-driven transitions
- `is_complete()` - Check terminal state
- `finalize()` - Publish final result

### Handler-Only Registration (RF-SDK-023)
Only events with actual handlers appear in `events_consumed`:
- `@on_goal("research.goal")` → adds "research.goal"
- `@on_transition()` → does NOT add "*" wildcard
- Topics never added to events_consumed

## Differences from Old Pattern

**Before (base Agent pattern):**
```python
@planner.on_event("research.goal", topic=EventTopic.ACTION_REQUESTS)
async def handle_goal(event: EventEnvelope, context: PlatformContext):
    # Manual state management
    # No GoalContext wrapper
    # No PlanContext
```

**After (Phase 1 Planner pattern):**
```python
@planner.on_goal("research.goal")
async def handle_goal(goal: GoalContext, context: PlatformContext):
    # State machine defined declaratively
    # GoalContext wrapper
    # PlanContext handles persistence
```

## Next Steps

- **Phase 2**: `ChoreographyPlanner` with LLM-based reasoning
- **Phase 2**: `PlannerDecision` types for structured decisions
- **Phase 3**: Tracker Service for progress observability
- **Phase 4**: Examples with complex multi-step workflows

## Related Examples

- `08-worker-basic` - Worker pattern with task handling
- `04-memory-working` - Working memory patterns
- `research-advisor` - Complex planner (will be refactored in Phase 2)
