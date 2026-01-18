# Architecture Refactoring: Event Service

**Document:** 01-EVENT-SERVICE.md  
**Status:** ⬜ Not Started  
**Priority:** 🔴 High (Foundation)  
**Last Updated:** January 11, 2026

---

## Quick Reference

| Aspect | Details |
|--------|----------|
| **Tasks** | RF-ARCH-003: Response Event in Envelope, RF-ARCH-004: Correlation Strategy |
| **Files** | `soorma-common/events.py`, Event Service |
| **Pairs With SDK** | [sdk/01-EVENT-SYSTEM.md](../sdk/01-EVENT-SYSTEM.md) |
| **Dependencies** | None (foundational) |
| **Blocks** | All other architecture work |
| **Estimated Effort** | 2-3 days |

---

## Context

### Why This Matters

The Event Service envelope is the **foundation** of all inter-service and agent communication:

1. **Response routing** enables dynamic request/response patterns
2. **Distributed tracing** enables observability across complex workflows
3. **Correlation** enables matching requests with responses

### Current State

Event envelope has basic fields but lacks:
- Explicit response event routing
- Distributed tracing support (trace_id, parent_event_id)
- Clear correlation semantics

### Key Files

```
soorma-common/
└── events.py           # EventEnvelope

services/event-service/
└── src/
    └── models/         # Service-side envelope handling
```

---

## Summary

This document covers Event Service envelope enhancements:
- **RF-ARCH-003:** Add response_event to EventEnvelope
- **RF-ARCH-004:** Correlation ID semantics for distributed tracing

These changes must be coordinated with SDK [01-EVENT-SYSTEM.md](../sdk/01-EVENT-SYSTEM.md).

---

## Tasks

### RF-ARCH-003: Add Response Event to Envelope

**Files:** `soorma-common/events.py`, Event Service

#### Current Envelope

```python
class EventEnvelope(BaseDTO):
    id: str
    source: str
    specversion: str = "1.0"
    type: str  # event_type
    topic: str
    time: str
    data: Dict[str, Any]
    correlation_id: Optional[str]
    tenant_id: Optional[str]
    session_id: Optional[str]
    subject: Optional[str]
```

#### Target Envelope

```python
class EventEnvelope(BaseDTO):
    # ... existing fields ...
    
    # NEW: Response routing (DisCo pattern)
    response_event: Optional[str] = Field(
        None,
        description="Event type the callee should use for response"
    )
    response_topic: Optional[str] = Field(
        None,
        description="Topic for response (defaults to action-results)"
    )
    
    # NEW: Distributed tracing
    parent_event_id: Optional[str] = Field(
        None,
        description="ID of parent event for trace tree"
    )
    trace_id: Optional[str] = Field(
        None,
        description="Root trace ID for distributed tracing"
    )
```

#### Why These Fields?

**DisCo Pattern (Dynamic Response Coupling):**
- **Problem:** Traditional pub/sub has static event names, tight coupling
- **Solution:** Caller specifies which event to use for response
- **Benefit:** Multiple concurrent requests, dynamic routing, loose coupling

**Example:**
```python
# Planner makes multiple web search requests
await bus.publish(
    topic="action-requests",
    event_type="web.search.requested",
    data={"query": "AI trends"},
    correlation_id="task-1",
    response_event="task-1.search.done",  # Unique response event
)

await bus.publish(
    topic="action-requests",
    event_type="web.search.requested",
    data={"query": "ML frameworks"},
    correlation_id="task-2",
    response_event="task-2.search.done",  # Different response event
)
```

**Distributed Tracing:**
- `trace_id` - Set at root goal, propagated through all events
- `parent_event_id` - Immediate parent event for trace tree
- `correlation_id` - Used for response routing (matches parent's correlation)

---

### RF-ARCH-004: Correlation ID Semantics

**Files:** `soorma-common/events.py`, documentation

#### Proposed Hierarchy

```
trace_id (root goal)
├── plan_id
│   ├── task_id (correlation_id for task)
│   │   ├── sub_task_id_1 (correlation_id for sub-task)
│   │   └── sub_task_id_2
│   └── task_id_2
│       └── sub_task_id_3
└── ...
```

#### Field Semantics

| Field | Purpose | Set By | Example |
|-------|---------|--------|---------|
| `trace_id` | Root trace for entire workflow | Initial goal submitter | `trace-abc123` |
| `correlation_id` | Response routing identifier | Event publisher (requestor) | `task-456` |
| `parent_event_id` | Immediate parent in trace tree | Event publisher | `event-xyz789` |

#### Rules

1. **trace_id propagation:**
   - Set once at root goal submission
   - Copied to all subsequent events in the workflow
   - Never changes within a workflow

2. **correlation_id usage:**
   - Set by requestor to identify expected response
   - Response uses requestor's `correlation_id` for routing
   - Each sub-task gets its own `correlation_id`

3. **parent_event_id linking:**
   - Points to immediate parent event's `id`
   - Enables reconstruction of full trace tree
   - Used by Tracker for execution timeline

#### SDK Usage Example

**Note:** The SDK provides helper methods (`create_child_request()`, `create_response()`) to auto-propagate metadata. See [sdk/01-EVENT-SYSTEM.md](../sdk/01-EVENT-SYSTEM.md) for details. The example below shows manual propagation for demonstration of the EventEnvelope fields.

```python
# 1. User submits goal (creates trace)
goal_event = await bus.publish(
    topic="action-requests",
    event_type="research.goal",
    data={"topic": "AI trends"},
    trace_id=str(uuid4()),  # NEW TRACE
)

# 2. Planner creates tasks (propagates trace) - manual example
await bus.publish(
    topic="action-requests",
    event_type="web.search.requested",
    data={"query": "AI trends"},
    trace_id=goal_event.trace_id,      # PROPAGATE
    correlation_id=f"task-{task_id}",  # For response routing
    parent_event_id=goal_event.id,     # Link to parent
    response_event="web.search.completed",
)

# 3. Worker delegates sub-task (propagates trace) - manual example
await bus.publish(
    topic="action-requests",
    event_type="extract.entities",
    data={"text": "..."},
    trace_id=event.trace_id,           # PROPAGATE
    correlation_id=f"subtask-{sub_id}", # New correlation for sub
    parent_event_id=event.id,          # Link to parent task
    response_event="extract.entities.done",
)

# RECOMMENDED: Use SDK helper methods instead
# See sdk/01-EVENT-SYSTEM.md for create_child_request() and create_response()
child_envelope = bus.create_child_request(
    parent_event=goal_event,
    event_type="web.search.requested",
    data={"query": "AI trends"},
    response_event="web.search.completed",
)
await bus.publish_envelope(child_envelope)  # All metadata auto-propagated
```

---

## Implementation Steps

### Step 1: Update EventEnvelope (soorma-common)

**Current State:** `EventEnvelope` in `libs/soorma-common/src/soorma_common/events.py` currently has:
- CloudEvents standard: `id`, `source`, `specversion`, `type`, `time`, `data`, `subject`
- Soorma-specific: `correlation_id`, `topic`, `tenant_id`, `session_id`

**Missing fields that need to be added:**

```python
# libs/soorma-common/src/soorma_common/events.py
class EventEnvelope(BaseDTO):
    """Event envelope with response routing and tracing support."""
    
    # Existing fields (already implemented)
    id: str = Field(default_factory=lambda: str(uuid4()))
    source: str
    specversion: str = "1.0"
    type: str  # event_type
    topic: EventTopic  # Uses EventTopic enum
    time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data: Optional[Dict[str, Any]] = None
    
    # Existing optional fields (already implemented)
    correlation_id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: Optional[str] = None
    session_id: Optional[str] = None
    subject: Optional[str] = None
    
    # NEW: Response routing (TO BE ADDED)
    response_event: Optional[str] = Field(
        None,
        description="Event type for response (caller-specified)"
    )
    response_topic: Optional[str] = Field(
        None,
        description="Topic for response (defaults to action-results if not specified)"
    )
    
    # NEW: Schema reference (TO BE ADDED)
    payload_schema_name: Optional[str] = Field(
        None,
        description="Registered schema name for payload (enables dynamic schema lookup)"
    )
    
    # NEW: Distributed tracing (TO BE ADDED)
    parent_event_id: Optional[str] = Field(
        None,
        description="ID of parent event in trace tree"
    )
    trace_id: Optional[str] = Field(
        None,
        description="Root trace ID for entire workflow"
    )
```

**Note:** Both Event Service and SDK use this same EventEnvelope from `soorma-common`. The Event Service imports it directly in `services/event-service/src/models/schemas.py`:
```python
from soorma_common.events import EventEnvelope
EventPayload = EventEnvelope
```

### Step 2: Update Event Service

Event Service should:
1. Accept new fields in publish endpoint
2. Include new fields in SSE stream
3. No validation required (optional fields)

### Step 3: Update SDK BusClient

See SDK [01-EVENT-SYSTEM.md](../sdk/01-EVENT-SYSTEM.md) for SDK changes.

### Step 4: Update Examples

Update examples to use new fields:
- research-advisor: Add trace_id to goal submission
- hello-world: Show simple request/response with response_event

---

## Testing Strategy

### Unit Tests

```python
async def test_event_envelope_with_tracing():
    """EventEnvelope should support tracing fields."""
    envelope = EventEnvelope(
        source="test-agent",
        type="test.event",
        topic="action-requests",
        data={"test": "data"},
        trace_id="trace-123",
        parent_event_id="event-456",
        correlation_id="task-789",
        response_event="test.response",
    )
    
    assert envelope.trace_id == "trace-123"
    assert envelope.parent_event_id == "event-456"
    assert envelope.response_event == "test.response"

async def test_event_envelope_backwards_compatible():
    """EventEnvelope should work without new fields."""
    envelope = EventEnvelope(
        source="test-agent",
        type="test.event",
        topic="action-requests",
        data={"test": "data"},
    )
    
    assert envelope.trace_id is None
    assert envelope.response_event is None
```

### Integration Tests

```python
async def test_trace_propagation():
    """Trace ID should propagate through event chain."""
    trace_id = str(uuid4())
    
    # Publish root event
    root = await bus.publish(
        topic="action-requests",
        event_type="root.event",
        data={},
        trace_id=trace_id,
    )
    
    # Publish child event
    child = await bus.publish(
        topic="action-requests",
        event_type="child.event",
        data={},
        trace_id=root.trace_id,  # Propagate
        parent_event_id=root.id,  # Link
    )
    
    assert child.trace_id == trace_id
    assert child.parent_event_id == root.id
```

---

## Event Service Architecture Patterns

**Status:** ✅ **Already Implemented** - The Event Service already supports all three patterns through the `queue_group` parameter in `adapter.subscribe()`. This section documents how to use existing functionality.

The Event Service supports three critical messaging patterns:

### Pattern 1: Queue Behavior (Store-and-Forward)

**Requirement:** Offline consumers should receive events when they reconnect.

**Current Implementation:** Event Service uses the underlying broker's durable subscription features. Each consumer with a `queue_group` maintains message persistence.

**How to Use:**
```python
# Subscribe with queue_group for durable subscription
await context.bus.subscribe(
    topics=["action-requests"],
    event_type="research.requested",
    handler=handle_research,
)
# When agent connects, it automatically receives any queued messages
```

**Broker-specific behavior:**
- **NATS:** Durable queue subscriptions persist messages until delivered
- **GCP Pub/Sub:** Subscriptions retain messages per retention policy
- **Memory Adapter:** Ephemeral (for testing only)

---

### Pattern 2: Broadcast/Fan-Out

**Requirement:** Multiple independent consumers receive same event (each consumer gets its own copy).

**Current Implementation:** Each agent subscription without a `queue_group` (or with unique `queue_group`) creates an independent consumer.

**How to Use:**
```python
# Agent A - gets all messages
await bus.subscribe(
    topics=["system-events"],
    event_type="task.progress",
    handler=handler_a,
)

# Agent B - also gets all messages (independent subscription)
await bus.subscribe(
    topics=["system-events"],
    event_type="task.progress",
    handler=handler_b,
)
```

**Note:** Event Service abstracts broker connections. Agents connect via Event Service API (HTTP/SSE), and Event Service manages broker subscriptions.

---

### Pattern 3: Load Balancing

**Requirement:** Multiple instances of same consumer agent share work (only one instance processes each message).

**Current Implementation:** Multiple agents using the **same `queue_group`** will have messages distributed among them (round-robin).

**How to Use:**
```python
# Instance 1 of research-worker
await bus.subscribe(
    topics=["action-requests"],
    event_type="research.requested",
    handler=handle_research,
    # queue_group automatically set to agent_name by EventClient
)

# Instance 2 of research-worker (same agent_name)
await bus.subscribe(
    topics=["action-requests"],
    event_type="research.requested",
    handler=handle_research,
    # Same queue_group = load balanced
)
```

**Implementation Detail:** In `event_manager.py`, line 135:
```python
# Use agent_name as queue_group if provided, otherwise fallback to agent_id.
# This enables load balancing across multiple instances of the same logical agent.
queue_group = agent_name if agent_name else agent_id
```

**See Tests:** `services/event-service/tests/test_queue_groups.py` demonstrates all patterns.

---

## Design Principles

The Event Service provides an **abstraction layer** between agents and message broker:

1. **Broker Portability** - Switch brokers (NATS ↔ GCP Pub/Sub) without changing agent code
2. **Security & Auth** - Centralized access control via Event Service API
3. **Protocol Flexibility** - Agents use HTTP/SSE, Event Service handles broker protocols
4. **Pattern Support** - Queue groups, broadcast, and load balancing work at broker level

---

## Open Questions

### Q1: Event Versioning Strategy
**Question:** How to handle event schema evolution?

**Options:**
- A) Version in event name: `research.requested.v2`
- B) Version in payload: `{ "version": 2, ... }`
- C) Schema registry with compatibility checks

**Current Leaning:** Option B for MVP, migrate to C for production

**Decision:** Defer to Phase 3 (Discovery)

---

### Q2: Multi-Tenancy Enforcement
**Question:** How to enforce tenant isolation in event routing?

**Current:** `tenant_id` in envelope, services filter by tenant

**Concern:** What prevents agent from publishing to wrong tenant?

**Options:**
- A) Trust agents (current)
- B) Event Service validates tenant from auth token
- C) Separate topic per tenant (doesn't scale)

**Recommendation:** Option B - Event Service should validate

**Decision:** Defer to Gateway implementation

---

### Q3: Event Retention & Replay
**Question:** How long to retain events? Support replay?

**Options:**
- A) Ephemeral only (no retention)
- B) Time-based retention (e.g., 7 days)
- C) Selective retention (only business-facts)

**Recommendation:** Option B for MVP, configurable per topic

**Decision:** Defer to Tracker service design

---

## Dependencies

- **Depends on:** Nothing (foundational)
- **Blocks:** All other architecture and SDK work
- **Pairs with SDK:** [sdk/01-EVENT-SYSTEM.md](../sdk/01-EVENT-SYSTEM.md)

---

## Related Documents

- [00-OVERVIEW.md](00-OVERVIEW.md) - Service responsibilities
- [../sdk/01-EVENT-SYSTEM.md](../sdk/01-EVENT-SYSTEM.md) - SDK BusClient changes
- [04-TRACKER-SERVICE.md](04-TRACKER-SERVICE.md) - Uses trace_id for observability
