# SDK Refactoring: Discovery & A2A

**Document:** 07-DISCOVERY.md  
**Status:** ⬜ Not Started  
**Priority:** 🟡 Medium (Phase 3)  
**Last Updated:** January 11, 2026

---

## Quick Reference

| Aspect | Details |
|--------|----------|
| **Tasks** | RF-SDK-007: Event Registration, RF-SDK-008: Agent Discovery |
| **Files** | `sdk/python/soorma/context.py`, `sdk/python/soorma/gateway.py` |
| **Pairs With Arch** | [arch/05-REGISTRY-SERVICE.md](../arch/05-REGISTRY-SERVICE.md) |
| **Dependencies** | 01-EVENT-SYSTEM, 03-COMMON-DTOS |
| **Blocks** | None |
| **Estimated Effort** | 2-3 days |

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

These tasks enable LLM-driven agent discovery and external A2A compatibility.

---

## Tasks

### RF-SDK-007: Event Registration Tied to Agent

**Files:** [context.py](../../sdk/python/soorma/context.py), Registry Service

#### Current Issue

Events registered flat, no ownership relationship.

#### Target

Events registered as part of agent registration, with `agent_id` as owner.

```python
class AgentCapability(BaseDTO):
    task_name: str
    description: str
    consumed_event: EventDefinition  # ← Full definition, not just name
    produced_events: List[EventDefinition]  # ← Full definitions
```

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

## Implementation Checklist

### RF-SDK-007: Event Registration

- [ ] **Update** `AgentCapability` to include full `EventDefinition`
- [ ] **Update** Registry Service to store event ownership
- [ ] **Add** cleanup of owned events on agent deregistration
- [ ] **Add** query events by agent endpoint

### RF-SDK-008: Discovery & A2A

- [ ] **Add** `version` field to `AgentDefinition`
- [ ] **Implement** `RegistryClient.discover()` method
- [ ] **Implement** `DiscoveredAgent` dataclass with schema access
- [ ] **Create** `sdk/python/soorma/gateway.py`
- [ ] **Implement** `A2AGatewayHelper` class
- [ ] **Add** A2A DTOs to `soorma-common` (see [03-COMMON-DTOS.md](03-COMMON-DTOS.md))

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
