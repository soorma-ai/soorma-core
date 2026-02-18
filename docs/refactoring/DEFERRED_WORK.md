# Deferred Work Tracking

**Purpose:** Track refactoring tasks deferred to future stages to prevent them from being lost.  
**Last Updated:** February 17, 2026

---

## Overview

During pre-launch refactoring, some features are intentionally deferred to:
- Focus on high-impact MVP features first
- Avoid scope creep and timeline delays
- Allow learning from usage patterns before over-engineering

This document tracks deferred items with clear rationale and target stages.

---

## Stage 4: Planner Model Deferrals (February 2026)

### RF-SDK-017: EventSelector Utility

**Description:** LLM-based event selection utility for intelligent routing.

**Original Spec:** [sdk/07-DISCOVERY.md](sdk/07-DISCOVERY.md)

**Use Case:**
```python
# Defer this pattern to Stage 5
from soorma.ai.selection import EventSelector

selector = EventSelector(
    context=context,
    topic="action-requests",
    prompt_template=ROUTING_PROMPT,
    model="gpt-4o-mini",
)

@worker.on_task("ticket.created")
async def route_ticket(task, context):
    decision = await selector.select_event(
        state={"ticket_data": task.data}
    )
    await selector.publish_decision(decision)
```

**Reason for Deferral:**
- ChoreographyPlanner is higher priority (87.5% code reduction in planners)
- EventSelector is more niche (intelligent routing use case)
- Can be built later using ChoreographyPlanner patterns as reference

**Current Status:**
- ✅ **EventToolkit exists** - provides discovery and formatting (50% done)
- ❌ **EventSelector missing** - needs LLM integration and selection logic

**Target Stage:** Stage 5 (Discovery)

**Estimated Effort:** 0.5-1 day (reduced from 1-2 days due to EventToolkit foundation)

**Dependencies:**
- ✅ Registry discovery API (already exists)
- ✅ EventToolkit (already exists - provides discovery and formatting)
- 🟡 PlannerDecision types (Stage 4 deliverable - can reuse pattern for EventDecision)

**Implementation Strategy:**
```python
# EventSelector can leverage existing EventToolkit for discovery/formatting
from soorma.ai.event_toolkit import EventToolkit
from litellm import completion

class EventSelector:
    def __init__(self, context, topic, prompt_template, model="gpt-4o-mini"):
        self.toolkit = EventToolkit(registry_client=context.registry)
        self.topic = topic
        self.prompt_template = prompt_template
        self.model = model
    
    async def select_event(self, state: Dict[str, Any]) -> EventDecision:
        # 1. Discover using EventToolkit (already exists)
        events = await self.toolkit.discover_events(topic=self.topic)
        
        # 2. Format using EventToolkit (already exists)
        formatted = self.toolkit.format_for_llm(events)
        
        # 3. Build prompt (new)
        prompt = self.prompt_template.format(
            state=state,
            events=formatted
        )
        
        # 4. Call LLM (new - reuse ChoreographyPlanner pattern)
        response = completion(model=self.model, messages=[...])
        
        # 5. Parse to EventDecision (new)
        return EventDecision(**response)
    
    async def publish_decision(self, decision: EventDecision):
        # Validate and publish (new)
        pass
```

**Requirements Documentation:**
```markdown
EventSelector should:
1. ✅ Discover available events from Registry (use EventToolkit)
2. ✅ Format events for LLM selection (use EventToolkit.format_for_llm)
3. ❌ Use customizable prompt templates (NEW)
4. ❌ Return EventDecision (event_type + payload + reasoning) (NEW type)
5. ✅ Validate selected event exists (use EventToolkit.create_payload)
6. ❌ Support BYO LLM model (NEW - same as ChoreographyPlanner)

Total NEW work: ~50% (LLM integration, prompt templates, EventDecision type)
```

**Tracking:**
- [ ] Update Stage 5 roadmap with EventSelector
- [ ] Create GitHub issue: "Implement EventSelector utility"
- [ ] Reference this document in issue

---

### RF-SDK-018: EventToolkit.format_for_llm_selection()

**Description:** Helper method to format discovered events for LLM consumption.

**Original Spec:** [sdk/07-DISCOVERY.md](sdk/07-DISCOVERY.md)

**Use Case:**
```python
# Defer this helper to Stage 5
from soorma.ai.toolkit import EventToolkit

@planner.on_goal("goal")
async def handle(goal, context):
    events = await context.registry.discover(topic="action-requests")
    
    # Format for LLM prompt
    formatted = EventToolkit.format_for_llm_selection(events)
    # Output: Human-readable event descriptions with schemas
```

**Reason for Deferral:**
- Similar functionality already in ChoreographyPlanner._build_prompt()
- Can extract and generalize later if multiple use cases emerge
- Not blocking any Stage 4 features

**Target Stage:** Stage 5 (Discovery)

**Estimated Effort:** 4-6 hours

**Dependencies:**
- EventDefinition schema from Registry
- PlannerDecision.model_json_schema() pattern

**Requirements Documentation:**
```markdown
format_for_llm_selection() should:
1. Accept List[EventDefinition] from Registry
2. Format as human-readable text for LLM prompts
3. Include: event_type, description, required fields
4. Optionally include full JSON schema
5. Support grouping by capability or topic
```

**Tracking:**
- [ ] Update Stage 5 roadmap with EventToolkit
- [ ] Create GitHub issue: "Add EventToolkit.format_for_llm_selection()"
- [ ] Reference in EventSelector implementation

---

### Advanced Conditional State Transitions

**Description:** Support condition expressions in state machine transitions.

**Original Spec:** Mentioned in [sdk/06-PLANNER-MODEL.md](sdk/06-PLANNER-MODEL.md)

**Use Case:**
```python
# MVP (Stage 4): Event-based transitions only
StateTransition(
    on_event="task.failed",
    to_state="retry_state"
)

# Future (Stage 5+): Conditional transitions
StateTransition(
    on_event="task.failed",
    to_state="retry_state",
    condition="plan.state['retry_count'] < 3"  # ← Deferred
)

# Or more complex conditions
StateTransition(
    on_event="validation.completed",
    to_state="publish_draft",
    condition="result.data['score'] > 0.8"
)
```

**Reason for Deferral:**
- Simple event-based transitions sufficient for MVP
- Conditional transitions add complexity:
  - Need condition parser/evaluator
  - Need validation of condition expressions
  - Need security (prevent code injection)
- Can evaluate if needed based on real usage patterns

**Target Stage:** Stage 5 or 6 (or post-launch)

**Estimated Effort:** 2-3 days

**Dependencies:**
- Stage 4 PlanContext state machine (must be stable)
- Safe expression evaluator (e.g., simpleeval library)

**Requirements Documentation:**
```markdown
Conditional Transitions Requirements:

1. Syntax:
   - Simple: "retry_count < 3"
   - Field access: "plan.state['field']"
   - Event data: "event.data['score'] > 0.8"
   - Boolean ops: "field == 'value' and count < 5"

2. Evaluation:
   - Safe execution (no eval() - use simpleeval)
   - Access to: plan.state, plan.results, event.data
   - No access to: context, filesystem, network

3. Validation:
   - Validate condition syntax at state machine creation
   - Provide helpful error messages
   - Document supported operators

4. Testing:
   - Unit tests for condition parser
   - Unit tests for condition evaluator
   - Integration tests with PlanContext

5. Security:
   - Whitelist allowed operations
   - Prevent code injection
   - Sanitize inputs
```

**Decision Criteria for Implementation:**
- Wait for 3+ real-world use cases requiring conditionals
- If most planners use simple event-based transitions, stay simple
- If complex routing needed, implement this feature

**Tracking:**
- [ ] Monitor Stage 4-5 planner examples for conditional needs
- [ ] Create GitHub issue: "Add conditional transitions to PlanContext" (label: `enhancement`, `deferred`)
- [ ] Revisit during Stage 6 planning

---

### Tracker Service UI

**Description:** Web UI for visualizing plan execution timelines.

**Original Spec:** [arch/04-TRACKER-SERVICE.md](arch/04-TRACKER-SERVICE.md) (query APIs)

**Use Case:**
```
Web UI showing:
- Plan execution timeline (Gantt chart)
- Task dependencies (DAG visualization)
- Event trace tree
- Performance metrics
```

**Reason for Deferral:**
- Tracker Service provides REST APIs (sufficient for MVP)
- FDE (Forward Deployed Engineering): Use curl, Postman, or simple scripts
- UI is nice-to-have, not blocking agent development
- Can build UI post-launch based on user feedback

**Target Stage:** Post-launch enhancement

**Estimated Effort:** 1-2 weeks (React + API integration)

**Dependencies:**
- Tracker Service REST APIs (Stage 4 deliverable)
- Plan/task timeline data model

**FDE Alternative (Stage 4):**
```bash
# Query plan progress via curl
curl http://localhost:8004/v1/tracker/plans/{plan_id}

# Query task timeline
curl http://localhost:8004/v1/tracker/plans/{plan_id}/tasks

# Simple Python script for visualization
python scripts/view_plan_timeline.py --plan-id {plan_id}
```

**Requirements Documentation:**
```markdown
Tracker UI Requirements (future):

1. Features:
   - Plan list (filter by user, status, date)
   - Plan detail view (timeline, tasks, events)
   - Event trace tree (expandable hierarchy)
   - Performance metrics (duration, success rate)
   - Search/filter plans

2. Tech Stack (TBD):
   - Frontend: React or Vue.js
   - Visualization: D3.js or similar
   - State management: Context API or Redux
   - API client: Fetch or Axios

3. Integration:
   - Uses Tracker Service REST APIs
   - No authentication initially (single-tenant)
   - WebSocket for real-time updates (optional)
```

**Tracking:**
- [ ] Create GitHub issue: "Build Tracker Service UI" (label: `enhancement`, `ui`)
- [ ] Revisit post-launch based on user requests
- [ ] Consider if community wants to contribute this

---

## Process for Adding Deferred Items

When deferring work during implementation:

1. **Document in this file:**
   - Description and use case
   - Reason for deferral
   - Target stage
   - Estimated effort
   - Dependencies
   - Requirements documentation

2. **Update refactoring README:**
   - Add to "Deferred to Stage X" section
   - Link to this document

3. **Create GitHub issue:**
   - Title: Clear description
   - Labels: `enhancement`, `deferred`
   - Body: Link to this document section
   - Milestone: Target stage or "Backlog"

4. **Reference in commit message:**
   - Example: `feat(sdk): Add ChoreographyPlanner; defer EventSelector to Stage 5 (see DEFERRED_WORK.md)`

---

## Review Cadence

- **During stage planning:** Review deferred items, promote to current stage if priorities changed
- **End of stage:** Update this document with new deferrals
- **Post-launch:** Triage deferred items based on user feedback

---

## Related Documents

- [docs/refactoring/README.md](README.md) - Refactoring index with stage status
- [docs/refactoring/sdk/](sdk/) - SDK refactoring specs
- [docs/refactoring/arch/](arch/) - Architecture refactoring specs
