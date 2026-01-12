# Architecture Refactoring: Registry Service

**Document:** 05-REGISTRY-SERVICE.md  
**Status:** ⬜ Not Started  
**Priority:** 🟡 Medium (Phase 3)  
**Last Updated:** January 11, 2026

---

## Quick Reference

| Aspect | Details |
|--------|----------|
| **Tasks** | RF-ARCH-005: Events Tied to Agents, RF-ARCH-006: Structured Capabilities, RF-ARCH-007: Enhanced Discovery |
| **Files** | Registry Service |
| **Pairs With SDK** | [sdk/07-DISCOVERY.md](../sdk/07-DISCOVERY.md) |
| **Dependencies** | 01-EVENT-SERVICE, 03-COMMON-LIBRARY |
| **Blocks** | None |
| **Estimated Effort** | 3-4 days |

---

## Context

### Why This Matters

Registry Service enables **dynamic agent discovery**:

1. **Event ownership** - Events tied to agents for lifecycle management
2. **Structured capabilities** - Full schemas for LLM reasoning
3. **Discovery API** - Find agents by capability with schemas

### Key Files

```
services/registry/
├── src/
│   ├── models/         # Agent/Event schemas
│   ├── routes/         # Registration, discovery APIs
│   └── db/            # Database layer
└── migrations/        # Schema changes
```

---

## Tasks

### RF-ARCH-005: Events Tied to Agents

Link events to their owning agents for cleanup and tracking.

**Database Schema:**
```sql
ALTER TABLE events ADD COLUMN owner_agent_id UUID REFERENCES agents(id) ON DELETE SET NULL;
ALTER TABLE events DROP CONSTRAINT events_event_name_key;
ALTER TABLE events ADD CONSTRAINT events_name_owner_unique UNIQUE(event_name, owner_agent_id);
```

### RF-ARCH-006: Structured Capabilities

Capabilities include full EventDefinition objects, not just names.

**Updated DTO:**
```python
class AgentCapability(BaseDTO):
    task_name: str
    description: str
    consumed_event: EventDefinition  # Full schema
    produced_events: List[EventDefinition]  # Full schemas
    examples: Optional[List[Dict[str, Any]]] = None
```

### RF-ARCH-007: Enhanced Discovery API

Discovery returns full schemas for LLM-based payload generation.

**New Endpoint:**
```python
GET /v1/agents/discover?capabilities=web_search&include_events=true

Response:
{
    "agents": [
        {
            "agent_id": "research-worker-001",
            "name": "Research Worker",
            "capabilities": [
                {
                    "task_name": "web_research",
                    "consumed_event": {
                        "event_name": "web.research.requested",
                        "payload_schema": {...}
                    },
                    "produced_events": [...]
                }
            ]
        }
    ]
}
```

See [sdk/07-DISCOVERY.md](../sdk/07-DISCOVERY.md) for SDK implementation.

---

## Dependencies

- **Depends on:** 01-EVENT-SERVICE, 03-COMMON-LIBRARY
- **Pairs with SDK:** [sdk/07-DISCOVERY.md](../sdk/07-DISCOVERY.md)

---

## Related Documents

- [00-OVERVIEW.md](00-OVERVIEW.md) - Service responsibilities
- [03-COMMON-LIBRARY.md](03-COMMON-LIBRARY.md) - A2A DTOs
- [../sdk/07-DISCOVERY.md](../sdk/07-DISCOVERY.md) - Discovery SDK methods
