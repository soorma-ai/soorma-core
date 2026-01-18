# SDK Refactoring: Discovery & A2A

**Document:** 07-DISCOVERY.md  
**Status:** ⬜ Not Started  
**Priority:** 🟡 Medium (Phase 3)  
**Last Updated:** January 11, 2026

---

## Quick Reference

| Aspect | Details |
|--------|----------|
| **Tasks** | RF-SDK-007: Event Registration<br>RF-SDK-008: Agent Discovery<br>RF-SDK-017: EventSelector utility<br>RF-SDK-018: EventToolkit LLM helpers |
| **Files** | `sdk/python/soorma/context.py`<br>`sdk/python/soorma/gateway.py`<br>`sdk/python/soorma/ai/selection.py` |
| **Pairs With Arch** | [arch/05-REGISTRY-SERVICE.md](../arch/05-REGISTRY-SERVICE.md) |
| **Dependencies** | 01-EVENT-SYSTEM, 03-COMMON-DTOS |
| **Blocks** | None |
| **Estimated Effort** | 3-4 days |

---

## Context

### Why This Matters

Discovery enables **dynamic agent collaboration**:

1. **Event Registration** - Events are owned by agents, registered with capabilities
2. **Agent Discovery** - Find agents by capability, get their event schemas
3. **A2A Gateway** - Expose internal agents to external A2A protocol clients

### Current State

- Events registered flat, no ownership relationship
- `registry.find()` returns agent info but not event schemas
- No A2A Agent Card export capability

### Key Files

```
sdk/python/soorma/
├── context.py          # RegistryClient.discover()
└── gateway.py          # NEW: A2AGatewayHelper

soorma-common/
└── a2a.py              # A2A protocol DTOs
```

### Prerequisite Concepts

From **01-EVENT-SYSTEM** (must complete first):
- `EventDefinition` with payload schemas
- `AgentCapability` with consumed/produced events

From **03-COMMON-DTOS** (must complete first):
- A2A DTOs in `soorma-common/a2a.py`

---

## Summary

This document covers agent and event discovery:
- **RF-SDK-007:** Event Registration Tied to Agent
- **RF-SDK-008:** Agent Discovery by Capability (A2A Alignment)
- **RF-SDK-017:** EventSelector utility for LLM-based event selection
- **RF-SDK-018:** EventToolkit LLM formatting helpers

These tasks enable LLM-driven agent discovery, event selection, and external A2A compatibility.

---

## Tasks

### RF-SDK-007: Event Registration Tied to Agent

**Files:** [context.py](../../sdk/python/soorma/context.py), Registry Service

#### Current Issue

Events registered flat, no ownership relationship.

#### Target

Events registered as part of agent registration, with `agent_id` as owner.

```python
class EventDefinition(BaseDTO):
    event_type: str  # Canonical event type, e.g., "research.requested"
    payload_schema_name: str  # Registered schema name (e.g., "research_request_v1")
    description: Optional[str]
    examples: Optional[List[Dict[str, Any]]]

class AgentCapability(BaseDTO):
    task_name: str
    description: str
    consumed_event: EventDefinition  # ← Full definition with schema name
    produced_events: List[EventDefinition]  # ← Full definitions with schema names
```

**Key Change:** Events reference `payload_schema_name` (registered in Registry) instead of embedding full JSON schema. This enables:
1. Schema reuse across multiple events
2. LLM agents to lookup schema by name when processing dynamic response events
3. Schema versioning independent of event names

**Registry Service Changes:**
- Store `agent_id` as owner of events
- On agent deregistration, optionally cleanup owned events
- Query events by owning agent

---

### RF-SDK-008: Agent Discovery by Capability (A2A Alignment)

**Files:** [context.py](../../sdk/python/soorma/context.py#L54-L107)

#### Current Issue

`registry.find(capability)` returns agent info but not event schemas.

#### Target

Enhanced discovery for LLM reasoning, aligned with A2A Agent Card standard.

---

## A2A Compatibility Analysis

The [A2A (Agent-to-Agent) protocol](https://google.github.io/agent-to-agent/) defines an "Agent Card" for discovery:

| A2A Agent Card Field | Soorma Equivalent | Notes |
|---------------------|-------------------|-------|
| `name` | `AgentDefinition.name` | ✅ Direct match |
| `description` | `AgentDefinition.description` | ✅ Direct match |
| `url` | N/A (we use events, not HTTP) | ⚠️ Different paradigm |
| `provider` | `AgentDefinition.tenant_id` | ✅ Maps to tenant |
| `version` | Add to `AgentDefinition` | 🔧 Need to add |
| `capabilities` | `AgentCapability` list | ✅ Similar concept |
| `skills` | `AgentCapability.task_name` + description | ✅ Maps to capabilities |
| `inputModes` / `outputModes` | Event schemas | ⚠️ Different approach |
| `authentication` | Platform-level (not per-agent) | ⚠️ Different approach |

**Recommendation:** Compatibility layer, not full A2A compliance
- Our event-driven model is fundamentally different from A2A's HTTP-based model
- We can export Agent Cards for interop, but internal model stays event-centric
- Add `version` field to `AgentDefinition` for better alignment
- **A2A conversion handled by `A2AGatewayHelper`**, not RegistryClient

---

## Target Design

### 1. RegistryClient Discovery

```python
class RegistryClient:
    async def discover(
        self,
        requirements: List[str],  # Capability requirements
        include_events: bool = True,  # Include event schemas
    ) -> List[DiscoveredAgent]:
        """
        Discover agents matching requirements.
        
        Returns agents with their capabilities AND the event schemas
        needed to communicate with them.
        """
        pass
    
    # NOTE: A2A Agent Card export is handled by A2AGatewayHelper.agent_to_card()
    # in the gateway module, not here. This keeps RegistryClient focused on
    # internal discovery while gateway handles external protocol translation.


@dataclass
class DiscoveredAgent:
    agent_id: str
    name: str
    description: str
    version: str  # Added for A2A alignment
    capabilities: List[AgentCapability]
    
    def get_consumed_event_schema(self, capability: str) -> EventDefinition:
        """Get the request event definition for invoking a capability."""
        for cap in self.capabilities:
            if cap.task_name == capability:
                return cap.consumed_event
        return None
    
    def get_produced_event_schema(self, capability: str) -> Optional[EventDefinition]:
        """Get the response event definition for a capability."""
        for cap in self.capabilities:
            if cap.task_name == capability and cap.produced_events:
                return cap.produced_events[0]
        return None
```

### 2. AgentDefinition Enhancement

```python
class AgentDefinition(BaseDTO):
    agent_id: str
    name: str
    description: str
    version: str = "1.0.0"  # NEW: for A2A alignment
    tenant_id: str
    capabilities: List[AgentCapability]
```

---

## A2A Gateway Pattern

For external-facing "gateway" agents, we expose A2A-compatible HTTP endpoints while internally using event-driven architecture:

```
External Client (HTTP/A2A)           Gateway Service              Internal Agents (Events)
        │                                  │                              │
        │  POST /.well-known/agent.json    │                              │
        │─────────────────────────────────>│                              │
        │  (A2A Agent Card)                │                              │
        │<─────────────────────────────────│                              │
        │                                  │                              │
        │  POST /tasks/send                │                              │
        │  (A2A Task, OAuth/API Key)       │                              │
        │─────────────────────────────────>│                              │
        │                                  │  action.request (events)     │
        │                                  │─────────────────────────────>│
        │                                  │                              │
        │                                  │  action.result (events)      │
        │                                  │<─────────────────────────────│
        │  (A2A Task Response)             │                              │
        │<─────────────────────────────────│                              │
```

**Implementation Notes:**
- A2A DTOs (`AgentCard`, `Task`, `Message`, etc.) live in `soorma-common`
- Gateway service translates HTTP ↔ events
- SDK provides `A2AGatewayHelper` for gateway implementation

---

## A2AGatewayHelper

```python
# sdk/python/soorma/gateway.py (new)
from soorma_common import A2AAgentCard, A2ATask, A2ATaskResponse
from soorma_common import ActionRequestEvent, ActionResultEvent

class A2AGatewayHelper:
    """Helper for implementing A2A-compatible gateway services."""
    
    @staticmethod
    def agent_to_card(
        agent: AgentDefinition,
        gateway_url: str,
        auth: A2AAuthentication,
    ) -> A2AAgentCard:
        """Convert internal AgentDefinition to A2A Agent Card."""
        return A2AAgentCard(
            name=agent.name,
            description=agent.description,
            url=gateway_url,
            version=agent.version or "1.0.0",
            provider={"organization": agent.tenant_id or "soorma"},
            capabilities={
                "streaming": False,
                "pushNotifications": True,
            },
            skills=[
                A2ASkill(
                    id=cap.task_name,
                    name=cap.task_name,
                    description=cap.description,
                    inputSchema=cap.consumed_event.payload_schema if hasattr(cap, 'consumed_event') else None,
                )
                for cap in agent.capabilities
            ],
            authentication=auth,
        )
    
    @staticmethod
    def task_to_event(
        task: A2ATask,
        event_type: str,
        response_event: str,
    ) -> ActionRequestEvent:
        """Convert A2A Task to internal action-request event."""
        # Extract text/data from message parts
        data = {}
        for part in task.message.parts:
            if part.type == "text":
                data["text"] = part.text
            elif part.type == "data":
                data.update(part.data or {})
        
        return ActionRequestEvent(
            source="gateway",
            type=event_type,
            data=data,
            correlation_id=task.id,
            session_id=task.sessionId,
            response_event=response_event,
        )
    
    @staticmethod
    def event_to_response(
        event: ActionResultEvent,
        task_id: str,
    ) -> A2ATaskResponse:
        """Convert internal action-result to A2A response."""
        if event.success:
            return A2ATaskResponse(
                id=task_id,
                status=A2ATaskStatus.COMPLETED,
                message=A2AMessage(
                    role="agent",
                    parts=[A2APart(type="data", data=event.result)],
                ),
            )
        else:
            return A2ATaskResponse(
                id=task_id,
                status=A2ATaskStatus.FAILED,
                error=event.error,
            )
```

---

## Usage Examples

### Internal Discovery (LLM Reasoning)

```python
@worker.on_task(event_type="complex.task")
async def handle_complex(task: TaskContext, context: PlatformContext):
    # Discover agents that can help with this task
    agents = await context.registry.discover(
        requirements=["text_analysis", "summarization"],
        include_events=True,
    )
    
    # LLM can reason about available capabilities
    for agent in agents:
        schema = agent.get_consumed_event_schema("text_analysis")
        # Use schema to generate appropriate request payload
```

### External A2A Gateway

```python
# Gateway service endpoint
@app.get("/.well-known/agent.json")
async def get_agent_card():
    agent = await registry.get_agent(agent_id="my-agent")
    return A2AGatewayHelper.agent_to_card(
        agent=agent,
        gateway_url="https://my-gateway.example.com",
        auth=A2AAuthentication(schemes=["oauth2"]),
    )

@app.post("/tasks/send")
async def send_task(task: A2ATask):
    event = A2AGatewayHelper.task_to_event(
        task=task,
        event_type="my.task.requested",
        response_event=f"task.{task.id}.completed",
    )
    await bus.publish(topic="action-requests", **event.dict())
```

---

## Tests to Add

```python
# test/test_discovery.py

async def test_discover_returns_agents_with_capabilities():
    """discover() should return agents matching requirements."""
    pass

async def test_discover_includes_event_schemas():
    """discover() with include_events=True should include schemas."""
    pass

async def test_discovered_agent_get_schema():
    """DiscoveredAgent should provide schema access methods."""
    pass

# test/test_gateway.py

async def test_agent_to_card():
    """agent_to_card should convert AgentDefinition to A2A format."""
    pass

async def test_task_to_event():
    """task_to_event should convert A2A Task to internal event."""
    pass

async def test_event_to_response():
    """event_to_response should convert result to A2A format."""
    pass
```

---

### RF-SDK-017: EventSelector Utility for LLM Event Selection

**Files:** New file `sdk/python/soorma/ai/selection.py`

#### Motivation

Examples `03-events-structured` and `research-advisor` have ~150 lines of similar boilerplate:
- Discover events from Registry
- Format events for LLM prompts
- Call LLM with structured prompts
- Validate LLM-selected events
- Publish selected events

This pattern repeats across multiple examples and should be SDK convenience.

#### Target Design

```python
# sdk/python/soorma/ai/selection.py
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from litellm import completion
import json

from soorma.context import PlatformContext
from soorma.registry import EventDefinition

class EventDecision(BaseModel):
    """Type-safe LLM event selection result."""
    event_type: str = Field(description="Selected event type")
    payload: Dict[str, Any] = Field(description="Event payload data")
    reasoning: str = Field(description="LLM explanation")
    confidence: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Confidence score"
    )
    
    @classmethod
    def model_json_schema(cls) -> Dict[str, Any]:
        """Get JSON schema for LLM prompts."""
        return cls.model_json_schema()

class EventSelector:
    """
    LLM-based event selection utility.
    
    Provides agent-customizable prompt templates for domain-specific routing.
    """
    
    def __init__(
        self,
        context: PlatformContext,
        topic: str,
        prompt_template: str,
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
    ):
        """
        Args:
            context: Platform context for registry access
            topic: Topic to discover events from
            prompt_template: Domain-specific business logic prompt with {{state}} and {{events}} placeholders.
                            Schema instruction is automatically appended by the utility.
            model: LLM model to use
            temperature: LLM temperature
        """
        self.context = context
        self.topic = topic
        self.prompt_template = prompt_template
        self.model = model
        self.temperature = temperature
        self._discovered_events: Optional[List[EventDefinition]] = None
    
    async def select_event(
        self,
        state: Dict[str, Any],
        filters: Optional[Dict[str, Any]] = None,
    ) -> EventDecision:
        """
        Use LLM to select best event based on state.
        
        Args:
            state: Current state data (e.g., ticket data, user query)
            filters: Optional filters for event discovery
        
        Returns:
            EventDecision with validated event and payload
        """
        # Discover events (cached)
        if self._discovered_events is None:
            self._discovered_events = await self.context.registry.discover(
                topic=self.topic,
                filters=filters,
            )
        
        # Format events for LLM
        events_text = self._format_events_for_llm(self._discovered_events)
        
        # Build business logic prompt from user template
        prompt = self.prompt_template.replace(
            "{{state}}", json.dumps(state, indent=2)
        ).replace(
            "{{events}}", events_text
        )
        
        # Append schema instruction (utility implementation detail)
        decision_schema = EventDecision.model_json_schema()
        prompt += f"\n\nRespond with JSON matching this schema:\n{json.dumps(decision_schema, indent=2)}"
        
        # Call LLM
        response = completion(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
            response_format={"type": "json_object"},
        )
        
        # Parse and validate
        decision_data = json.loads(response.choices[0].message.content)
        decision = EventDecision(**decision_data)
        
        # Validate event exists
        event_types = [e.event_type for e in self._discovered_events]
        if decision.event_type not in event_types:
            raise ValueError(
                f"LLM selected invalid event '{decision.event_type}'. "
                f"Available: {event_types}"
            )
        
        return decision
    
    async def publish_decision(
        self,
        decision: EventDecision,
        correlation_id: Optional[str] = None,
        response_event: Optional[str] = None,
    ):
        """Publish selected event."""
        await self.context.bus.publish(
            topic=self.topic,
            event_type=decision.event_type,
            data=decision.payload,
            correlation_id=correlation_id,
            response_event=response_event,
        )
    
    def _format_events_for_llm(self, events: List[EventDefinition]) -> str:
        """Format events for LLM consumption (delegates to EventToolkit)."""
        from soorma.registry import EventToolkit
        return EventToolkit.format_for_llm_selection(events)
```

#### Usage Example

```python
# Example: Ticket routing agent
from soorma.ai.selection import EventSelector

# Domain-specific prompt template (agent provides business logic only)
# Schema instruction is automatically appended by EventSelector
ROUTING_PROMPT = """
You are a support ticket router. Analyze the ticket and select the best routing.

TICKET:
{{state}}

AVAILABLE ROUTES:
{{events}}

Select the best routing event and explain why.
"""

selector = EventSelector(
    context=context,
    topic="action-requests",
    prompt_template=ROUTING_PROMPT,
    model="gpt-4o-mini",
)

@worker.on_task("ticket.created")
async def route_ticket(task, context):
    # SDK handles: discovery, formatting, LLM call, validation
    decision = await selector.select_event(
        state={"ticket_data": task.data},
        filters={"category": "routing"},
    )
    
    # SDK validates event exists before publishing
    await selector.publish_decision(
        decision,
        correlation_id=task.correlation_id,
        response_event="ticket.routed",
    )
```

#### Benefits

- **Reduces boilerplate**: 150 lines → 20 lines
- **Customizable**: Agents provide domain-specific prompts
- **Type-safe**: Returns EventDecision (Pydantic)
- **Validated**: Prevents hallucinated events
- **Reusable**: Same pattern across all routing agents

---

### RF-SDK-018: EventToolkit.format_for_llm_selection()

**Files:** Update existing `sdk/python/soorma/registry.py` (EventToolkit class)

#### Motivation

Examples have repeated code for formatting events for LLM consumption:
```python
# Repeated in multiple examples
def format_events_for_llm(events: list[dict]) -> str:
    formatted = []
    for i, event in enumerate(events, 1):
        metadata = event.get("metadata", {})
        formatted.append(
            f"{i}. **{event['name']}**\n"
            f"   Description: {event['description']}\n"
            f"   Schema: {json.dumps(event.get('schema'), indent=2)}\n"
        )
    return "\n".join(formatted)
```

This should be a static method on EventToolkit.

#### Target Design

```python
# sdk/python/soorma/registry.py
from typing import List
from soorma.registry import EventDefinition
import json

class EventToolkit:
    # ... existing methods ...
    
    @staticmethod
    def format_for_llm_selection(events: List[EventDefinition]) -> str:
        """
        Format events for LLM selection prompts.
        
        Args:
            events: List of EventDefinition objects
        
        Returns:
            Formatted string for LLM consumption
        """
        if not events:
            return "No events available."
        
        formatted = []
        for i, event in enumerate(events, 1):
            formatted.append(
                f"{i}. **{event.event_type}**\n"
                f"   Description: {event.description}\n"
                f"   Schema: {event.payload_schema_name}\n"
            )
            
            if event.examples:
                formatted.append(f"   Example: {json.dumps(event.examples[0], indent=2)}\n")
        
        return "\n".join(formatted)
```

#### Usage

```python
from soorma.registry import EventToolkit

events = await context.registry.discover(topic="action-requests")
events_text = EventToolkit.format_for_llm_selection(events)

prompt = f"""
Select the best event:

AVAILABLE EVENTS:
{events_text}
"""
```

---

## Implementation Checklist

### RF-SDK-007: Event Registration

- [ ] **Update** `AgentCapability` to include full `EventDefinition`
- [ ] **Update** Registry Service to store event ownership
- [ ] **Add** cleanup of owned events on agent deregistration
- [ ] **Add** query events by agent endpoint
- [ ] **Write tests first** for event ownership tracking
- [ ] **Write tests first** for event cleanup on deregistration

### RF-SDK-008: Discovery & A2A

- [ ] **Add** `version` field to `AgentDefinition`
- [ ] **Write tests first** for RegistryClient.discover()
- [ ] **Implement** `RegistryClient.discover()` method
- [ ] **Write tests first** for DiscoveredAgent schema access
- [ ] **Implement** `DiscoveredAgent` dataclass with schema access
- [ ] **Create** `sdk/python/soorma/gateway.py`
- [ ] **Write tests first** for A2AGatewayHelper conversions
- [ ] **Implement** `A2AGatewayHelper` class
- [ ] **Add** A2A DTOs to `soorma-common` (see [03-COMMON-DTOS.md](03-COMMON-DTOS.md))

### RF-SDK-017: EventSelector Utility

- [ ] **Write tests first** for EventDecision validation:
  - [ ] Test valid decisions (all required fields)
  - [ ] Test invalid decisions (missing fields)
  - [ ] Test confidence score validation (0-1 range)
  - [ ] Test model_json_schema() returns valid JSON schema
- [ ] **Implement** EventDecision in `ai/selection.py`
- [ ] **Write tests first** for EventSelector:
  - [ ] Test select_event() discovers events (with caching)
  - [ ] Test select_event() formats events for LLM
  - [ ] Test select_event() appends schema instruction to user prompt
  - [ ] Test select_event() calls LLM with full prompt (business logic + schema)
  - [ ] Test select_event() parses LLM response to EventDecision
  - [ ] Test select_event() validates event exists in discovered events
  - [ ] Test select_event() raises error on hallucinated events
  - [ ] Test publish_decision() publishes with correct params
  - [ ] Test prompt template placeholder replacement (state, events only)
- [ ] **Implement** EventSelector class in `ai/selection.py`
- [ ] **Write integration tests** with mocked LLM responses
- [ ] **Write integration tests** with real Registry discovery
- [ ] **Update ticket routing example** to use EventSelector

### RF-SDK-018: EventToolkit LLM Helpers

- [ ] **Write tests first** for format_for_llm_selection():
  - [ ] Test empty events list returns "No events available"
  - [ ] Test single event formatting
  - [ ] Test multiple events formatting with numbering
  - [ ] Test schema name is included (not full schema)
  - [ ] Test examples are included when present
  - [ ] Test formatting matches expected structure
- [ ] **Implement** EventToolkit.format_for_llm_selection() in `registry.py`
- [ ] **Document** usage in docstrings

---

## Dependencies

- **Depends on:** [01-EVENT-SYSTEM.md](01-EVENT-SYSTEM.md) (event definitions)
- **Depends on:** [03-COMMON-DTOS.md](03-COMMON-DTOS.md) (A2A DTOs in common library)
- **Blocked by:** Nothing

---

## Open Questions

None currently - design is settled.

---

## Related Documents

- [00-OVERVIEW.md](00-OVERVIEW.md) - Progressive complexity model
- [03-COMMON-DTOS.md](03-COMMON-DTOS.md) - A2A DTOs in soorma-common
- [A2A Protocol](https://google.github.io/agent-to-agent/) - External reference
