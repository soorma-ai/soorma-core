# Soorma Platform Topics

## Overview

The Soorma platform uses a fixed set of **well-defined topics** for event-driven communication between agents and services. Unlike generic message buses that allow arbitrary topic names, Soorma enforces a strict topic schema to ensure:

- **Type safety**: Each topic has specific event DTOs
- **Clear semantics**: Topic names reflect the DisCo (Distributed Cognition) pattern
- **Discoverability**: Services can understand event flow by topic name
- **Governance**: Changes to topics require code changes, preventing ad-hoc sprawl

All topics are defined in `soorma-common` library as the `EventTopic` enum.

## Core DisCo Topics

These topics implement the Distributed Cognition pattern for agentic orchestration:

### `action-requests`
**When to use**: Request another agent to perform an action (from planner or coordinator)

**Event type**: `ActionRequestEvent`

**Typical event_type patterns**:
- `research.requested`
- `analysis.requested`
- `tool.execute`

**Example**:
```python
await client.publish(
    event_type="research.requested",
    topic="action-requests",
    data={
        "query": "What are the latest ML trends?",
        "plan_id": "plan-123",
    }
)
```

**Who subscribes**: Worker agents that perform tasks

---

### `action-results`
**When to use**: Report results from completing an action (from worker back to planner)

**Event type**: `ActionResultEvent`

**Typical event_type patterns**:
- `research.completed`
- `analysis.completed`
- `tool.executed`

**Example**:
```python
await client.publish(
    event_type="research.completed",
    topic="action-results",
    data={
        "action_event_id": "evt-456",
        "success": True,
        "result": {"findings": "..."},
    }
)
```

**Who subscribes**: Planner agents that initiated the action

---

### `business-facts`
**When to use**: Announce business domain observations, state changes, or facts

**Event type**: `BusinessFactEvent`

**Typical event_type patterns**:
- `order.placed`
- `inventory.low`
- `customer.registered`
- `payment.received`

**Example**:
```python
await client.publish(
    event_type="order.placed",
    topic="business-facts",
    data={
        "order_id": "ORD-001",
        "customer": "Alice",
        "total": 1500.00,
    }
)
```

**Who subscribes**: Any agent interested in domain events (for choreography patterns)

---

## System Topics

These topics are for platform-level concerns:

### `system-events`
**When to use**: Platform lifecycle events (startup, shutdown, health)

**Typical event_type patterns**:
- `agent.started`
- `agent.stopped`
- `service.unhealthy`

**Example**:
```python
await client.publish(
    event_type="agent.started",
    topic="system-events",
    data={
        "agent_id": "worker-001",
        "capabilities": ["research", "analysis"],
    }
)
```

**Who subscribes**: Platform monitoring and orchestration services

---

### `notification-events`
**When to use**: Send user-facing notifications (email, SMS, push)

**Typical event_type patterns**:
- `notification.email`
- `notification.sms`
- `alert.triggered`

**Example**:
```python
await client.publish(
    event_type="notification.email",
    topic="notification-events",
    data={
        "recipient": "user@example.com",
        "subject": "Your order has shipped",
        "body": "...",
    }
)
```

**Who subscribes**: Notification services (email gateway, SMS gateway, etc.)

---

### `billing-events`
**When to use**: Track usage and costs for billing/metering

**Event type**: `BillingEvent`

**Typical event_type patterns**:
- `usage.llm_tokens`
- `usage.api_call`
- `usage.storage`

**Example**:
```python
await client.publish(
    event_type="usage.llm_tokens",
    topic="billing-events",
    data={
        "unit_of_work": "gpt-4-turbo request",
        "tokens": 1250,
        "cost_usd": 0.025,
    }
)
```

**Who subscribes**: Billing and analytics services

---

## Plan Orchestration Topics

These topics support workflow and plan execution:

### `plan-events`
**When to use**: Plan lifecycle events (creation, updates, completion)

**Typical event_type patterns**:
- `plan.created`
- `plan.updated`
- `plan.completed`
- `plan.failed`

**Example**:
```python
await client.publish(
    event_type="plan.created",
    topic="plan-events",
    data={
        "plan_id": "plan-123",
        "goal": "Research and summarize AI trends",
        "steps": [...],
    }
)
```

**Who subscribes**: Plan orchestrators, dashboards, workflow engines

---

### `task-events`
**When to use**: Individual task lifecycle within a plan

**Typical event_type patterns**:
- `task.started`
- `task.completed`
- `task.failed`
- `task.retry`

**Example**:
```python
await client.publish(
    event_type="task.completed",
    topic="task-events",
    data={
        "task_id": "task-456",
        "plan_id": "plan-123",
        "result": {...},
    }
)
```

**Who subscribes**: Plan orchestrators, progress tracking services

---

## Topic Selection Decision Tree

```
┌─────────────────────────────────────────┐
│ What are you publishing?                │
└──────────────────┬──────────────────────┘
                   │
    ┌──────────────┴──────────────┐
    │                             │
    ▼                             ▼
Request for another          Report/Observation
agent to do work?            of domain state?
    │                             │
    │                             │
    ▼                             ▼
action-requests              business-facts
    │                             │
    │                             │
Response from               ┌─────┴─────┐
completing work?            │           │
    │                       │           │
    ▼                       ▼           ▼
action-results        Platform      User-facing
                      lifecycle?    notification?
                          │              │
                          │              │
                          ▼              ▼
                    system-events   notification-events
                          │
                          │
                   ┌──────┴──────┐
                   │             │
                   ▼             ▼
              Plan/task      Billing/
              tracking?      usage?
                   │             │
                   │             │
                   ▼             ▼
              plan-events   billing-events
              task-events
```

## Best Practices

### ✅ DO
- Use `action-requests` / `action-results` for agent coordination
- Use `business-facts` for domain events in choreography
- Use `plan-events` / `task-events` for workflow tracking
- Subscribe to topics using wildcard patterns: `["action-results", "business-facts"]`

### ❌ DON'T
- Don't create custom topics (e.g., "orders", "tickets", "payments")
- Don't use arbitrary topic names
- Don't bypass topic validation
- Don't mix concerns (e.g., billing data in action-requests)

## See Also

- [EVENT_PATTERNS.md](EVENT_PATTERNS.md) - Event-driven patterns
- [DESIGN_PATTERNS.md](DESIGN_PATTERNS.md) - Agent orchestration patterns
- `soorma-common/events.py` - Topic and event definitions
