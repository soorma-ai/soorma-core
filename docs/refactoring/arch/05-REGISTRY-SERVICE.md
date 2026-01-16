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

### RF-ARCH-005: Schema Registration by Name (Not Event Name)

**Critical Design Change:** Register **payload schemas by schema name**, not event name. This decouples schemas from dynamic event names.

**Why:** When LLM agents delegate to discovered agents with dynamic response_event names, they need to know the response payload schema. Since event names are now dynamic strings (caller-specified), schemas must be registered independently.

**Schema Registration:**
```python
class PayloadSchema(BaseDTO):
    schema_name: str  # e.g., "research_result_v1"
    version: str
    json_schema: Dict[str, Any]
    owner_agent_id: str
    description: Optional[str]
```

**Database Schema:**
```sql
CREATE TABLE payload_schemas (
    id UUID PRIMARY KEY,
    schema_name VARCHAR NOT NULL,
    version VARCHAR NOT NULL,
    json_schema JSONB NOT NULL,
    owner_agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(schema_name, version)
);

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
                    "description": "Performs web research on a given topic",
                    "consumed_event": {
                        "event_type": "web.research.requested",
                        "payload_schema_name": "research_request_v1",
                        "description": "Request for web research",
                        "examples": [{"topic": "AI trends", "max_results": 10}]
                    },
                    "produced_events": [
                        {
                            "event_type": "research.completed",  # Canonical/example type
                            "payload_schema_name": "research_result_v1",
                            "description": "Research results (actual event type from request's response_event)"
                        }
                    ]
                }
            ]
        }
    ]
}

# To get the actual schema, LLM agent makes a separate call:
GET /v1/schemas/research_request_v1

Response:
{
    "schema_name": "research_request_v1",
    "version": "1.0",
    "json_schema": {
        "type": "object",
        "properties": {
            "topic": {"type": "string"},
            "max_results": {"type": "integer"}
        },
        "required": ["topic"]
    }
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
