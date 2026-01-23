# Examples & Documentation Refactor Plan

**Status:** 🟡 In Progress  
**Last Updated:** January 22, 2026  
**Owner:** @amit

---

## 1. Problem Statement

The current examples and documentation in `soorma-core` suffer from several issues:

### 1.1 Examples Issues

| Issue | Description |
|-------|-------------|
| **Mixed Concerns** | `hello-world` and `research-advisor` try to demonstrate multiple concepts at once |
| **Boilerplate Overload** | `research-advisor/planner.py` has ~485 lines of LLM reasoning code that should be SDK methods |
| **Missing Focused Examples** | No isolated examples for: Events, Memory, Structured Events, Tool Discovery |
| **Complexity Jump** | Gap between `hello-world` (simple decorators) and `research-advisor` (full autonomous choreography) |

### 1.2 Documentation Issues

| Issue | Description |
|-------|-------------|
| **Mixed Content** | `ARCHITECTURE.md` conflates platform services with agent design patterns |
| **No Pattern Library** | Developers can't easily find "how to do X" patterns |
| **Blog Disconnect** | Blog posts reference concepts without clear mapping to examples |

---

## 2. Goals

1. **Progressive Learning Path**: Examples that build on each other from simple → complex
2. **One Example = One Concept**: Each example focuses on demonstrating one capability clearly
3. **SDK-First**: Move reusable logic from examples into SDK, reducing boilerplate
4. **AI-Assistant Friendly**: Documentation structured so Copilot/Cursor can guide developers

---

## 3. Proposed Example Structure

```
examples/
├── README.md                          # Example index with learning path
│
├── 01-hello-world/                    # Basic agent lifecycle
│   ├── README.md
│   ├── worker.py                      # Simplest possible worker
│   └── client.py                      # Event publishing
│
├── 02-events-simple/                  # Simple event pub/sub
│   ├── README.md
│   ├── publisher.py                   # Publish events
│   └── subscriber.py                  # Subscribe and react
│
├── 03-events-structured/              # Rich event metadata for LLM reasoning
│   ├── README.md
│   ├── events.py                      # Event definitions with schemas
│   ├── registry_setup.py              # Register events with metadata
│   └── llm_event_selector.py          # LLM chooses events based on metadata
│
├── 04-memory-semantic/                # RAG / Knowledge storage
│   ├── README.md
│   ├── store_knowledge.py             # Store facts with embeddings
│   └── search_knowledge.py            # Semantic search
│
├── 05-memory-working/                 # Plan-scoped shared state
│   ├── README.md
│   ├── planner.py                     # Store state with plan_id
│   └── worker.py                      # Read state from same plan_id
│
├── 06-memory-episodic/                # Conversation history / audit trail
│   ├── README.md
│   └── conversation_agent.py          # Log interactions, recall history
│
├── 07-tool-discovery/                 # Dynamic capability discovery
│   ├── README.md
│   ├── tool_provider.py               # Register tool capabilities
│   └── worker_with_tools.py           # Worker that discovers and uses tools dynamically
│
├── 08-planner-worker-basic/           # Trinity pattern (no LLM orchestration)
│   ├── README.md
│   ├── planner.py                     # Goal → Plan → Tasks
│   ├── worker.py                      # Task execution
│   └── client.py
│
├── 09-app-research-advisor/           # Full application: Autonomous Choreography pattern
│   ├── README.md                      # Application overview
│   ├── ARCHITECTURE.md                # Deep dive on Autonomous Choreography pattern
│   ├── planner.py                     # Uses SDK's ChoreographyPlanner
│   ├── researcher.py                  # Web research worker
│   ├── advisor.py                     # Content drafting worker
│   ├── validator.py                   # Fact-checking worker
│   └── client.py
│
└── 10-multi-turn-conversation/        # Stateful conversations
    ├── README.md
    ├── planner.py                     # Handles follow-ups
    └── client.py                      # Multi-turn interaction
```

---

## 4. SDK Enhancements Required

The `research-advisor` planner has significant boilerplate that should become SDK features:

### 4.1 ChoreographyPlanner Class

```python
# Current (boilerplate in example)
async def get_next_action(trigger_context, workflow_data, available_events, context):
    prompt = f"""You are an autonomous orchestrator agent..."""
    response = completion(model=get_llm_model(), messages=[...])
    return json.loads(response.choices[0].message.content)

# Proposed (SDK method)
from soorma.ai import ChoreographyPlanner
from soorma.ai.decisions import PlannerDecision, PlanAction

planner = ChoreographyPlanner(
    name="orchestrator",
    max_actions=10,  # circuit breaker
    reasoning_model="gpt-4o"
)

@planner.on_goal("research.goal")
async def handle_goal(goal, context):
    # SDK handles: event discovery, LLM reasoning, payload construction
    # Returns a typed Pydantic object, not a raw dict
    decision: PlannerDecision = await planner.reason_next_action(
        trigger=f"New goal: {goal.data['objective']}",
        context=context
    )
    
    # SDK validates event exists in Registry BEFORE publishing
    # Prevents "hallucinated events" - LLM can't publish non-existent events
    await planner.execute_decision(decision, context)
```

#### 4.1.1 PlannerDecision Type Safety

```python
# soorma/ai/decisions.py
from enum import Enum
from pydantic import BaseModel
from typing import Optional, Any

class PlanAction(str, Enum):
    PUBLISH_EVENT = "publish"    # Trigger next agent
    COMPLETE = "complete"        # Goal fulfilled, deliver result
    WAIT = "wait"                # Need more info, pause

class PlannerDecision(BaseModel):
    action: PlanAction
    event_name: Optional[str] = None      # Must exist in Registry if action=PUBLISH_EVENT
    payload: Optional[dict[str, Any]] = None
    result: Optional[str] = None          # Final output if action=COMPLETE
    reasoning: str                         # LLM's explanation (for audit trail)
    trace_id: Optional[str] = None        # Correlation ID for State Tracker (future)
    plan_id: Optional[str] = None         # Links decision to originating plan

# In execute_decision():
if decision.action == PlanAction.PUBLISH_EVENT:
    # Validate against discovered events (not just Registry - already filtered)
    if decision.event_name not in [e["name"] for e in discovered_events]:
        raise InvalidEventError(f"Event '{decision.event_name}' not in discovered events")
    # Proceed to publish...
```

### 4.2 WorkflowState Helper

```python
# Current (manual working memory management)
workflow_state = await context.memory.retrieve("workflow_state", plan_id=plan_id) or {}
action_history = workflow_state.get('action_history', [])
action_history.append(event_name)
workflow_state['action_history'] = action_history
await context.memory.store("workflow_state", workflow_state, plan_id=plan_id)

# Proposed (SDK helper)
from soorma.workflow import WorkflowState

state = WorkflowState(context, plan_id)
await state.record_action(event_name)
await state.set("research", research_data)
history = await state.get_action_history()
```

### 4.3 EventDiscovery Helpers

```python
# Proposed addition to EventToolkit
async with EventToolkit(context.registry.base_url) as toolkit:
    # Already exists
    events = await toolkit.discover_actionable_events(topic="action-requests")
    
    # New: Format for LLM with enhanced metadata
    llm_prompt = toolkit.format_for_llm_selection(events)
    
    # New: Parse LLM response back to event
    selected_event, payload = toolkit.parse_llm_selection(llm_response, events)
```

### 4.4 LLM Event Selection Utilities

> **Background**: Examples `03-events-structured` and `research-advisor` contain ~100+ lines of similar boilerplate for:
> - Discovering events from Registry
> - Formatting events for LLM prompts  
> - Calling LLM with structured prompts
> - Validating LLM-selected events
> - Publishing selected events
>
> This code should move to SDK utilities with customizable templates.

```python
# Current (boilerplate in examples/03-events-structured/llm_event_selector.py)
async def discover_routing_events(context) -> list[dict]:
    async with EventToolkit(context.registry.base_url) as toolkit:
        events = await toolkit.discover_actionable_events(topic="action-requests")
        return events

def format_events_for_llm(events: list[dict]) -> str:
    formatted = []
    for i, event in enumerate(events, 1):
        metadata = event.get("metadata", {})
        formatted.append(f"{i}. **{event['name']}**\n   Description: {event['description']}\n")
    return "\n".join(formatted)

async def select_event_with_llm(data: dict, events: list[dict]) -> dict:
    prompt = f"""Analyze and select best event..."""
    response = completion(model=model, messages=[...])
    return json.loads(response.choices[0].message.content)

# Proposed (SDK utilities)
from soorma.ai import EventSelector

# Agent provides domain-specific prompt template
ROUTING_PROMPT = """
You are a support ticket router. Analyze the ticket and select routing.

TICKET: {{ticket_data}}

AVAILABLE ROUTES: {{events}}

Select the best routing event and explain why.
"""

selector = EventSelector(
    context=context,
    topic="action-requests",
    prompt_template=ROUTING_PROMPT,  # Agent customization point
    model=os.getenv("LLM_MODEL", "gpt-4o-mini")
)

@worker.on_event("ticket.created")
async def route_ticket(event, context):
    # SDK handles: discovery, formatting, LLM call, validation
    decision = await selector.select_event(
        state={"ticket_data": event.data},
        filters={"category": "routing"}  # Optional event filtering
    )
    
    # SDK validates event exists before publishing
    await selector.publish_decision(decision, context)
```

**Benefits**:
- **Reduces boilerplate**: ~150 lines → ~20 lines in examples
- **Customizable**: Agents specify domain logic via prompt templates
- **Type-safe**: Returns structured `EventDecision` (not raw dict)
- **Validated**: SDK ensures LLM can't hallucinate non-existent events
- **Maintained**: Bug fixes benefit all agents using pattern
- **Consistent**: Same LLM selection pattern across all agents

**EventDecision Type**:
```python
from pydantic import BaseModel

class EventDecision(BaseModel):
    event_name: str          # Validated against discovered events
    payload: dict[str, Any]  # Validated against event schema
    reasoning: str           # LLM explanation for audit
    confidence: float        # Optional: LLM confidence score
```

---

## 5. Documentation Restructure

### 5.1 Split ARCHITECTURE.md

| New File | Content |
|----------|---------|
| `ARCHITECTURE.md` | Platform services only (Registry, Event Service, Memory, Gateway) |
| `docs/DESIGN_PATTERNS.md` | Agent patterns (Trinity, Choreography, Event-Driven) |
| `docs/DEVELOPER_GUIDE.md` | DX sections (Solo Creator, Integration Developer) |
| `docs/MEMORY_PATTERNS.md` | When to use Semantic vs Working vs Episodic |
| `docs/EVENT_PATTERNS.md` | Simple events vs Structured events with LLM reasoning |

### 5.2 Create Pattern Catalog (AI-Assistant Friendly)

```markdown
<!-- docs/PATTERNS.md -->
# Pattern Catalog

## When to Use Each Pattern

| I want to... | Use Pattern | See Example |
|--------------|-------------|-------------|
| React to simple events | Event Subscriber | `02-events-simple` |
| Let LLM choose next action | Structured Events + LLM | `03-events-structured` |
| Store facts for RAG | Semantic Memory | `04-memory-semantic` |
| Share state across agents in a workflow | Working Memory | `05-memory-working` |
| Log conversation history | Episodic Memory | `06-memory-episodic` |
| Decompose goals into tasks | Planner-Worker | `08-planner-worker-basic` |
| Fully autonomous orchestration | Autonomous Choreography | `09-app-research-advisor` |
```

---

## 6. Action Items

### Phase 1: Foundation Examples ✅ COMPLETED
- [x] Create `examples/README.md` with learning path overview
- [x] Update `01-hello-world/` to use correct topics (action-requests/action-results)
- [x] Update `02-events-simple/` to use correct topics (business-facts for domain events)
- [x] Refactor `03-events-structured/` with EventDefinition pattern:
  - [x] Created `events.py` with Pydantic models and EventDefinition objects
  - [x] Split into `llm_utils.py` (educational boilerplate) and `ticket_router.py` (agent logic)
  - [x] Removed `registry_setup.py` (SDK auto-registration)
  - [x] Updated README with EventDefinition pattern documentation
- [x] Created `docs/TOPICS.md` documenting all 8 Soorma topics
- [x] Updated `docs/EVENT_PATTERNS.md` with topics section
- [x] Updated all example READMEs to reflect correct topics and patterns

### Phase 2: SDK Primitives ✅ INTEGRATED
> **Status:** SDK conveniences integrated into overall Soorma Core refactoring plan.  
> **See:** [docs/refactoring/README.md](docs/refactoring/README.md) Stages 2-5
>
> The following SDK primitives are now part of the main refactoring:
> - RF-SDK-014: WorkflowState helper (Stage 2)
> - RF-SDK-015: PlannerDecision types (Stage 4)
> - RF-SDK-016: ChoreographyPlanner class (Stage 4)
> - RF-SDK-017: EventSelector utility (Stage 5)
> - RF-SDK-018: EventToolkit.format_for_llm_selection() (Stage 5)
>
> **Examples refactoring will resume with Phase 3 after SDK implementation completes.**

### Phase 3: Memory Examples ✅ COMPLETED
> **Depends on:** Phase 2 (`WorkflowState` helper)

- [x] Create `04-memory-semantic/` (RAG pattern)
- [x] Create `05-memory-working/` (uses `WorkflowState` helper)
- [x] Create `06-memory-episodic/` (conversation history)
- [x] Create `docs/MEMORY_PATTERNS.md`

### Phase 4: Advanced Examples (Week 2-3)
> **Depends on:** Phase 2 (`ChoreographyPlanner` class)

- [ ] Create `07-tool-discovery/` with `worker_with_tools.py`
- [ ] Create `08-planner-worker-basic/` (refactored from hello-world)
- [ ] Refactor `09-app-research-advisor/` using `ChoreographyPlanner` (renamed from research-advisor)
- [ ] Create `10-multi-turn-conversation/`

### Phase 5: Documentation & AI Tooling (Week 3)
- [ ] Create `.cursorrules` file for AI assistant guidance (see Section 6.1)
- [ ] Split `ARCHITECTURE.md` into focused documents
- [ ] Create `docs/PATTERNS.md` pattern catalog
- [ ] Create `docs/DESIGN_PATTERNS.md`
- [ ] Update `README.md` with new structure
- [ ] Update blog posts to reference specific examples

### 6.1 `.cursorrules` for AI Assistant Guidance

Create a root-level `.cursorrules` file to explicitly guide AI assistants:

```markdown
# Soorma Development Rules for AI Assistants

## Code Generation Guidelines

When generating Soorma agent code, follow these patterns:

### For a simple Worker agent:
- Reference: `examples/01-hello-world/worker.py`
- Use `@worker.on_event()` decorator pattern

### For event publishing/subscribing:
- Simple events: `examples/02-events-simple/`
- Events with LLM selection: `examples/03-events-structured/`

### For Memory operations:
- Semantic (RAG): `examples/04-memory-semantic/`
- Working (plan state): `examples/05-memory-working/` - use `WorkflowState` helper
- Episodic (history): `examples/06-memory-episodic/`

### For Tool discovery:
- Reference: `examples/07-tool-discovery/worker_with_tools.py`
- Tools are capabilities attached to Workers

### For Planner-Worker orchestration:
- Without LLM: `examples/08-planner-worker-basic/`
- With LLM (autonomous): `examples/09-app-research-advisor/`
- Use `ChoreographyPlanner` class for autonomous orchestration

### For multi-turn conversations:
- Reference: `examples/10-multi-turn-conversation/`

## Architecture References
- Platform services: `ARCHITECTURE.md`
- Design patterns: `docs/DESIGN_PATTERNS.md`
- Memory patterns: `docs/MEMORY_PATTERNS.md`
- Pattern catalog: `docs/PATTERNS.md`
```

---

## 7. Example Template

Each example should follow this template:

```markdown
# Example Name

**Concepts:** Event Publishing, Memory Retrieval  
**Difficulty:** Beginner | Intermediate | Advanced  
**Prerequisites:** `01-hello-world`

## What You'll Learn
- Bullet point of key takeaways

## The Pattern
Brief explanation of when to use this pattern.

## Code Walkthrough
- Step-by-step explanation of the code.

## Running the Example
- Step-by-step commands

## Key Takeaways
- What to remember
- Common mistakes to avoid

## Next Steps
- Link to next example in learning path
```

---

## 8. Success Criteria

- [ ] Developer can complete learning path in 2 hours
- [ ] Each example runs independently with `soorma dev`
- [ ] AI assistants (Copilot/Cursor) can recommend correct example for a task
- [ ] `research-advisor` planner code is <100 lines (vs current 485)
- [ ] Blog posts link to specific examples demonstrating each concept

---

## 9. Notes & Decisions

### Why numbered prefixes?
- Creates clear learning progression
- File browsers show examples in order
- AI assistants understand the hierarchy

### Why separate Memory examples?
- CoALA framework has 3 distinct memory types
- Developers often conflate them
- Focused examples prevent misuse

### What about the existing examples?
- `hello-world/` → Refactor into `01-hello-world/` and `08-planner-worker-basic/`
- `research-advisor/` → Refactor into `09-app-research-advisor/` with SDK helpers

### Why `09-app-*` naming?
- "Autonomous Choreography" is the *pattern*
- "Research Advisor" is the *application* demonstrating the pattern
- Users looking for "the big example" can find it easily
- Future apps can follow: `09-app-code-reviewer/`, `09-app-support-agent/`

### State Tracker Integration (Future)
- State Tracker service will be added to soorma-core later
- SDK has placeholder hooks (`_register_plan`, `_report_decision`) ready to wire up
- `trace_id` in `PlannerDecision` enables correlation across distributed agents
- State Tracker documentation will be separate (observability focus)

### Plan Abstraction (State Machine)
**Status:** Design phase - to be implemented with State Tracker

The `Plan` concept will represent a dynamically generated state machine for workflow tracking:

```python
# Conceptual design (not yet implemented)
class Plan:
    """State machine representing workflow execution."""
    plan_id: str
    goal: str
    state: PlanState  # ACTIVE, COMPLETED, FAILED, PAUSED
    steps: List[PlanStep]  # Generated by LLM reasoning
    current_step: int
    metadata: Dict[str, Any]
    
# Generated by Planner based on:
# 1. Goal description
# 2. Discovered events/capabilities from Registry
# 3. LLM reasoning about optimal workflow
# 4. Historical patterns (from memory)

# State Tracker will:
# - Persist plan state
# - Track step execution
# - Enable observability ("what is this plan doing?")
# - Support pause/resume
# - Provide audit trail
```

**Design Principles:**
- Plans are LLM-generated, not hardcoded
- Steps adapt to available capabilities
- State machine enables pause/resume
- Integration with Working Memory for step data
- Observable via State Tracker UI

**Will be defined during Phase 4/5 when implementing:**
- `08-planner-worker-basic` example
- State Tracker service
- Plan lifecycle events (plan.created, plan.step_completed, etc.)

---

## Changelog

| Date | Change |
|------|--------|
| 2026-01-06 | Initial plan created |
| 2026-01-06 | Swapped Phase 2/3 order (SDK primitives before examples that use them) |
| 2026-01-06 | Added `.cursorrules` action item for AI assistant guidance |
| 2026-01-06 | Refined `ChoreographyPlanner` with typed `PlannerDecision` + Registry validation |
| 2026-01-06 | Renamed `tool_consumer.py` → `worker_with_tools.py` for clarity |
| 2026-01-06 | Renamed `09-autonomous-choreography/` → `09-app-research-advisor/` (pattern vs application) |
| 2026-01-06 | Added `trace_id` + `plan_id` to `PlannerDecision` for State Tracker correlation |
| 2026-01-06 | Added State Tracker placeholder hooks to Phase 2 SDK primitives |
| 2026-01-06 | **Phase 1 COMPLETED**: Foundation examples refactored with correct topics and EventDefinition pattern |
| 2026-01-21 | **Phase 3 COMPLETED**: Memory examples (semantic, episodic, working) and MEMORY_PATTERNS.md implemented |
