# SDK Refactoring: Event System

**Document:** 01-EVENT-SYSTEM.md  
**Status:** ⬜ Not Started  
**Priority:** 🔴 High (Foundation)  
**Last Updated:** January 11, 2026

---

## Quick Reference

| Aspect | Details |
|--------|----------|
| **Tasks** | RF-SDK-001, RF-SDK-002, RF-SDK-003 |
| **Files** | `sdk/python/soorma/context.py` |
| **Pairs With Arch** | [arch/01-EVENT-SERVICE.md](../arch/01-EVENT-SERVICE.md) |
| **Dependencies** | None (foundational) |
| **Blocks** | All other SDK documents |
| **Estimated Effort** | 2-3 days |

---

## Context

### Why This Matters

The Event System is the **foundation** of all agent communication:

1. **All agents** use `BusClient` to publish and subscribe to events
2. **Topic routing** determines which services receive events
3. **Response correlation** enables request/response patterns

### Current State

- `BusClient._infer_topic()` magically guesses topics from event names (error-prone)
- `response_event` is derived from request name, not explicit (inflexible)
- `on_event()` decorator doesn't require topic (inconsistent)

### Key Files

```
sdk/python/soorma/
├── context.py          # BusClient, PlatformContext
└── agents/
    ├── agent.py        # Base Agent with on_event()
    ├── worker.py       # Uses bus.publish()
    └── planner.py      # Uses bus.publish()
```

### Topic Structure

| Topic | Purpose | Example Events |
|-------|---------|----------------|
| `action-requests` | Request work from agents | `calculate.requested`, `research.goal` |
| `action-results` | Return results to requestor | `calculate.completed`, `research.done` |
| `business-facts` | Announce domain events | `order.created`, `user.registered` |
| `notification-events` | Notifications, HITL | `notification.human_input` |
| `system-events` | Observability, metrics | `task.progress`, `plan.started` |

---

## Summary

This document covers the foundational event system refactoring:
- **RF-SDK-001:** Remove topic inference from BusClient
- **RF-SDK-002:** Add response_event to action requests  
- **RF-SDK-003:** Refactor on_event() signature

These are **breaking changes** that must be completed first before other refactoring tasks.

---

## Tasks

### RF-SDK-001: Remove Topic Inference from BusClient

**Files:** [context.py](../../sdk/python/soorma/context.py#L705-L718)

#### Current (BAD)
```python
# BusClient._infer_topic() - REMOVE THIS
def _infer_topic(self, event_type: str) -> str:
    if event_type.endswith(".requested"):
        return "action-requests"
    # ... magic inference
```

#### Target
```python
async def publish(
    self,
    topic: str,          # ← REQUIRED, no default
    event_type: str,
    data: Dict[str, Any],
    correlation_id: Optional[str] = None,
    response_event: Optional[str] = None,  # ← NEW
) -> str:
```

#### Convenience Methods

To enforce contracts and reduce boilerplate:

```python
class BusClient:
    async def request(
        self,
        event_type: str,
        data: Dict[str, Any],
        response_event: str,  # ← REQUIRED for requests
        correlation_id: Optional[str] = None,
        response_topic: str = "action-results",
    ) -> str:
        """
        Publish to action-requests topic with mandatory response_event.
        Enforces the request/response contract.
        """
        return await self.publish(
            topic="action-requests",
            event_type=event_type,
            data=data,
            correlation_id=correlation_id,
            response_event=response_event,
            response_topic=response_topic,
        )
    
    async def respond(
        self,
        event_type: str,  # The response_event from original request
        data: Dict[str, Any],
        correlation_id: str,  # ← REQUIRED for responses
        topic: str = "action-results",
    ) -> str:
        """
        Publish to action-results topic with mandatory correlation_id.
        Enforces response correlation contract.
        """
        return await self.publish(
            topic=topic,
            event_type=event_type,
            data=data,
            correlation_id=correlation_id,
        )
    
    async def announce(
        self,
        event_type: str,
        data: Dict[str, Any],
        correlation_id: Optional[str] = None,
    ) -> str:
        """
        Publish to business-facts topic for domain events/observations.
        No response expected.
        """
        return await self.publish(
            topic="business-facts",
            event_type=event_type,
            data=data,
            correlation_id=correlation_id,
        )
```

#### Usage Examples
```python
# Action request (requires response_event)
await context.bus.request(
    event_type="research.requested",
    data={"topic": "AI trends"},
    response_event="research.completed",
)

# Action response (requires correlation_id)
await context.bus.respond(
    event_type="research.completed",
    data={"findings": [...]},
    correlation_id=request.correlation_id,
)

# Business fact announcement (no response needed)
await context.bus.announce(
    event_type="order.placed",
    data={"order_id": "123"},
)
```

#### Tests to Add
```python
# test/test_bus_client.py

def test_publish_requires_topic():
    """publish() should raise if topic not provided."""
    with pytest.raises(TypeError):
        await bus.publish(event_type="test.event", data={})

def test_publish_with_response_event():
    """publish() should include response_event in envelope."""
    event_id = await bus.publish(
        topic="action-requests",
        event_type="test.requested",
        data={},
        response_event="test.completed",
    )
    # Verify envelope contains response_event field
    
def test_request_requires_response_event():
    """request() should raise if response_event not provided."""
    with pytest.raises(TypeError):
        await bus.request(event_type="test.event", data={})

def test_respond_requires_correlation_id():
    """respond() should raise if correlation_id not provided."""
    with pytest.raises(TypeError):
        await bus.respond(event_type="test.result", data={})
```

---

### RF-SDK-002: Add Response Event to Action Requests

**Files:** [context.py](../../sdk/python/soorma/context.py), [events.py](../../sdk/python/soorma/events.py)

#### Rationale
When publishing an action request, the caller must specify which event type the callee should use for the response. This enables dynamic routing and decouples request/response contracts.

#### Current Event Envelope
```python
{
    "id": "evt_123",
    "type": "research.requested",
    "topic": "action-requests",
    "data": {...},
    "correlation_id": "corr_456"
}
```

#### Target Event Envelope
```python
{
    "id": "evt_123",
    "type": "research.requested",
    "topic": "action-requests",
    "data": {...},
    "correlation_id": "corr_456",
    "response_event": "research.completed",  # ← NEW
    "response_topic": "action-results"       # ← NEW (optional)
}
```

#### Tests to Add
```python
def test_action_request_includes_response_event():
    """Action requests should include response_event in envelope."""
    pass

def test_tool_publishes_to_specified_response_event():
    """Tool should publish result to the response_event from request."""
    pass

def test_worker_publishes_to_specified_response_event():
    """Worker should publish result to the response_event from request."""
    pass
```

---

### RF-SDK-003: Refactor on_event() Signature

**Files:** [base.py](../../sdk/python/soorma/agents/base.py#L277-L306)

#### Current
```python
@agent.on_event("data.requested")  # Only event_type
async def handler(event, context): ...
```

#### Target
```python
@agent.on_event(topic="action-requests", event_type="data.requested")
async def handler(event, context): ...

# OR for convenience with defaults
@agent.on_event("data.requested", topic="business-facts")  # topic has default
```

#### Design Decision
- **Option A:** Always require topic (explicit)
- **Option B:** Require topic for base Agent, higher abstractions (Worker, Tool) have defaults
- **Recommendation:** Option B - progressive disclosure

| Agent Type | Default Topic | Requires Explicit Topic |
|------------|---------------|------------------------|
| `Agent` | None | Yes |
| `Tool` | `action-requests` | No |
| `Worker` | `action-requests` | No |
| `Planner` | `action-requests` | No |

#### Tests to Add
```python
def test_on_event_requires_topic_for_base_agent():
    """Base Agent.on_event() should require topic parameter."""
    agent = Agent(name="test")
    
    with pytest.raises(TypeError):
        @agent.on_event("test.event")  # Missing topic
        async def handler(event, ctx): pass

def test_on_event_accepts_topic_keyword():
    """on_event() should accept topic as keyword argument."""
    agent = Agent(name="test")
    
    @agent.on_event(topic="business-facts", event_type="test.event")
    async def handler(event, ctx): pass
    
    # Verify subscription is registered with correct topic
```

---

## Implementation Checklist

- [ ] **Read existing code** in `context.py`, `events.py`, `base.py`
- [ ] **Write tests first** for RF-SDK-001
- [ ] **Implement** RF-SDK-001: Remove `_infer_topic()`, add convenience methods
- [ ] **Write tests first** for RF-SDK-002
- [ ] **Implement** RF-SDK-002: Add `response_event` to envelope
- [ ] **Write tests first** for RF-SDK-003
- [ ] **Implement** RF-SDK-003: Update `on_event()` signature
- [ ] **Update examples** to use new patterns
- [ ] **Update tests** that relied on old behavior

---

## Dependencies

- **Depends on:** Nothing (foundation)
- **Blocks:** All other SDK refactoring tasks

---

## Open Questions

None currently - design is settled.

---

## Related Documents

- [00-OVERVIEW.md](00-OVERVIEW.md) - Context and principles
- [05-WORKER-MODEL.md](05-WORKER-MODEL.md) - Uses these event patterns
