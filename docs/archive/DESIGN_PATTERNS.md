# Design Patterns

**Status:** 📝 Draft  
**Last Updated:** January 6, 2026

This document describes agent design patterns in Soorma.

---

## Overview

Soorma agents can be organized using various patterns depending on your use case. This guide helps you choose the right pattern for your needs.

---

## Pattern Catalog

### 1. Worker Pattern

**Use when:** Simple reactive agents that respond to events

**Complexity:** ⭐ Beginner

**Example:** [01-hello-world](../examples/01-hello-world/)

```python
from soorma import Worker

worker = Worker(name="my-worker", capabilities=["greeting"])

@worker.on_event("greeting.request")
async def handle(event, context):
    # Process event
    await context.bus.publish("greeting.response", ...)
```

**Characteristics:**
- Stateless or manages own state
- Reacts to events
- No coordination with other agents
- Simple to implement and understand

**Best for:**
- Data processing pipelines
- Notifications and alerts
- Simple CRUD operations
- Webhook handlers

---

### 2. Trinity Pattern (Planner-Worker-Tool)

**Use when:** Goal-driven task decomposition with clear steps

**Complexity:** ⭐⭐ Intermediate

**Example:** [08-planner-worker-basic](../examples/08-planner-worker-basic/) (coming in Phase 4)

**Architecture:**
- **Planner:** Decomposes goals into actionable steps
- **Worker:** Executes specific tasks/capabilities
- **Tool:** Provides reusable, stateless operations

**Characteristics:**
- Clear separation of concerns (strategy vs execution vs utilities)
- Planner handles workflow orchestration
- Workers handle domain-specific execution
- Tools provide shared, reusable capabilities
- Explicit task coordination

**Best for:**
- Multi-step workflows with predictable patterns
- Task assignment to specialized workers
- Reusable operations that multiple agents need
- When control flow is well-understood
- Applications requiring auditability and observability

**Note:** The Plan abstraction (state machine for workflow tracking) will be defined with the State Tracker service. See refactor plan for details.

---

### 3. Autonomous Choreography Pattern

**Use when:** Complex, adaptive workflows where LLM decides next steps

**Complexity:** ⭐⭐⭐ Advanced

**Example:** [09-app-research-advisor](../examples/09-app-research-advisor/) (coming in Phase 4)

**How it works:**
1. Planner receives goal event (e.g., `research.goal`)
2. LLM discovers available events from Registry
3. LLM reasons about next action based on:
   - Current goal and context
   - Workflow state (from Working Memory)
   - Available capabilities (discovered events)
   - Previous actions taken
4. Planner publishes chosen event (e.g., `web.search.request`)
5. Worker responds with results event (e.g., `web.search.complete`)
6. Planner receives results, reasons about next step, repeats

**Event-driven flow:**
- No loops - each step is triggered by incoming events
- State tracked in Working Memory and Plan (state machine)
- Circuit breaker (max actions) prevents runaway workflows
- LLM adapts based on results from each step

**Characteristics:**
- No predefined workflow - LLM decides dynamically
- Events discovered at runtime from Registry
- Self-adapting to available capabilities
- Fully event-driven (no while loops)
- Circuit breaker prevents infinite action sequences

**Best for:**
- Unpredictable workflows where steps depend on intermediate results
- Complex decision trees with many possible paths
- Adaptive systems that evolve with available capabilities
- When requirements change frequently
- Research, exploration, and creative tasks

---

## Autonomous Choreography (Key Innovation)

Traditional agent systems hardcode workflow logic: "after step A, do step B." This is brittle and requires code changes when workflows evolve.

### The Soorma Approach

**1. Registration**
Agents register events they consume/produce with the Registry, including rich metadata:
```python
from soorma_common import EventDefinition, EventTopic

RESEARCH_EVENT = EventDefinition(
    event_name="content.research",
    topic=EventTopic.ACTION_REQUESTS,
    description="Research a topic and gather information",
    payload_schema={...}
)
```

**2. Discovery**
Planner queries Registry to find available events at runtime:
```python
from soorma.ai.event_toolkit import EventToolkit

events = await toolkit.discover_actionable_events(
    topic="action-requests"
)
# Returns all events with metadata
```

**3. Reasoning**
LLM analyzes event metadata to understand capabilities:
```python
prompt = f"""
Available Events:
{format_events(events)}

Current State:
{workflow_state}

Goal: {user_goal}

Decide the next action to progress toward the goal.
"""
```

**4. Decision**
LLM selects appropriate event and constructs payload:
```python
response = await llm.reason(prompt)
# Returns: {"event": "content.research", "payload": {...}}
```

**5. Execution**
Event is published, triggering the next agent:
```python
await context.bus.publish(
    event_type=response["event"],
    topic="action-requests",
    data=response["payload"]
)
```

### Benefits

- **Dynamic Adaptation:** Add new agents without changing orchestration code
- **Runtime Discovery:** Agents discover capabilities as they become available
- **LLM Reasoning:** System adapts to context and chooses optimal path
- **No Hardcoding:** Workflows emerge from agent decisions, not predefined rules
- **Evolutionary:** System improves as you add more specialized agents

### Example

See [examples/research-advisor](../examples/research-advisor/) for complete implementation.

---

## Circuit Breakers & Safety

Autonomous systems need safeguards to prevent runaway behavior.

### Action Limits

Prevent infinite loops by limiting total actions:

```python
MAX_TOTAL_ACTIONS = 10

if len(action_history) >= MAX_TOTAL_ACTIONS:
    logger.warning("Action limit reached, forcing completion")
    return force_completion()
```

**Implementation:**
- Track every action (event published) in workflow state
- Set reasonable limits based on workflow complexity
- Force graceful completion when limit reached
- Log warning for debugging

### Vague Result Detection

Catch when LLM returns meta-descriptions instead of actual content:

```python
vague_indicators = ["draft is ready", "already prepared", "content is complete"]

if any(indicator in result.lower() for indicator in vague_indicators):
    # Use actual content from working memory instead
    result = workflow_state["draft"]["draft_text"]
```

**Why needed:**
- LLMs sometimes say "content is ready" instead of returning content
- Prevents publishing empty or meta results
- Ensures quality control on outputs

### Timeout Handling (Planned)

Future State Tracker service will provide:
- Detect stalled workflows (no progress in N minutes)
- Automatic retry of failed events
- Human intervention triggers
- Observability dashboards
- Workflow replay capabilities

### Best Practices

✅ **Do:**
- Set action limits appropriate for your workflow
- Log all circuit breaker activations
- Test edge cases (infinite loops, failures)
- Monitor workflow completion rates
- Implement graceful degradation

❌ **Don't:**
- Remove circuit breakers "because they're annoying"
- Set limits too high (defeats purpose)
- Ignore circuit breaker warnings in logs
- Assume LLMs always behave perfectly

**Note:** Implementation details (ChoreographyPlanner SDK class, Plan state machine) will be defined in Phase 4. See [refactor plan](../EXAMPLES_REFACTOR_PLAN.md) for roadmap.

---

### 4. Saga Pattern (Distributed Transactions)

**Use when:** Multi-step transactions that need rollback

**Complexity:** ⭐⭐⭐ Advanced

**Example:** Coming in future release

```python
# Coordinator tracks saga state
@worker.on_event("order.create")
async def start_saga(event, context):
    saga_id = generate_id()
    
    # Step 1: Reserve inventory
    await publish("inventory.reserve", saga_id=saga_id)
    
    # If any step fails, compensate
    @worker.on_event("inventory.failed")
    async def compensate(event, context):
        # Undo previous steps
        await publish("order.cancel", saga_id=saga_id)
```

**Characteristics:**
- Manages distributed transactions
- Compensation logic for failures
- State tracking across services
- Eventually consistent

**Best for:**
- Order processing
- Booking systems
- Financial transactions
- Multi-service updates

---

## Plans and Sessions: Workflow Organization

### Conceptual Model

The Memory Service provides two organizational constructs for structuring multi-agent workflows:

| Concept | Purpose | Scope | Typical Use |
|---------|---------|-------|-------------|
| **Plan** | Individual work unit/workflow execution | Single goal execution | Chat conversation, research task, document generation |
| **Session** | Container grouping related plans | Multi-plan conversation | Multi-turn project, extended research session, user journey |

### Plans: The Execution Unit

**Plans** are the primary organizational unit in Soorma. Each plan represents a single workflow execution with its own:
- Unique `plan_id` (the business identifier)
- Goal event and goal data (what the plan aims to achieve)
- Status (running, completed, failed, paused)
- Working memory state (plan-scoped key-value storage)

**Data Model:**
```python
class Plan:
    plan_id = String(100)          # Primary identifier
    tenant_id = UUID               # Multi-tenant isolation
    user_id = UUID                 # User/agent ownership
    session_id = String(100)       # OPTIONAL - links to session
    goal_event = String(255)       # What the plan aims to achieve
    goal_data = JSON               # Parameters for the goal
    status = String(50)            # running/completed/failed/paused
    parent_plan_id = String(100)   # For hierarchical plans
    created_at, updated_at
```

**Key Characteristics:**
- ✅ **Working memory is plan-scoped** - All temporary state is isolated per plan
- ✅ **Plans can exist independently** - `session_id` is optional
- ✅ **Plans can be hierarchical** - `parent_plan_id` creates plan trees
- ✅ **Each plan has a lifecycle** - Track status from creation to completion

### Sessions: The Grouping Container

**Sessions** are optional organizational metadata that group related plans together. A session represents a higher-level conversation or interaction boundary.

**Data Model:**
```python
class Session:
    session_id = String(100)       # Business identifier
    tenant_id = UUID               # Multi-tenant isolation
    user_id = UUID                 # User ownership
    name = String(255)             # Optional human-readable name
    session_metadata = JSON        # Flexible metadata
    last_interaction = DateTime    # Auto-updated timestamp
    created_at
```

**Key Characteristics:**
- ✅ **One session can contain multiple plans** - Group related work units
- ✅ **Sessions don't store data directly** - They're organizational metadata
- ✅ **Sessions track interaction time** - `last_interaction` auto-updates
- ✅ **Plans can exist without sessions** - Sessions are optional

### Relationship to Memory Types

**Critical Understanding:**

```
Session (optional container)
  └─ Plan 1 (work unit)
      ├─ Working Memory (plan-scoped state)
      ├─ Episodic Memory (agent_id + user_id scoped)
      └─ Semantic Memory (user_id scoped)
  └─ Plan 2 (work unit)
      ├─ Working Memory (different plan = different state)
      ├─ Episodic Memory (shared across plans)
      └─ Semantic Memory (shared across plans)
```

**Important:** Sessions don't directly contain memories:
- **Working Memory** = Scoped to `plan_id` (not session_id)
- **Episodic Memory** = Scoped to `agent_id + user_id` (crosses plans/sessions)
- **Semantic Memory** = Scoped to `user_id` (crosses plans/sessions)

### When to Use Plans vs Sessions

#### Use Plans Alone When:

✅ Simple single-conversation chatbots

✅ One-off task execution

✅ Independent workflow instances

✅ No need to group related work

**Example: Simple Chatbot**
```python
# Each conversation = one plan
plan_id = str(uuid.uuid4())
state = WorkflowState(context.memory, plan_id, tenant_id, user_id)

# Store conversation state
await state.set("history", messages)
await state.set("user_preferences", prefs)
```

#### Use Plans + Sessions When:

✅ Multi-turn research projects (multiple plans per project)

✅ Complex user journeys (multiple related workflows)

✅ Need to group and query related work units

✅ Long-running interactions with multiple sub-goals

**Example: Research Project**
```python
# Create session for the project
session_id = "research-project-123"

# Create multiple plans within the session
plan1_id = str(uuid.uuid4())
await create_plan(plan1_id, session_id=session_id, goal="literature_review")

plan2_id = str(uuid.uuid4())
await create_plan(plan2_id, session_id=session_id, goal="data_analysis")

plan3_id = str(uuid.uuid4())
await create_plan(plan3_id, session_id=session_id, goal="write_report")

# Each plan has its own working memory
state1 = WorkflowState(context.memory, plan1_id, tenant_id, user_id)
state2 = WorkflowState(context.memory, plan2_id, tenant_id, user_id)

# But they share episodic and semantic memory via user_id
```

### Design Patterns with Plans

#### Pattern 1: Simple Chat (Plan Only)
```python
# Each conversation is a plan
plan_id = f"chat-{user_id}-{timestamp}"

# Store conversation state in working memory
state = WorkflowState(context.memory, plan_id, tenant_id, user_id)
await state.set("history", messages)

# Log interactions in episodic memory
await context.memory.log_interaction(
    agent_id="chatbot",
    role="user",
    content=message,
    user_id=user_id,
    metadata={"plan_id": plan_id}
)
```

#### Pattern 2: Multi-Step Workflow (Plan with Substeps)
```python
# Main plan
main_plan_id = str(uuid.uuid4())

# Sub-plans (hierarchical)
plan1 = await create_plan(
    plan_id=str(uuid.uuid4()),
    parent_plan_id=main_plan_id,
    goal="step1"
)

# Each sub-plan gets its own working memory
state1 = WorkflowState(context.memory, plan1.plan_id, tenant_id, user_id)
```

#### Pattern 3: Project with Multiple Goals (Session + Plans)
```python
# Create session
session_id = "project-789"
await create_session(session_id, name="Q1 Product Launch")

# Create plans for each phase
research_plan = await create_plan(
    session_id=session_id,
    goal_event="research.market"
)

design_plan = await create_plan(
    session_id=session_id,
    goal_event="design.prototype"
)

# Later: Query all work in this project
plans = await list_plans(session_id=session_id)
```

### Best Practices

1. **Default to plans alone** - Only introduce sessions when you need grouping
2. **Use plan_id for working memory** - Never try to store state at session level
3. **Link episodic memory to plans** - Include `plan_id` in metadata for traceability
4. **Clean up completed plans** - Delete working memory when workflows finish
5. **Update plan status** - Track lifecycle (running → completed/failed)
6. **Use parent_plan_id for hierarchy** - Better than sessions for nested workflows

### Common Mistakes

❌ **Trying to store data in sessions**
```python
# WRONG: Sessions don't have data storage
session.data = {"important": "stuff"}  # This doesn't exist!
```

✅ **Store data in plan working memory**
```python
# RIGHT: Use plan-scoped working memory
state = WorkflowState(context.memory, plan_id, tenant_id, user_id)
await state.set("important", "stuff")
```

❌ **Confusing session_id with plan_id**
```python
# WRONG: Working memory needs plan_id, not session_id
state = WorkflowState(context.memory, session_id, tenant_id, user_id)
```

✅ **Use plan_id for working memory**
```python
# RIGHT: Working memory is plan-scoped
state = WorkflowState(context.memory, plan_id, tenant_id, user_id)
```

### Security and Isolation

Both plans and sessions enforce multi-tenant isolation:

```python
# Unique constraints ensure no collisions
(tenant_id, plan_id) = UNIQUE      # Plans isolated per tenant
(tenant_id, session_id) = UNIQUE   # Sessions isolated per tenant

# All queries filtered by tenant_id + user_id
plans = await list_plans(tenant_id=tenant_id, user_id=user_id)
```

**Row Level Security (RLS):** PostgreSQL RLS policies enforce data isolation at the database level.

---

## Choosing a Pattern

### Agent Orchestration Patterns

| Your Requirement | Use This Pattern |
|------------------|------------------|
| Simple event reaction | Worker Pattern |
| Multi-step with known sequence | Trinity Pattern |
| Complex, adaptive workflow | Autonomous Choreography |
| Distributed transaction | Saga Pattern |

### Memory Patterns

For memory-related decisions, see [Memory Patterns](./MEMORY_PATTERNS.md):
- **Semantic Memory** - Long-term knowledge storage (RAG)
- **Working Memory** - Plan-scoped shared state
- **Episodic Memory** - Conversation history

The Memory Patterns guide includes comprehensive examples, comparison tables, and decision trees.

---

## Related Documentation

- [Architecture](../ARCHITECTURE.md) - Platform services and infrastructure
- [Developer Guide](./DEVELOPER_GUIDE.md) - Development workflows and testing
- [Event Patterns](./EVENT_PATTERNS.md) - Event-driven communication
- [Memory Patterns](./MEMORY_PATTERNS.md) - Memory usage guide
- [Examples](../examples/) - Working implementations

---

**Status Note:** This document will be expanded as more patterns are implemented in examples.
