# 03 - Events Structured

**Concepts:** Rich event metadata, LLM-based event selection, Structured events for reasoning  
**Difficulty:** Intermediate  
**Prerequisites:** [02-events-simple](../02-events-simple/)

## What You'll Learn

- How to add rich metadata to events for better discoverability
- How to register events with semantic descriptions
- How to use LLMs to select the right event based on context
- When to use structured events vs simple events

## The Problem

In [02-events-simple](../02-events-simple/), events were hardcoded:

```python
@worker.on_event("order.placed", topic=EventTopic.BUSINESS_FACTS)
async def handle_order(event, context):
    # Handler knows exactly what event it will publish
    await context.bus.announce("inventory.reserve", ...)
```

But what if an agent needs to **dynamically choose** which event to publish based on:
- Current workflow state
- Available capabilities in the system
- Business logic that changes frequently
- Context that only an LLM can understand?

**Example:** A customer support agent needs to escalate a ticket, but the right action depends on:
- Ticket severity
- Available support tiers
- Current system load
- Customer's support plan

Instead of hardcoding all these conditions, we let an LLM reason about which event to publish.

## The Pattern

**Structured Events** use `EventDefinition` with rich metadata:

```python
from pydantic import BaseModel, Field
from soorma_common import EventDefinition, EventTopic

class Tier2RoutePayload(BaseModel):
    ticket_id: str = Field(..., description="Ticket to route")
    category: str = Field(..., description="Issue category")
    severity: str = Field(..., description="Severity level")
    technical_area: str = Field(..., description="Technical domain")

TIER2_ROUTE_EVENT = EventDefinition(
    event_name="ticket.route.tier2",
    topic=EventTopic.ACTION_REQUESTS,
    description="Route ticket to Tier 2 technical support for technical issues requiring specialized knowledge like API errors, integration problems, performance issues",
    payload_schema=Tier2RoutePayload.model_json_schema(),
)
```

**Note:** In this example, `ticket.created` uses `EventTopic.BUSINESS_FACTS` (domain event), while routing decisions use `EventTopic.ACTION_REQUESTS` (requesting agents to handle tickets). See [TOPICS.md](../../docs/TOPICS.md).

When agents declare `events_consumed` and `events_produced` with `EventDefinition` objects, the SDK automatically registers them:

```python
from events import TICKET_CREATED_EVENT, TIER1_ROUTE_EVENT, TIER2_ROUTE_EVENT, ...

worker = Worker(
    name="ticket-router",
    events_consumed=[TICKET_CREATED_EVENT],
    events_produced=[TIER1_ROUTE_EVENT, TIER2_ROUTE_EVENT, ...],
)
```

This metadata allows:
1. **Discovery** - Agents can query available events from the Registry
2. **LLM Selection** - LLMs can reason about which event to use
3. **Validation** - Registry validates published events match their schema
4. **Documentation** - Self-documenting event catalog
5. **Flow Tracking** - Registry knows which agents consume/produce which events

## Use Case

A support ticket triage system where an LLM agent decides how to route tickets based on:
- Ticket content
- Customer history
- Available support capabilities
- Current queue status

The agent discovers available routing events and uses an LLM to select the most appropriate one.

## Code Walkthrough

### Event Definitions ([events.py](events.py))

Events are defined with Pydantic schemas and rich metadata:

```python
from pydantic import BaseModel, Field
from soorma_common import EventDefinition, EventTopic

class Tier1RoutePayload(BaseModel):
    ticket_id: str = Field(..., description="Ticket to route")
    category: str = Field(..., description="Issue category")
    priority: str = Field(..., description="Priority level")

TIER1_ROUTE_EVENT = EventDefinition(
    event_name="ticket.route.tier1",
    topic=EventTopic.ACTION_REQUESTS,
    description="Route ticket to Tier 1 general support for common issues...",
    payload_schema=Tier1RoutePayload.model_json_schema(),
)
```

**How it applies the concepts:**
- `EventDefinition` wraps event metadata (name, topic, description, schema)
- Pydantic schemas self-document what data is required and what each field means
- Event descriptions guide LLM reasoning ("Route to Tier 1 for common issues...")
- When agent declares these in `events_produced`, the SDK auto-registers them with the Registry

### LLM Utilities ([llm_utils.py](llm_utils.py))

Two generic utilities for LLM-based event selection:

**`select_event_with_llm(prompt_template, context_data, formatted_events, model)`** - Uses LLM to select the best event:

```python
# Format prompt by substituting agent-specific template variables
prompt = prompt_template.format(
    context_data=json.dumps(context_data, indent=2),
    events=formatted_events  # Pre-formatted event options
)

# Call LLM
response = completion(
    model=model or os.getenv("LLM_MODEL", "gpt-4o-mini"),
    messages=[{"role": "user", "content": prompt}],
    response_format={"type": "json_object"}
)

# Return decision with event_name, reason, data
return json.loads(response.choices[0].message.content)
```

**`validate_and_publish(decision, events, topic, context)`** - Validates LLM's choice and publishes:

```python
# Prevent hallucinations - check event was actually discovered
if decision["event_name"] not in [e.event_name for e in events]:
    print(f"ERROR: LLM selected invalid event: {decision['event_name']}")
    return False

# Publish validated event
await context.bus.publish(
    event_type=decision["event_name"],
    topic=topic,
    data=decision["data"],
)
return True
```

### Ticket Router Agent ([ticket_router.py](ticket_router.py))

The agent demonstrates the clean pattern when using SDK toolkit + LLM utilities:

```python
worker = Worker(
    name="ticket-router",
    events_consumed=[TICKET_CREATED_EVENT],
    events_produced=[
        TIER1_ROUTE_EVENT,
        TIER2_ROUTE_EVENT,
        SPECIALIST_ROUTE_EVENT,
        MANAGEMENT_ESCALATION_EVENT,
        AUTOCLOSE_EVENT,
    ],
)
```

**Domain-specific LLM prompt** - Only the prompt is agent-specific:

```python
TICKET_ROUTING_PROMPT = """You are a support ticket routing assistant...

TICKET INFORMATION:
{context_data}

AVAILABLE ROUTING OPTIONS:
{events}

Select the most appropriate routing event...
Return JSON with: event_name, reason, data
"""
```

**Event handler using three steps**:

```python
@worker.on_event("ticket.created", topic=EventTopic.BUSINESS_FACTS)
async def route_ticket(event: EventEnvelope, context: PlatformContext):
    data = event.data or {}
    
    # Step 1: Discover available routing events from Registry
    events = await context.toolkit.discover_actionable_events(
        topic=EventTopic.ACTION_REQUESTS
    )
    
    # Step 2: Format events for LLM and let it select the best one
    event_dicts = context.toolkit.format_for_llm(events)
    formatted_events = context.toolkit.format_as_prompt_text(event_dicts)
    
    decision = await select_event_with_llm(
        prompt_template=TICKET_ROUTING_PROMPT,  # Domain-specific
        context_data=data,
        formatted_events=formatted_events,
    )
    
    # Step 3: Validate and publish the decision
    await validate_and_publish(
        decision=decision,
        events=events,
        topic=EventTopic.ACTION_REQUESTS,
        context=context
    )
```

**How it applies the concepts:**
- SDK `discover_actionable_events()` finds all events the Registry knows about
- SDK `format_for_llm()` and `format_as_prompt_text()` prepare events for LLM reasoning
- Agent provides domain-specific prompt (ticket routing instructions)
- LLM utility selects the best event based on context and available options
- Validation prevents LLM hallucinations (if LLM picks non-existent event, it fails safely)

## Running the Example

### Prerequisites

**Terminal 1: Start Platform Services**

```bash
# From soorma-core root directory
soorma dev --build
```

**Leave this running** for all examples.

**Set your OpenAI API key:**

```bash
export OPENAI_API_KEY='your-key-here'
```

**Note:** When the worker starts, the SDK automatically registers its event definitions with the Registry. Other agents can then discover these events using `EventToolkit.discover_actionable_events()`. This example demonstrates both event registration (automatic via SDK) and event discovery (explicit via EventToolkit).

### Quick Start

**Terminal 2: Run the example**

```bash
cd examples/03-events-structured
./start.sh
```

This starts the ticket router agent which will:
1. Register its event definitions with the Registry
2. Listen for `ticket.created` events
3. Discover available routing options
4. Use LLM to select the best routing event

**Terminal 3: Create a test ticket**

```bash
python client.py "My API integration is failing"
```

### Manual Steps

**After starting platform services above...**

**Terminal 2: Start the Ticket Router Agent**

```bash
cd examples/03-events-structured
python ticket_router.py
```

The agent will:
1. Register its event definitions with the Registry
2. Listen for `ticket.created` events  
3. Show routing decisions for each ticket

**Terminal 3: Create Test Tickets**

```bash
# Simple issue → Tier 1
python client.py "My password reset link isn't working"

# Technical issue → Tier 2
python client.py "Getting 500 error when calling /api/v2/users endpoint"

# Complex issue → Specialist
python client.py "Need to integrate SSO with custom SAML provider"
```

### Expected Output

The selector will show:
```
📧 New ticket received: TICK-001
   Issue: Getting 500 error when calling /api/v2/users endpoint
   
🔍 Discovering available routing events from Registry

🤖 LLM Analysis:
   Reasoning about appropriate routing...
   
✅ Published routing decision
```

## Key Takeaways

✅ **EventDefinition wraps metadata** - Event descriptions and schemas guide LLM reasoning  
✅ **SDK auto-registers events** - Pass EventDefinition objects to `events_consumed`/`events_produced`, SDK handles Registry registration  
✅ **Discovery enables flexibility** - Agents use `context.toolkit.discover_actionable_events()` to find available options at runtime  
✅ **LLM reasoning selects dynamically** - Instead of hardcoding workflows, let LLMs choose based on context and available capabilities  
✅ **Validation prevents hallucinations** - Always check that LLM-selected events actually exist in the Registry before publishing  
✅ **Separate domain logic from utilities** - Agent code focuses on the prompt (domain-specific); discovery, formatting, validation are reusable utilities  

## When to Use Structured Events

| Use Structured Events When... | Use Simple Events When... |
|-------------------------------|---------------------------|
| Workflows change frequently | Workflow is stable |
| Multiple routing options exist | Single deterministic path |
| Decisions require reasoning | Decisions are rule-based |
| Events are added dynamically | Events are known at compile time |
| Need event discovery | Direct event names are fine |

## Comparison

### Simple Events (02-events-simple)
```python
from soorma_common.events import EventTopic

# Hardcoded - fast, but inflexible
@worker.on_event("order.placed", topic=EventTopic.BUSINESS_FACTS)
async def handle(event, context):
    await context.bus.announce("inventory.reserve", topic=EventTopic.ACTION_REQUESTS, ...)
```

### Structured Events (This example)
```python
from soorma_common.events import EventTopic

# Dynamic - flexible, but requires LLM call
@worker.on_event("order.placed", topic=EventTopic.BUSINESS_FACTS)
async def handle(event, context):
    # Discover events dynamically
    events = await context.toolkit.discover_actionable_events(
        topic=EventTopic.ACTION_REQUESTS
    )
    # Use LLM to select
    event_dicts = context.toolkit.format_for_llm(events)
    formatted = context.toolkit.format_as_prompt_text(event_dicts)
    selected = await llm_choose_event(formatted, context)
    # Publish selected event
    await context.bus.announce(selected, topic=EventTopic.ACTION_REQUESTS, ...)
```

## Advanced: Preventing Hallucinated Events

The SDK validates that events exist in Registry before publishing:

```python
# In ChoreographyPlanner (Phase 2 SDK enhancement)
async def execute_decision(self, decision, context):
    # Validate event exists
    if decision.event_name not in self.discovered_events:
        raise InvalidEventError(
            f"LLM tried to publish '{decision.event_name}' but it doesn't exist"
        )
    
    # Safe to publish
    await context.bus.announce(decision.event_name, ...)
```

This prevents LLMs from "hallucinating" event names that don't exist.

## Next Steps

- **[04-memory-working](../04-memory-working/)** - Learn workflow state management (recommended next)
- **[05-memory-semantic](../05-memory-semantic/)** - RAG with LLM routing (builds on this example)
- **07-tool-discovery (coming soon)** - Similar pattern for discovering tools
- **09-app-research-advisor (coming soon)** - Full autonomous system using structured events

---

**📖 Additional Resources:**
- [Event Patterns Documentation](../../docs/EVENT_PATTERNS.md)
- [Design Patterns - Autonomous Choreography](../../docs/DESIGN_PATTERNS.md)
