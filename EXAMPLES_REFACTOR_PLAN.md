# Examples & Documentation Refactor Plan

**Status:** 🟡 In Progress  
**Last Updated:** January 6, 2026  
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

### Phase 1: Foundation Examples (Week 1)
- [ ] Create `examples/README.md` with learning path overview
- [ ] Extract and simplify `01-hello-world/` (remove unnecessary complexity)
- [ ] Create `02-events-simple/` (pub/sub without LLM)
- [ ] Create `03-events-structured/` (events with rich metadata for LLM)

### Phase 2: SDK Primitives (Week 1 - parallelize with Phase 1)
> **Rationale:** Build SDK helpers first so examples can use them cleanly. Avoids "write it hard way then refactor" double work.

- [ ] Implement `PlannerDecision` and `PlanAction` types in `soorma/ai/decisions.py`
  - Include `trace_id` and `plan_id` fields for future State Tracker correlation
- [ ] Implement `ChoreographyPlanner` class with Registry validation
  - Add placeholder hook: `async def _register_plan(self, goal, context): pass`
  - Add placeholder hook: `async def _report_decision(self, decision, context): pass`
  - These no-ops will be wired to State Tracker later without breaking API
- [ ] Implement `WorkflowState` helper in `soorma/workflow.py`
- [ ] Add `format_for_llm_selection()` to EventToolkit
- [ ] Update SDK CHANGELOG

### Phase 3: Memory Examples (Week 2)
> **Depends on:** Phase 2 (`WorkflowState` helper)

- [ ] Create `04-memory-semantic/` (RAG pattern)
- [ ] Create `05-memory-working/` (uses `WorkflowState` helper)
- [ ] Create `06-memory-episodic/` (conversation history)
- [ ] Create `docs/MEMORY_PATTERNS.md`

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
