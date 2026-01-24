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
@worker.on_event("order.placed", topic="business-facts")
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

Define events using `EventDefinition` with Pydantic schemas:

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
    description="Route ticket to Tier 1 general support for common issues like password resets, account questions, basic troubleshooting",
    payload_schema=Tier1RoutePayload.model_json_schema(),
)
```

### LLM Utilities ([llm_utils.py](llm_utils.py))

> **Note**: These utilities are shown for educational purposes. The SDK will provide built-in methods to handle this complexity.

This file contains reusable functions for LLM-based event selection:

**`discover_events(context, topic)`** - Discovers available events from Registry:
```python
async def discover_events(context, topic: str) -> list[dict]:
    async with EventToolkit(context.registry.base_url) as toolkit:
        events = await toolkit.discover_actionable_events(topic=topic)
        return events
```

**`format_events_for_llm(events)`** - Formats event metadata for LLM prompts:
```python
def format_events_for_llm(events: list[dict]) -> str:
    formatted = []
    for event in events:
        formatted.append(
            f"**{event['name']}**\n"
            f"   Description: {event['description']}\n"
        )
    return "\n".join(formatted)
```

**`select_event_with_llm(prompt_template, context_data, events, model)`** - Uses LLM to select best event:
```python
async def select_event_with_llm(
    prompt_template: str,  # Agent provides domain-specific instructions
    context_data: dict,
    events: list[dict],
    model: str = None
) -> dict:
    # Format events for LLM
    event_options = format_events_for_llm(events)
    
    # Build prompt with agent's template
    prompt = prompt_template.format(
        context_data=json.dumps(context_data, indent=2),
        events=event_options
    )
    
    # Call LLM
    response = completion(
        model=model or os.getenv("LLM_MODEL", "gpt-4o-mini"),
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    
    return json.loads(response.choices[0].message.content)
```

**`validate_and_publish(decision, events, topic, context)`** - Validates LLM's choice and publishes:
```python
async def validate_and_publish(
    decision: dict,
    events: list[dict],
    topic: str,
    context
) -> bool:
    event_names = [e["name"] for e in events]
    
    # Prevent LLM hallucinations - validate event exists
    if decision["event_name"] not in event_names:
        print(f"ERROR: LLM selected invalid event: {decision['event_name']}")
        return False
    
    # Publish the validated event
    await context.bus.publish(
        event_type=decision["event_name"],
        topic=topic,
        data=decision["data"],
    )
    return True
```

### Ticket Router Agent ([ticket_router.py](ticket_router.py))

The agent focuses on domain-specific logic, using the utilities from `llm_utils.py`:

```python
from soorma import Worker
from events import TICKET_CREATED_EVENT, TIER1_ROUTE_EVENT, ...
from llm_utils import discover_events, select_event_with_llm, validate_and_publish

# Pass EventDefinition objects - SDK auto-registers them
worker = Worker(
    name="ticket-router",
    capabilities=["routing"],
    events_consumed=[TICKET_CREATED_EVENT],
    events_produced=[TIER1_ROUTE_EVENT, TIER2_ROUTE_EVENT, ...],
)

# Domain-specific LLM prompt (agent customization)
TICKET_ROUTING_PROMPT = """You are a support ticket router...

TICKET: {context_data}
OPTIONS: {events}

Select the best routing event..."""

@worker.on_event("ticket.created", topic="business-facts")
async def route_ticket(event, context):
    # Step 1: Discover available routing options
    events = await discover_events(context, topic="action-requests")
    
    # Step 2: Let LLM select best option using agent's prompt
    decision = await select_event_with_llm(
        prompt_template=TICKET_ROUTING_PROMPT,  # Agent customizes here
        context_data=event.data,
        events=events
    )
    
    # Step 3: Validate and publish the decision
    await validate_and_publish(decision, events, "action-requests", context)
```

**Key Insight**: The agent code is focused and readable. The ~150 lines of boilerplate are isolated in `llm_utils.py`.

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

This will:
1. Verify platform services are running
2. Start the LLM event selector

**Terminal 3: Create a test ticket**

```bash
python client.py "My API integration is failing"
```

### Manual Steps

**After starting platform services above...**

**Terminal 2: Start the LLM Event Selector**

```bash
cd examples/03-events-structured
python ticket_router.py
```

This agent will:
1. Listen for `ticket.created` events
2. Discover available routing events from Registry
3. Use an LLM to select the appropriate routing event
4. Publish the selected event

**Terminal 3: Create Test Tickets**

```bash
# Simple issue
python client.py "My password reset link isn't working"

# Technical issue
python client.py "Getting 500 error when calling /api/v2/users endpoint"

# Complex issue
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

✅ **Discovery enables flexibility** - Agents can find available events from the Registry  
✅ **LLMs reason about options** - Choose dynamically based on context and event metadata  
✅ **Structured events self-document** - Event descriptions and schemas guide LLM reasoning  
✅ **Decoupled workflows** - Agents discover capabilities without hardcoded dependencies  
✅ **SDK auto-registration** - When agents declare `events_consumed` and `events_produced` with `EventDefinition` objects, the SDK automatically registers them with the Registry on startup

**Key Pattern:** Pass `EventDefinition` objects (not strings) to `events_consumed` and `events_produced`. The SDK:
1. Extracts event metadata from EventDefinition
2. Registers events with Registry when agent starts
3. Makes events discoverable via `EventToolkit.discover_actionable_events()`
4. No manual registration needed  

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
# Hardcoded - fast, but inflexible
@worker.on_event("order.placed", topic="business-facts")
async def handle(event, context):
    await context.bus.announce("inventory.reserve", ...)
```

### Structured Events (This example)
```python
# Dynamic - flexible, but requires LLM call
@worker.on_event("order.placed", topic="business-facts")
async def handle(event, context):
    events = await discover_events(topic="inventory")
    selected = await llm_choose_event(events, context)
    await context.bus.announce(selected, ...)
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
