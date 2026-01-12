# Architecture Refactoring: User-Agent Service

**Document:** 06-USER-AGENT.md  
**Status:** ⬜ Not Started  
**Priority:** 🟢 Low (Phase 4)  
**Last Updated:** January 11, 2026

---

## Quick Reference

| Aspect | Details |
|--------|----------|
| **Task** | RF-ARCH-002: HITL Pattern |
| **Files** | User-Agent Service (new) |
| **Pairs With SDK** | N/A (service-only) |
| **Dependencies** | 01-EVENT-SERVICE |
| **Blocks** | None |
| **Estimated Effort** | 3-5 days |

---

## Context

### Why This Matters

User-Agent Service bridges **autonomous agents and humans**:

1. **HITL (Human-in-the-Loop)** - Request human input during execution
2. **Goal submission** - UI submits user goals to appropriate agents
3. **Progress notifications** - Push updates to users
4. **Chat interface** - Conversational interaction with agents

### Key Files

```
services/user-agent/      # NEW SERVICE
├── src/
│   ├── subscribers/      # Listen to notification-events
│   ├── routes/           # UI APIs
│   └── websocket/        # Real-time notifications
```

---

## HITL Pattern

**RF-ARCH-002: Human-in-the-Loop Event Flow**

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

**Event Definition:**
```python
# Agent requests human input
await ctx.bus.publish(
    topic="notification-events",
    event_type="notification.human_input",
    data={
        "question": "Which data source?",
        "options": ["web", "database", "api"],
        "timeout_seconds": 300,
        "response_event": "user.selection.made",
    },
    correlation_id=task_id,
    response_event="user.selection.made",
)

# User-Agent forwards to UI, receives response, publishes
await ctx.bus.publish(
    topic="action-results",
    event_type="user.selection.made",
    data={"selection": "web"},
    correlation_id=task_id,
)
```

---

## Service Responsibilities

```
┌─────────────────────────────────────────────────────────────────┐
│                      User-Agent Service                          │
├─────────────────────────────────────────────────────────────────┤
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
│  - WebSocket /ws - Real-time updates                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Dependencies

- **Depends on:** 01-EVENT-SERVICE
- **Blocks:** None
- **Pairs with SDK:** N/A

---

## Related Documents

- [00-OVERVIEW.md](00-OVERVIEW.md) - Service responsibilities
- [01-EVENT-SERVICE.md](01-EVENT-SERVICE.md) - notification-events topic
