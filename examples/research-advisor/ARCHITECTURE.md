# Research Advisor: Architecture Deep Dive

This document provides technical details on how the Research Advisor implements **Autonomous Choreography**. For a quick overview and setup instructions, see [README.md](README.md).

## Why Avoid Hardcoded Workflow Rules?

Traditional agent systems embed workflow logic in code:

```python
# ❌ Hardcoded workflow - brittle, requires code changes
def handle_research_result():
    publish("draft.requested")  # Always this, no flexibility

def handle_draft_result():
    publish("validation.requested")  # Rigid sequence
```

This approach has problems:
- **Brittle**: Adding/removing steps requires code changes
- **No Context Awareness**: Can't adapt to unusual situations
- **Poor Composability**: Hard to reuse agents in different workflows

### The Autonomous Choreography Approach

Instead, we let an LLM reason about what to do next:

```python
# ✅ LLM-driven decisions - flexible, context-aware
async def handle_any_result(trigger_context):
    events = await registry.discover_events()  # What can I do?
    decision = await llm.reason(
        trigger=trigger_context,
        state=workflow_state,
        available_events=events  # Rich metadata
    )
    await publish(decision.event, decision.payload)
```

The LLM reads event metadata (descriptions, purposes, schemas) and reasons:
> "I have research data. Looking at available events, 'agent.draft.requested' creates responses from research. That's what I need next."

## The DisCo Protocol

DisCo (Distributed Cognition) is the protocol that enables this:

### 1. Events as Capabilities
Every agent capability is expressed as an **Event Definition**:
```python
RESEARCH_REQUEST_EVENT = EventDefinition(
    event_name="agent.research.requested",
    description="Request web research on a topic",
    purpose="Gather information from the web to answer questions",
    payload_schema=ResearchRequestPayload.model_json_schema()
)
```

### 2. Registry as Capability Index
Agents register their events on startup. The Registry becomes a searchable index of "what can be done" in the system.

### 3. Dynamic Discovery
The Planner queries the Registry to discover available actions:
```python
async with EventToolkit(registry_url) as toolkit:
    events = await toolkit.discover_actionable_events(topic="action-requests")
    # Returns: [{name, description, purpose, payload_schema}, ...]
```

### 4. LLM as Reasoning Engine
The Planner presents discovered events to an LLM:
```
## DISCOVERED AVAILABLE EVENTS
[
  {
    "event_name": "agent.research.requested",
    "description": "Request web research on a topic",
    "purpose": "Gather information from the web",
    "payload_schema": {"query": "string", "context": "string"}
  },
  {
    "event_name": "agent.draft.requested",
    "description": "Request a draft response based on research",
    "purpose": "Create user-facing content from research data",
    "payload_schema": {"user_request": "string", "research_context": "string"}
  }
]

## YOUR TASK
Analyze current state and select the best event to progress toward the goal.
```

The LLM reasons about metadata and returns a decision.

## Prompt Engineering for Autonomous Agents

The Planner's prompt is carefully structured:

### 1. Trigger Context
What just happened - provides immediate context:
```
"Research completed. Summary: 'NATS is a lightweight messaging system...'"
```

### 2. Workflow State
Accumulated data from previous steps:
```json
{
  "goal": {"goal": "Compare NATS vs Pub/Sub"},
  "research": {"summary": "..."},
  "draft": {"draft_text": "..."},
  "action_history": ["agent.research.requested", "agent.draft.requested"]
}
```

### 3. Discovered Events
Event metadata from the Registry (see above).

### 4. Decision Guidelines
General principles, NOT specific rules:
```
- Choose events based on their DESCRIPTION and PURPOSE
- Progress logically: gather info → process → validate → deliver
- If validation is available, use it before completing
```

### 5. Response Format
Structured output the code can parse:
```json
{
  "action": "publish",
  "event": "agent.validation.requested",
  "payload": {"draft_text": "...", "source_text": "..."},
  "reasoning": "Draft exists, validation event checks accuracy before delivery."
}
```

## Avoiding Hardcoded Rules

### ❌ What NOT to Do
```python
# Don't hardcode event names in prompts
prompt = """
WORKFLOW RULES:
1. After research, always publish agent.draft.requested
2. After draft, always publish agent.validation.requested
"""
```

### ✅ What TO Do
```python
# Let LLM reason from event metadata
prompt = f"""
DISCOVERED EVENTS:
{format_events_for_llm(events)}  # Includes descriptions, purposes

GUIDELINES:
- Choose based on event descriptions
- Validate content before delivering to users
"""
```

The difference: specific event names come from **discovered metadata**, not hardcoded rules.

## Circuit Breakers: Balancing Autonomy and Safety

Autonomous systems can exhibit problematic behaviors:

### Problem: Runaway Loops
LLM might get stuck: research → draft → research → draft → ...

### Solution: Action Limits
```python
MAX_TOTAL_ACTIONS = 10

if len(action_history) >= MAX_TOTAL_ACTIONS:
    # Force completion with best available result
    return {"action": "complete", "result": draft_text or research_summary}
```

### Problem: Vague Results
LLM might return meta-descriptions: "The draft is ready" instead of actual content.

### Solution: Content Validation
```python
vague_indicators = ["draft is ready", "already prepared", "has been generated"]
if any(indicator in result.lower() for indicator in vague_indicators):
    result = workflow_state["draft"]["draft_text"]  # Use actual content
```

## Future: Tracker Service

Current limitations:
- **Lost Events**: If an event is dropped, workflow stalls forever
- **Timeouts**: No detection of slow/stuck workers
- **No Observability**: Can't see workflow progress externally

### Planned Tracker Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Planner   │────▶│   Tracker   │────▶│  Dashboard  │
│             │     │  (Monitor)  │     │  (Human UI) │
└─────────────┘     └──────┬──────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │   Alerts    │
                    │  Timeouts   │
                    │  Retries    │
                    └─────────────┘
```

The Tracker will:
1. **Monitor Progress**: Track workflow state transitions
2. **Detect Stalls**: Timeout if no progress after N seconds
3. **Enable Intervention**: Human can unstick or redirect workflows
4. **Provide Observability**: Dashboard showing active workflows

This balances **autonomy** (LLM makes decisions) with **reliability** (guaranteed completion).

## Summary

| Principle | Implementation |
|-----------|----------------|
| **No Hardcoded Workflows** | LLM reasons from event metadata |
| **Dynamic Discovery** | Query Registry for available events |
| **Rich Event Metadata** | Descriptions, purposes, schemas |
| **Context-Aware Decisions** | LLM sees full workflow state |
| **Safety Limits** | Circuit breakers prevent runaways |
| **Future Reliability** | Tracker service for observability |

This architecture demonstrates the power of the Soorma Platform and DisCo protocol: agents coordinate complex workflows through emergent behavior, not rigid programming.
