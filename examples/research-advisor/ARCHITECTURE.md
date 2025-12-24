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

---

## Memory Architecture (CoALA Framework)

This example demonstrates proper usage of the **CoALA** (Cognitive Architectures for Language Agents) memory framework with four distinct memory types:

### Memory Type Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Memory Architecture                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐  ┌─────────────────┐                   │
│  │ SEMANTIC MEMORY │  │ WORKING MEMORY  │                   │
│  │  (Knowledge)    │  │  (Plan State)   │                   │
│  └─────────────────┘  └─────────────────┘                   │
│         ↓                      ↓                            │
│   Cross-Plan            Plan-Scoped                         │
│   Persistent            Temporary                           │
│                                                             │
│  ┌─────────────────┐  ┌─────────────────┐                   │
│  │ EPISODIC MEMORY │  │ PROCEDURAL MEM  │                   │
│  │  (History)      │  │  (Skills)       │                   │
│  └─────────────────┘  └─────────────────┘                   │
│         ↓                      ↓                            │
│   User/Agent            User/Agent                          │
│   Scoped                Scoped                              │
└─────────────────────────────────────────────────────────────┘
```

### 1. Semantic Memory - Cross-Plan Knowledge

**Purpose**: Store facts and knowledge that should be reusable across all workflows.

**Scope**: Global (accessible by any agent, any user, any plan)

**Example in Researcher**:
```python
# Store research findings for future reuse
await context.memory.store_knowledge(
    content=summary,  # The actual research findings
    metadata={"query_topic": query_topic, "source_url": source_url}
)
```

**Use Case**: 6 months later, a different user asks "What are AI trends?" → Semantic search retrieves this research finding via vector similarity.

**Why not Working Memory?** Working Memory is plan-scoped and deleted after workflow completes.

**Why not Episodic Memory?** Episodic stores "who said what when" - not searchable knowledge.

### 2. Working Memory - Plan-Scoped State

**Purpose**: Store workflow state and intermediate data for the current plan execution.

**Scope**: Plan-scoped (only accessible via `plan_id`, deleted after plan completes)

**Example in Planner**:
```python
# Store workflow state for this specific plan
workflow_state = {
    "action_history": [...],
    "research": {"summary": "...", "source_url": "..."},
    "draft": {"draft_text": "...", "iteration": 1}
}
await context.memory.store("workflow_state", workflow_state, plan_id=plan_id)
```

**Use Case**: Planner needs to track what actions have been taken in **this workflow** to avoid loops and make informed decisions.

**Why not Semantic Memory?** This is temporary state, not reusable knowledge.

**Why not Episodic Memory?** This is structured state, not conversation history.

### 3. Episodic Memory - Interaction History

**Purpose**: Store user/agent interaction history for conversation context and audit trails.

**Scope**: User + Agent scoped (tied to `user_id` and `agent_id`)

**Example in Researcher**:
```python
# Log what the researcher did
await context.memory.log_interaction(
    agent_id="web-researcher",
    user_id=DEFAULT_USER_ID,
    role="assistant",
    content=f"Research completed for '{query_topic}': {summary[:200]}...",
    metadata={"event_id": event_id}
)
```

**Use Case**: "What did the researcher do last week?" or conversation context windows.

**Why not Semantic Memory?** This is about "who did what" not "what facts do we know".

**Why not Working Memory?** This persists beyond plan completion for audit trails.

### 4. Procedural Memory - Skills & Prompts

**Purpose**: Store dynamic prompts, few-shot examples, and agent skills.

**Scope**: User + Agent scoped (personalized behavior)

**Example** (not used in this demo, but available):
```python
# Store a personalized skill for this user
await context.memory.store_skill(
    agent_id="researcher",
    user_id=user_id,
    trigger_condition="research on academic papers",
    procedure_type="system_prompt",
    content="Always prioritize peer-reviewed sources"
)
```

**Use Case**: Personalize agent behavior per user without changing code.

### Memory Pattern in Research Advisor

```python
# RESEARCHER WORKER
async def on_research_request(event, context):
    # 1. SEMANTIC: Check existing knowledge BEFORE expensive web search
    existing = await context.memory.search_knowledge(query=topic, limit=3)
    
    if existing and len(existing) > 0:
        # Reuse cached research - avoid duplicate web searches
        summary = existing[0]['content']
        url = existing[0]['metadata'].get('source_url', 'Previously researched')
    else:
        # No cached knowledge - perform new web search
        summary, url = await do_web_search(topic)
        
        # Store NEW findings only (avoid duplicate storage)
        await context.memory.store_knowledge(
            content=summary,
            metadata={"query_topic": topic, "source_url": url}
        )
    
    # 2. WORKING: Always store in plan-scoped memory (cached or new)
    await context.memory.store(
        key=f"research_{topic}",
        value={"summary": summary, "source_url": url},
        plan_id=plan_id
    )
    
    # 3. EPISODIC: Log interaction for audit trail
    await context.memory.log_interaction(
        agent_id="web-researcher",
        user_id=user_id,
        role="assistant",
        content=f"Research completed: {summary[:200]}..."
    )


# PLANNER AGENT
async def on_research_result(event, context):
    # 1. SEMANTIC: Store findings for future discovery
    await context.memory.store_knowledge(content=summary, metadata={...})
    
    # 2. WORKING: Update plan state with full structured data
    workflow_state = await context.memory.retrieve("workflow_state", plan_id=plan_id)
    workflow_state['research'] = full_research_data
    await context.memory.store("workflow_state", workflow_state, plan_id=plan_id)
    
    # 3. EPISODIC: Log planner decision
    await context.memory.log_interaction(
        agent_id="planner",
        user_id=user_id,
        role="assistant",
        content=f"Decision: Proceeding to draft based on research"
    )
```

### Memory Design Principles

1. **Semantic for Facts**: If it's knowledge that should be discoverable later → Semantic
2. **Working for State**: If it's temporary plan execution state → Working
3. **Episodic for History**: If it's "who did what when" → Episodic
4. **Procedural for Skills**: If it's "how to behave" → Procedural

### Benefits of Multi-Memory Architecture

- **Knowledge Reuse**: Research findings persist beyond workflow completion
- **Plan Isolation**: Each workflow has its own state, no cross-contamination
- **Auditability**: Full history of agent actions and decisions
- **Personalization**: Future support for user-specific agent behaviors

---

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
