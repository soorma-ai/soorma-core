# Soorma Architecture Refactoring Plan

**Status:** 📋 Planning  
**Last Updated:** January 11, 2026  
**Authors:** Architecture Team

---

## 1. Executive Summary

This document outlines architectural refactoring decisions for the Soorma platform services and overall design. It complements the SDK Refactoring Plan and focuses on cross-cutting concerns, service responsibilities, and communication patterns.

**Key Principles:**
- Event-driven architecture (agents communicate via events, not API calls)
- Services are passive listeners (consume events, update state)
- Clear separation of concerns between services
- Progressive disclosure (simple → discoverable → autonomous)
- Industry standards where applicable

---

## 2. Service Responsibilities

### 2.1 Current Service Map

| Service | Current Role | Issues |
|---------|--------------|--------|
| **Registry** | Agent & event registration, discovery | Events not tied to agents |
| **Event Service** | Pub/sub backbone (NATS proxy) | Works well |
| **Memory** | CoALA memory (semantic, episodic, procedural, working) | Good foundation |
| **Tracker** | (Planned) Observability, state machine tracking | Not implemented |
| **Gateway** | (Planned) API gateway, auth | Not implemented |

### 2.2 Target Service Responsibilities

```
┌─────────────────────────────────────────────────────────────────┐
│                        External Clients                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Gateway Service                              │
│  - Authentication / Authorization                                │
│  - Rate limiting                                                 │
│  - Request routing                                               │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│   Registry    │    │ Event Service │    │    Memory     │
│  - Agents     │    │  - Pub/Sub    │    │  - Semantic   │
│  - Events     │    │  - SSE        │    │  - Episodic   │
│  - Discovery  │    │  - JetStream  │    │  - Procedural │
└───────────────┘    └───────────────┘    │  - Working    │
                              │           └───────────────┘
                              │
                     ┌────────┴────────┐
                     ▼                 ▼
              ┌───────────┐     ┌───────────┐
              │  Tracker  │     │ User-Agent│
              │ (Passive) │     │  (HITL)   │
              └───────────┘     └───────────┘
```

---

## 3. Event Communication Model

### 3.1 Topic Structure (Current)

Current topics defined in `soorma-common`:
- `action-requests` - Agent-to-agent task delegation
- `action-results` - Task completion responses
- `business-facts` - Domain events / facts
- `system-events` - Platform lifecycle events
- `notification-events` - User notifications
- `billing` - Billing events
- `audit-events` - Audit trail

### 3.2 Topic Usage Clarification

#### RF-ARCH-001: Clarify `business-facts` Purpose
**Issue:** Business-facts conflated with user goals

**Resolution:**
| Topic | Purpose | Examples |
|-------|---------|----------|
| `business-facts` | Public service announcements, domain observations | `order.placed`, `inventory.low`, `customer.registered` |
| `action-requests` | Inter-agent work delegation, INCLUDING user goals | `research.goal`, `analyze.requested`, `summarize.task` |
| `action-results` | Task completion responses | `research.completed`, `analyze.result` |

**User Goals:** User-submitted goals go to `action-requests` topic, routed to appropriate Planner agent. `business-facts` is purely for announcing facts that any interested party can react to.

---

#### RF-ARCH-002: HITL (Human-in-the-Loop) Pattern
**Question:** How should agents request human input?

**Proposed Design:**

1. **User-Agent Service** (new core service)
   - Registers consumed events for HITL on `notification-events` topic
   - Manages human input/response flow
   - Bridges to UI/notification channels

2. **HITL Event Flow:**
```
Agent                     User-Agent                    Human
  │                           │                           │
  │ notification.human_input  │                           │
  │──────────────────────────>│                           │
  │  (question, options,      │ Push notification         │
  │   response_event)         │──────────────────────────>│
  │                           │                           │
  │                           │        User response      │
  │                           │<──────────────────────────│
  │  {response_event}         │                           │
  │<──────────────────────────│                           │
```

3. **Event Definitions:**
```python
# Request human input
HUMAN_INPUT_REQUEST = EventDefinition(
    event_name="notification.human_input",
    topic=EventTopic.NOTIFICATION_EVENTS,
    description="Request human input/decision",
    payload_schema={
        "type": "object",
        "properties": {
            "question": {"type": "string"},
            "options": {"type": "array"},
            "timeout_seconds": {"type": "integer"},
            "response_event": {"type": "string"},  # Caller specifies
            "response_topic": {"type": "string"},
        }
    }
)
```

---

### 3.3 Event Envelope Enhancement

#### RF-ARCH-003: Add Response Event to Envelope
**Files:** `soorma-common/events.py`, Event Service

**Current Envelope:**
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

**Target Envelope:**
```python
class EventEnvelope(BaseDTO):
    # ... existing fields ...
    
    # NEW: Response routing
    response_event: Optional[str] = Field(
        None,
        description="Event type the callee should use for response"
    )
    response_topic: Optional[str] = Field(
        None,
        description="Topic for response (defaults to action-results)"
    )
    
    # NEW: Tracing
    parent_event_id: Optional[str] = Field(
        None,
        description="ID of parent event for trace tree"
    )
    trace_id: Optional[str] = Field(
        None,
        description="Root trace ID for distributed tracing"
    )
```

---

### 3.4 Event Correlation Strategy

#### RF-ARCH-004: Correlation ID Semantics
**Question:** How do events correlate across plans, tasks, and sub-tasks?

**Proposed Hierarchy:**
```
trace_id (root)
├── plan_id
│   ├── task_id (correlation_id for task)
│   │   ├── sub_task_id_1
│   │   └── sub_task_id_2
│   └── task_id_2
└── ...
```

**Rules:**
1. `trace_id` - Set at the root goal, propagated through all events
2. `correlation_id` - Set by the event publisher, used for response routing
3. `parent_event_id` - ID of the immediate parent event (for trace tree)

**SDK Usage:**
```python
# Goal submission creates trace
await bus.publish(
    topic="action-requests",
    event_type="research.goal",
    data={"topic": "AI trends"},
    trace_id=str(uuid4()),  # New trace
)

# Planner creates plan, uses trace_id
await bus.publish(
    topic="action-requests",
    event_type="web.search.requested",
    data={...},
    trace_id=event.trace_id,  # Propagate trace
    correlation_id=plan.plan_id,  # For response routing
    parent_event_id=event.id,  # Parent is goal event
    response_event="web.search.completed",
)
```

---

## 4. Registry Service Refactoring

### 4.1 Event Registration Model

#### RF-ARCH-005: Events Tied to Agents
**Current:** Events registered flat, no ownership

**Target:** Events registered as part of agent capabilities

**Database Schema Change:**
```sql
-- Current: events table has no agent reference
CREATE TABLE events (
    id UUID PRIMARY KEY,
    event_name VARCHAR(255) UNIQUE,
    topic VARCHAR(100),
    description TEXT,
    payload_schema JSONB,
    response_schema JSONB
);

-- Target: events linked to agents
CREATE TABLE events (
    id UUID PRIMARY KEY,
    event_name VARCHAR(255),
    topic VARCHAR(100),
    description TEXT,
    payload_schema JSONB,
    response_schema JSONB,
    owner_agent_id UUID REFERENCES agents(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(event_name, owner_agent_id)  -- Same event name, different owners allowed
);
```

**API Changes:**
```python
# Register event with agent ownership
POST /v1/events
{
    "event": {
        "event_name": "research.requested",
        "topic": "action-requests",
        "description": "Request research on a topic",
        "payload_schema": {...}
    },
    "owner_agent_id": "researcher-agent-123"  # NEW
}

# Query events by owner
GET /v1/events?owner_agent_id=researcher-agent-123
```

---

### 4.2 Capability-Event Linkage

#### RF-ARCH-006: Structured Capability with Event Definitions
**Current:** Capabilities have event names as strings

```python
class AgentCapability(BaseDTO):
    task_name: str
    description: str
    consumed_event: str  # Just a name
    produced_events: List[str]  # Just names
```

**Target:** Capabilities include full event definitions

```python
class AgentCapability(BaseDTO):
    task_name: str
    description: str
    consumed_event: EventDefinition  # Full schema
    produced_events: List[EventDefinition]  # Full schemas
    
    # For LLM reasoning
    examples: Optional[List[Dict[str, Any]]] = None
    constraints: Optional[List[str]] = None
```

**Benefits:**
1. Single source of truth for capability ↔ event relationship
2. LLM can reason about payload schemas
3. Event cleanup on agent deregistration
4. Validation at registration time

---

### 4.3 Agent Discovery Enhancement

#### RF-ARCH-007: Discovery for LLM Reasoning
**Current:** Simple capability search

**Target:** Rich discovery with event schemas for autonomous agents

```python
# New API endpoint
GET /v1/agents/discover
Query params:
  - capabilities: List[str]  # Required capabilities
  - include_events: bool = true  # Include event schemas
  - include_examples: bool = false  # Include usage examples

Response:
{
    "agents": [
        {
            "agent_id": "research-worker-001",
            "name": "Research Worker",
            "description": "Performs web research",
            "capabilities": [
                {
                    "task_name": "web_research",
                    "description": "Search and summarize web content",
                    "consumed_event": {
                        "event_name": "web.research.requested",
                        "topic": "action-requests",
                        "payload_schema": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string"},
                                "max_results": {"type": "integer"}
                            },
                            "required": ["query"]
                        }
                    },
                    "produced_events": [
                        {
                            "event_name": "web.research.completed",
                            "payload_schema": {...}
                        }
                    ]
                }
            ]
        }
    ],
    "count": 1
}
```

---

## 5. Memory Service Refactoring

### 5.1 Working Memory for Task Context

#### RF-ARCH-008: TaskContext Memory Type
**Current:** Working memory keyed by `plan_id` + `key`

**Issue:** Need to persist `TaskContext` for async task completion

**Target:** Add explicit task context storage

```python
# New Memory Service endpoints

# Store task context
POST /v1/memory/task-context
{
    "task_id": "task-123",
    "plan_id": "plan-456",
    "context": {
        "event_type": "research.requested",
        "response_event": "research.completed",
        "response_topic": "action-results",
        "data": {...},
        "sub_tasks": [],
        "state": {}
    }
}

# Retrieve task context
GET /v1/memory/task-context/{task_id}

# Delete task context (on completion)
DELETE /v1/memory/task-context/{task_id}
```

**Schema:**
```sql
CREATE TABLE task_context (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    task_id VARCHAR(100) NOT NULL UNIQUE,
    plan_id VARCHAR(100),
    event_type VARCHAR(255),
    response_event VARCHAR(255),
    response_topic VARCHAR(100),
    data JSONB NOT NULL DEFAULT '{}',
    sub_tasks JSONB DEFAULT '[]',
    state JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX task_context_plan_idx ON task_context (plan_id);
ALTER TABLE task_context ENABLE ROW LEVEL SECURITY;
```

---

### 5.2 Plan/Session Query APIs

#### RF-ARCH-009: Query Active Plans/Sessions
**Question:** How to list active plans and sessions for a user?

**Resolution:** Memory Service provides this (not Tracker)

```python
# List active plans for user
GET /v1/memory/plans?user_id={user_id}&status=active

Response:
{
    "plans": [
        {
            "plan_id": "plan-123",
            "goal_event": "research.goal",
            "status": "running",
            "created_at": "2026-01-11T10:00:00Z",
            "task_count": 3,
            "completed_tasks": 1
        }
    ]
}

# List sessions/conversations for user
GET /v1/memory/sessions?user_id={user_id}&limit=10

Response:
{
    "sessions": [
        {
            "session_id": "sess-456",
            "agent_id": "research-advisor",
            "created_at": "2026-01-11T09:00:00Z",
            "last_interaction": "2026-01-11T10:30:00Z",
            "message_count": 15
        }
    ]
}
```

---

## 6. Tracker Service Design

### 6.1 Passive Event Consumer

#### RF-ARCH-010: Tracker as Event Listener
**Principle:** Tracker does NOT expose APIs for writing. It consumes events.

**Event Sources:**
- `system-events` topic: Agent lifecycle, task progress
- `action-requests` topic: Task starts
- `action-results` topic: Task completions

**Tracker Subscriptions:**
```python
# Tracker subscribes to system-events
@tracker.on_event(topic="system-events", event_type="task.progress")
async def track_progress(event):
    await db.update_task_progress(
        task_id=event["data"]["task_id"],
        status=event["data"]["status"],
        progress=event["data"]["progress"],
    )

@tracker.on_event(topic="action-results", event_type="*")
async def track_completion(event):
    await db.record_task_completion(
        task_id=event["correlation_id"],
        result=event["data"],
    )
```

**Read APIs (Tracker exposes):**
```python
# Query plan execution status
GET /v1/tracker/plans/{plan_id}

# Query task history
GET /v1/tracker/plans/{plan_id}/tasks

# Query execution timeline
GET /v1/tracker/plans/{plan_id}/timeline

# Query overall metrics
GET /v1/tracker/metrics?agent_id={agent_id}&period=7d
```

---

### 6.2 Progress Granularity

#### RF-ARCH-011: Task Progress Model
**Question:** State transitions only, or finer-grained progress?

**Resolution:** Support both

**Progress Events:**
```python
# State transition (coarse)
await bus.publish(
    topic="system-events",
    event_type="task.state_changed",
    data={
        "task_id": "task-123",
        "plan_id": "plan-456",
        "previous_state": "pending",
        "new_state": "running",
    }
)

# Progress update (fine-grained, optional)
await bus.publish(
    topic="system-events",
    event_type="task.progress",
    data={
        "task_id": "task-123",
        "plan_id": "plan-456",
        "state": "running",
        "progress": 0.5,  # 50%
        "message": "Processing document 3 of 6",
    }
)
```

**Task States:**
- `pending` - Task created, not started
- `running` - Task in progress
- `delegated` - Task delegated to sub-agent
- `waiting` - Waiting for sub-task results
- `completed` - Successfully completed
- `failed` - Failed with error
- `cancelled` - Cancelled by user/system

---

## 7. User-Agent Service (New)

### 7.1 Purpose
Bridge between autonomous agents and human users for:
- HITL (Human-in-the-Loop) interactions
- Goal submission from UI
- Progress notifications to users
- Chat/conversation interface

### 7.2 Responsibilities

```
┌─────────────────────────────────────────────────────────────────┐
│                      User-Agent Service                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Consumes:                        Produces:                      │
│  - notification.human_input       - {response_event} (dynamic)  │
│  - notification.progress          - user.goal.submitted         │
│  - action-results (for user)      - user.message.sent           │
│                                                                  │
│  APIs (for UI):                                                  │
│  - POST /v1/goals - Submit goal                                 │
│  - POST /v1/messages - Send chat message                        │
│  - GET /v1/conversations - List conversations                   │
│  - GET /v1/notifications - Get pending HITL requests            │
│  - POST /v1/notifications/{id}/respond - Submit response        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 8. Implementation Phases

### Phase 1: Foundation (Weeks 1-2)
- [ ] RF-ARCH-003: Add response_event to EventEnvelope
- [ ] RF-ARCH-004: Implement correlation ID strategy
- [ ] RF-SDK-001: Remove topic inference from SDK
- [ ] RF-SDK-002: Add response_event to SDK publish

### Phase 2: Registry Enhancement (Weeks 3-4)
- [ ] RF-ARCH-005: Events tied to agents (schema migration)
- [ ] RF-ARCH-006: Structured capabilities with EventDefinition
- [ ] RF-ARCH-007: Enhanced discovery API

### Phase 3: Memory & Task Context (Weeks 5-6)
- [ ] RF-ARCH-008: TaskContext memory type
- [ ] RF-ARCH-009: Plan/session query APIs
- [ ] RF-SDK-004: Worker async task model

### Phase 4: Tracker Service (Weeks 7-8)
- [ ] RF-ARCH-010: Tracker as event listener
- [ ] RF-ARCH-011: Task progress model
- [ ] RF-SDK-009: Remove direct tracker API calls

### Phase 5: Planner & User-Agent (Weeks 9-10)
- [ ] RF-SDK-006: Planner on_goal and on_transition
- [ ] User-Agent service (basic HITL)
- [ ] RF-ARCH-002: HITL event pattern

---

## 9. Open Architecture Questions

### Q1: Event Versioning
**Question:** How to handle event schema evolution?

**Options:**
- A) Version in event name: `research.requested.v2`
- B) Version in payload: `{ "version": 2, ... }`
- C) Schema registry with compatibility checks

**Current Leaning:** Option B for simplicity, migrate to C for production

---

### Q2: Multi-Tenancy in Events
**Question:** How to enforce tenant isolation in event routing?

**Current:** `tenant_id` in envelope, services filter by tenant

**Concern:** What prevents agent from publishing to wrong tenant?

**Options:**
- A) Trust agents (current)
- B) Event Service validates tenant from auth token
- C) Separate topic per tenant (doesn't scale)

**Recommendation:** Option B - Event Service should validate

---

### Q3: Event Retention & Replay
**Question:** How long to retain events? Support replay?

**Options:**
- A) Ephemeral only (no retention)
- B) Time-based retention (e.g., 7 days)
- C) Selective retention (only business-facts)

**Recommendation:** Option B for MVP, configurable per topic

---

### Q4: Produced Events in Agent Registration
**Question:** Do we need `produced_events` if consumers define their response events?

**Analysis:**
- DisCo pattern: Caller specifies `response_event`
- Traditional: Publisher defines events, consumers discover

**Resolution:** Keep `produced_events` for:
1. Documentation / discoverability
2. `business-facts` publishers (no specific consumer)
3. Validation that agent publishes declared events

For `action-results`, the actual event is specified by caller via `response_event`.

---

## 10. Industry Standards Alignment

### A2A (Agent-to-Agent) Protocol
Reference: [Google A2A](https://google.github.io/agent-to-agent/)

**Relevant Concepts:**
- **Agent Card** - Agent discovery metadata (align with our AgentDefinition)
- **Task** - Unit of work (align with our TaskContext)
- **Artifact** - Intermediate/final outputs

**Action Items:**
- [ ] Review A2A Agent Card spec
- [ ] Evaluate alignment with AgentCapability
- [ ] Consider adopting A2A Task structure

### MCP (Model Context Protocol)
Reference: [Anthropic MCP](https://github.com/anthropics/model-context-protocol)

**Relevant Concepts:**
- Tool definitions with JSON Schema
- Resource abstraction

**Action Items:**
- [ ] Review MCP tool specification
- [ ] Consider alignment for Tool agent type

---

## 11. References

- [SDK_REFACTORING_PLAN.md](SDK_REFACTORING_PLAN.md) - SDK-specific refactoring
- [ARCHITECTURE.md](../ARCHITECTURE.md) - Platform architecture
- [TOPICS.md](TOPICS.md) - Topic definitions
- [Memory Service ARCHITECTURE.md](../../services/memory/ARCHITECTURE.md) - Memory service design
