# Event System: Technical Architecture

**Status:** ✅ Stage 1 Complete (January 17, 2026)  
**Last Updated:** February 15, 2026  
**Related Stages:** Stage 1 (RF-ARCH-003, RF-ARCH-004, RF-SDK-001, RF-SDK-002, RF-SDK-003, RF-SDK-013)

---

## Design Principles

### Event-Driven Architecture

Soorma uses event-driven choreography as the primary communication mechanism:

- **Loose coupling:** Agents don't call each other directly
- **Async by default:** No blocking operations
- **Scalable:** Add/remove agents without code changes
- **Observable:** All interactions are events that can be traced

### Fixed Topic Schema

Unlike generic message buses that allow arbitrary topics, Soorma enforces a strict schema:

```python
# From soorma_common.models
class EventTopic(str, Enum):
    ACTION_REQUESTS = "action-requests"
    ACTION_RESULTS = "action-results"
    BUSINESS_FACTS = "business-facts"
    NOTIFICATION_EVENTS = "notification-events"
    SYSTEM_EVENTS = "system-events"
    ORCHESTRATION_EVENTS = "orchestration-events"  # Future use
    BUSINESS_POLICIES = "business-policies"        # Future use
    AGENT_REGISTRY = "agent-registry"              # Future use
```

**Benefits:**
- Type safety (can't typo a topic name)
- Clear semantics (topic names reflect DisCo pattern)
- Discoverability (services understand event flow)
- Governance (changes require code, not ad-hoc)

### Explicit Over Implicit

**Stage 1 Key Decision:** Remove all topic inference

```python
# OLD (implicit topic - BAD)
await context.bus.publish("order.created", data={...})

# NEW (explicit topic - GOOD)
await context.bus.publish(
    topic=EventTopic.ACTION_REQUESTS,
    event_type="order.created",
    data={...}
)
```

**Rationale:** Magic inference is hard to debug and violates "explicit over implicit" principle.

---

## Event Service Design

### Architecture

```
┌─────────────┐
│   Agent 1   │──┐
└─────────────┘  │
                 │
┌─────────────┐  │    ┌─────────────────┐    ┌─────────────┐
│   Agent 2   │──┼───▶│  Event Service  │◀──▶│ NATS Server │
└─────────────┘  │    │  (FastAPI)      │    │ (JetStream) │
                 │    └─────────────────┘    └─────────────┘
┌─────────────┐  │             │
│   Agent 3   │──┘             │
└─────────────┘                ▼
                          SSE Stream
```

### Tech Stack

- **Frontend:** FastAPI HTTP proxy
- **Backend:** NATS JetStream (durable messaging)
- **Protocol:** Server-Sent Events (SSE) for streaming
- **Persistence:** JetStream provides at-least-once delivery

### Key Features

1. **SSE Streaming:** Agents subscribe via HTTP SSE connections
2. **Queue Groups:** Load balancing using agent_name as queue_group
3. **Topic-based Routing:** NATS subjects map to Soorma topics
4. **Persistent Storage:** JetStream retains messages for offline consumers
5. **Auto-reconnection:** Agents automatically reconnect on disconnect

### NATS Subject Mapping

```python
# Soorma topic → NATS subject
"action-requests" → "events.action-requests"
"business-facts" → "events.business-facts"
```

**Implementation:** `services/event-service/src/adapters/nats_adapter.py`

---

## EventEnvelope

### Stage 1 Enhancements (RF-ARCH-003, RF-ARCH-004)

**Added fields:**

```python
@dataclass
class EventEnvelope:
    # Existing fields
    id: str
    event_type: str
    topic: str
    timestamp: datetime
    data: Dict[str, Any]
    correlation_id: str
    
    # Stage 1 additions
    response_event: Optional[str] = None       # Caller-specified response
    response_topic: Optional[str] = None       # Where to publish response
    trace_id: Optional[str] = None             # Distributed tracing
    parent_event_id: Optional[str] = None      # Event hierarchy
    payload_schema_name: Optional[str] = None  # Schema for LLM lookup
    
    # Context
    tenant_id: str
    user_id: str
    source: str  # Agent/service that published
```

### Field Semantics

| Field | Purpose | Set By | Used By |
|-------|---------|--------|------|
| `response_event` | Caller specifies expected response event name | Caller | Responder publishes to this |
| `response_topic` | Topic for response (default: action-results) | Caller | Responder uses this topic |
| `trace_id` | Distributed tracing ID for entire workflow | First event in chain | All child events inherit |
| `parent_event_id` | Parent event in hierarchy | Child event | Tracing/debugging |
| `payload_schema_name` | Schema reference for LLM reasoning | Publisher | LLM looks up schema |

### Correlation Semantics (RF-ARCH-004)

```
Goal Event (trace_id: T1)
  ├─ Task 1 (trace_id: T1, parent: goal_id, correlation: task1_id)
  │   ├─ Sub-task A (trace_id: T1, parent: task1_id, correlation: subtask_a_id)
  │   └─ Sub-task B (trace_id: T1, parent: task1_id, correlation: subtask_b_id)
  └─ Task 2 (trace_id: T1, parent: goal_id, correlation: task2_id)
```

**Rules:**
- `trace_id`: Same for entire workflow (goal → tasks → sub-tasks)
- `correlation_id`: Unique per request (used to match responses)
- `parent_event_id`: Links child to immediate parent

---

## SDK BusClient

### Stage 1 Refactoring (RF-SDK-001, RF-SDK-002, RF-SDK-003, RF-SDK-013)

**File:** `sdk/python/soorma/context.py`

### Core Methods

#### publish() - Basic Publishing

```python
async def publish(
    self,
    topic: str,                    # Explicit (no inference)
    event_type: str,
    data: Dict[str, Any],
    correlation_id: Optional[str] = None,
    response_event: Optional[str] = None,  # Stage 1
    response_topic: Optional[str] = None,  # Stage 1
    trace_id: Optional[str] = None,        # Stage 1
    parent_event_id: Optional[str] = None, # Stage 1
) -> str:
    """Publish event to topic."""
    # Create EventEnvelope
    envelope = EventEnvelope(
        id=str(uuid4()),
        event_type=event_type,
        topic=topic,
        data=data,
        # ... populate all fields
    )
    
    # Send to Event Service
    await self._http_client.post(
        f"{self._base_url}/v1/events/publish",
        json=envelope.model_dump(mode="json")
    )
    
    return envelope.id
```

#### request() - Request with Response Event (RF-SDK-002)

```python
async def request(
    self,
    topic: str,
    event_type: str,
    data: Dict[str,Any],
    response_event: str,           # Required
    response_topic: str = "action-results",
    correlation_id: Optional[str] = None,
) -> str:
    """Publish action request with response routing."""
    return await self.publish(
        topic=topic,
        event_type=event_type,
        data=data,
        response_event=response_event,
        response_topic=response_topic,
        correlation_id=correlation_id or str(uuid4()),
    )
```

#### respond() - Publish Response (RF-SDK-002)

```python
async def respond(
    self,
    event_type: str,               # From request.response_event
    data: Dict[str, Any],
    correlation_id: str,           # From request
    topic: str = "action-results",
) -> str:
    """Publish response to original requester."""
    return await self.publish(
        topic=topic,
        event_type=event_type,
        data=data,
        correlation_id=correlation_id,
    )
```

#### announce() - Broadcast Event (RF-SDK-002)

```python
async def announce(
    self,
    event_type: str,
    data: Dict[str, Any],
    topic: str = "business-facts",
) -> str:
    """Broadcast domain event (no response expected)."""
    return await self.publish(
        topic=topic,
        event_type=event_type,
        data=data,
        correlation_id=str(uuid4()),
    )
```

### Event Creation Utilities (RF-SDK-013)

#### create_child_request()

```python
def create_child_request(
    self,
    parent_event: EventEnvelope,
    event_type: str,
    data: Dict[str, Any],
    response_event: str,
    response_topic: str = "action-results",
) -> Dict[str, Any]:
    """Create child request params with auto-propagated metadata."""
    return {
        "topic": "action-requests",
        "event_type": event_type,
        "data": data,
        "response_event": response_event,
        "response_topic": response_topic,
        "correlation_id": str(uuid4()),
        "trace_id": parent_event.trace_id,           # Inherited
        "parent_event_id": parent_event.id,          # Link to parent
        "tenant_id": parent_event.tenant_id,          # Inherited
        "user_id": parent_event.user_id,              # Inherited
    }
```

**Usage:**

```python
# Create child request
child_params = context.bus.create_child_request(
    parent_event=goal_event,
    event_type="web.search.requested",
    data={"query": "AI trends"},
    response_event="task-1.search.done",
)

# Publish with all metadata auto-propagated
await context.bus.request(**child_params)
```

#### create_response()

```python
def create_response(
    self,
    request_event: EventEnvelope,
    data: Dict[str, Any],
) -> Dict[str, Any]:
    """Create response params matching request."""
    return {
        "topic": request_event.response_topic or "action-results",
        "event_type": request_event.response_event,  # Caller-specified
        "data": data,
        "correlation_id": request_event.correlation_id,
        "trace_id": request_event.trace_id,
        "parent_event_id": request_event.id,
    }
```

---

## Messaging Patterns Implementation

### Pattern 1: Queue Behavior (Store-and-Forward)

**Implementation:** NATS JetStream with durable subscriptions

```python
# Event Service: Create durable subscription
sub = await self._client.subscribe(
    subject="events.action-requests",
    queue="worker-group",  # Durable queue group
)
```

**Behavior:**
- Messages persisted in JetStream
- Delivered when consumer reconnects
- At-least-once delivery guarantee

**Broker-Specific:**
- **NATS JetStream:** Durable queue subscriptions
- **GCP Pub/Sub:** Subscription retention policy
- **Memory Adapter:** Ephemeral (testing only)

### Pattern 2: Broadcast/Fan-Out

**Implementation:** Each agent creates independent subscription

```python
# Agent A creates subscription
await event_service.subscribe(
    topics=["system-events"],
    agent_name="logger",
    queue_group="logger",  # Unique queue_group
)

# Agent B creates subscription
await event_service.subscribe(
    topics=["system-events"],
    agent_name="analytics",
    queue_group="analytics",  # Different queue_group
)
```

**Behavior:**
- Each agent gets all messages
- Independent processing
- No interference between agents

### Pattern 3: Load Balancing

**Implementation:** Multiple agents share same queue_group

```python
# services/event-service/src/event_manager.py:135
queue_group = agent_name if agent_name else agent_id
```

**Behavior:**
- Agents with same name → same queue_group
- NATS distributes messages round-robin
- Only one instance processes each message

**Example:**

```python
# Three instances of "heavy-task-worker"
# All use queue_group="heavy-task-worker"
# Messages distributed 1→2→3→1→2→3...
```

**Tests:** `services/event-service/tests/test_queue_groups.py`

---

## Decorator Design (RF-SDK-003)

### on_event() Signature

**Stage 1 Change:** Require explicit topic parameter for base Agent

```python
# OLD (BAD)
@agent.on_event("order.placed")

# NEW (GOOD)
@agent.on_event(topic=EventTopic.BUSINESS_FACTS, event_type="order.placed")
```

### Higher Abstractions Have Defaults

```python
# Worker: action-requests implied
@worker.on_task("process.requested")

# Tool: action-requests implied
@tool.on_invoke("calculate.requested")

# Planner: orchestration-events implied
@planner.on_goal("research.goal")
```

**Design Rationale:** Base Agent requires explicit topic for clarity, but higher abstractions provide sensible defaults for their specific use cases.

---

## Multi-Tenancy

### Tenant Context Propagation

All events include tenant and user context:

```python
class EventEnvelope:
    tenant_id: str  # Isolates tenants
    user_id: str    # Tracks user/agent identity
```

### Enforcement

**Event Service:** Validates tenant_id from authentication context

```python
# services/event-service/src/api/routes.py
async def publish_event(
    event: EventEnvelope,
    tenant_id: str = Depends(get_tenant_id),  # From auth token
):
    # Override event.tenant_id with authenticated tenant
    event.tenant_id = tenant_id
    await event_manager.publish(event)
```

**Row-Level Security:** Memory Service enforces RLS at database level

---

## Implementation Status

### Stage 1: Foundation - Event System ✅

**Completion Date:** January 17, 2026

**Completed Tasks:**
- ✅ RF-ARCH-003: EventEnvelope enhancements
  - Added response_event, response_topic
  - Added trace_id, parent_event_id
  - Added payload_schema_name
- ✅ RF-ARCH-004: Correlation ID semantics
  - Defined trace_id vs correlation_id distinction
  - Event hierarchy with parent_event_id
- ✅ RF-SDK-001: Remove topic inference from BusClient
  - Explicit topic parameter required
  - No magic derivation from event name
- ✅ RF-SDK-002: Add response_event to action requests
  - request() method with response routing
  - respond() convenience method
  - announce() for broadcasts
- ✅ RF-SDK-003: Refactor on_event() signature
  - Require topic parameter for base Agent
  - Higher abstractions provide defaults
- ✅ RF-SDK-013: Event creation utilities
  - create_child_request() with auto-propagation
  - create_response() matching request
- ✅ Messaging patterns documented
  - Queue behavior (store-and-forward)
  - Broadcast/fan-out
  - Load balancing via queue_group
- ✅ Examples updated
  - 02-events-simple
  - 03-events-structured
- ✅ All tests passing (64/64)

**Test Coverage:**
- Event Service: 21 tests passing
- SDK Event Tests: 28 tests passing
- Integration Tests: 15 tests passing

**CHANGELOG:** Updated in Event Service, SDK, and soorma-common

---

## Performance Characteristics

### Throughput

- **NATS JetStream:** 10-100K messages/sec per topic
- **HTTP Proxy:** Limited by HTTP connections (~1K req/sec per instance)
- **SSE Streaming:** Real-time delivery (<10ms latency)

### Scalability

- **Horizontal:** Add Event Service replicas behind load balancer
- **Vertical:** NATS cluster with multiple nodes
- **Topic Partitioning:** Future enhancement

### Reliability

- **At-least-once delivery:** JetStream guarantees
- **Auto-reconnection:** SDK handles connection failures
- **Message retention:** Configurable (default: 24 hours)

---

## Related Documentation

- [README.md](./README.md) - User guide and patterns
- [Messaging Patterns](../MESSAGING_PATTERNS.md) - Detailed pattern examples
- [Agent Patterns](../agent_patterns/ARCHITECTURE.md) - Event subscription model
- [Event Service](../../services/event-service/README.md) - Service implementation
- [Refactoring Plan](../refactoring/arch/01-EVENT-SERVICE.md) - Stage 1 design decisions
