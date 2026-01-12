# SDK Refactoring: Common DTOs & Tracker Events

**Document:** 03-COMMON-DTOS.md  
**Status:** ⬜ Not Started  
**Priority:** � High (Foundation)  
**Last Updated:** January 11, 2026

---

## Quick Reference

| Aspect | Details |
|--------|----------|
| **Tasks** | RF-SDK-011: Tracker via Events, RF-SDK-012: Common Library DTOs |
| **Files** | `soorma-common/`, `sdk/python/soorma/agents/` |
| **Pairs With Arch** | [arch/03-COMMON-LIBRARY.md](../arch/03-COMMON-LIBRARY.md), [arch/04-TRACKER-SERVICE.md](../arch/04-TRACKER-SERVICE.md) |
| **Dependencies** | None (foundational) |
| **Blocks** | 06-PLANNER-MODEL, 07-DISCOVERY |
| **Estimated Effort** | 1-2 days |

---

## Context

### Why This Matters

This document covers two **foundational** concerns:

1. **Common DTOs** (`soorma-common`) - Shared data contracts between SDK and services
   - `StateConfig`, `StateTransition`, `StateAction` - Used by Planner and State Tracker
   - `A2AAgentCard`, `A2ATask`, etc. - Used by Discovery and Gateway

2. **Tracker via Events** - Decouple SDK from direct tracker API calls
   - Workers/Planners publish events on `system-events` topic
   - Tracker service subscribes and updates state

### Current State

- SDK calls `context.tracker.emit_progress()` directly (tight coupling)
- DTOs are scattered across services without shared contracts
- Planner will need `StateConfig` DTOs that should be shared with Tracker

### Key Files

```
soorma-common/
├── models.py           # Existing shared models
├── state.py            # NEW: StateConfig, StateTransition, StateAction
└── a2a.py              # NEW: A2A protocol DTOs

sdk/python/soorma/
├── models.py           # Re-exports from soorma-common
└── agents/
    ├── worker.py       # Remove tracker API calls
    └── planner.py      # Import StateConfig from common
```

---

## Summary

This document covers tracker integration and common library DTOs:
- **RF-SDK-011:** Tracker via Events, Not API
- **RF-SDK-012:** Common Library DTOs (soorma-common)

These tasks decouple the SDK from direct tracker calls and establish shared contracts.

---

## Tasks

### RF-SDK-011: Tracker via Events, Not API

**Files:** [worker.py](../../sdk/python/soorma/agents/worker.py#L264-L280), [context.py](../../sdk/python/soorma/context.py#L799-L900)

#### Current Issue

Workers call `context.tracker.emit_progress()` directly, creating tight coupling.

#### Target

Workers publish events on `system-events` topic, Tracker service subscribes.

```python
# Worker publishes (no direct API call)
await context.bus.publish(
    topic="system-events",
    event_type="task.progress",
    data={
        "plan_id": task.plan_id,
        "task_id": task.task_id,
        "status": "running",
        "progress": 0.5,
    },
)

# Tracker service subscribes to system-events topic
# and updates its database based on events
```

#### TrackerClient Changes

| Method | Action |
|--------|--------|
| `tracker.emit_progress()` | **Remove** - use event publishing |
| `tracker.complete_task()` | **Remove** - use event publishing |
| `tracker.fail_task()` | **Remove** - use event publishing |
| `tracker.get_plan_status()` | **Keep** - read-only query |
| `tracker.list_tasks()` | **Keep** - read-only query |

---

### RF-SDK-012: Common Library DTOs

**Files:** `soorma-common/models.py`, `soorma-common/a2a.py` (new), `soorma-common/state.py` (new)

#### Goal

Move shared DTOs to `soorma-common` so services and SDK share the same contracts.

---

## Current soorma-common Exports

```python
# Already in soorma-common
from soorma_common import (
    # Agent Registry
    AgentCapability, AgentDefinition, AgentRegistrationRequest, ...
    # Event Registry  
    EventDefinition, EventRegistrationRequest, ...
    # Memory Service
    SemanticMemoryCreate, EpisodicMemoryCreate, ...
    # Event Envelopes
    EventEnvelope, ActionRequestEvent, ActionResultEvent, ...
)
```

---

## New DTOs to Add

### 1. State Machine DTOs (`soorma-common/state.py`)

Used by Planner SDK AND State Tracker Service.

```python
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any

class StateAction(BaseModel):
    """Action to execute when entering a state."""
    event_type: str = Field(..., description="Event to publish")
    response_event: str = Field(..., description="Expected response event")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Event payload template")


class StateTransition(BaseModel):
    """A transition from one state to another."""
    on_event: str = Field(..., description="Event type that triggers this transition")
    to_state: str = Field(..., description="Target state name")
    condition: Optional[str] = Field(default=None, description="Optional condition expression")


class StateConfig(BaseModel):
    """Configuration for a state in the plan state machine."""
    state_name: str = Field(..., description="Unique state identifier")
    description: str = Field(..., description="Human-readable description")
    action: Optional[StateAction] = Field(default=None, description="Action on state entry")
    transitions: List[StateTransition] = Field(default_factory=list)
    default_next: Optional[str] = Field(default=None, description="For unconditional transitions")
    is_terminal: bool = Field(default=False, description="Whether this is a terminal state")


class PlanDefinition(BaseModel):
    """Definition of a plan's state machine - used for registration."""
    plan_type: str = Field(..., description="Type of plan (e.g., 'research.plan')")
    description: str = Field(..., description="Plan description")
    initial_state: str = Field(default="start", description="Starting state")
    states: Dict[str, StateConfig] = Field(..., description="State machine definition")


class PlanRegistrationRequest(BaseModel):
    """Request to register a plan type with State Tracker."""
    plan: PlanDefinition


class PlanInstanceRequest(BaseModel):
    """Request to create a new plan instance."""
    plan_type: str
    goal_data: Dict[str, Any]
    session_id: Optional[str] = None
    parent_plan_id: Optional[str] = None
```

### 2. A2A Compatibility DTOs (`soorma-common/a2a.py`)

For external-facing gateway agents.

```python
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Literal
from enum import Enum


class A2AAuthType(str, Enum):
    API_KEY = "apiKey"
    OAUTH2 = "oauth2"
    NONE = "none"


class A2AAuthentication(BaseModel):
    """A2A authentication configuration."""
    schemes: List[A2AAuthType]
    credentials: Optional[str] = None  # URL for OAuth discovery


class A2ASkill(BaseModel):
    """A2A Skill - maps to our AgentCapability."""
    id: str
    name: str
    description: str
    tags: List[str] = Field(default_factory=list)
    inputSchema: Optional[Dict[str, Any]] = None  # JSON Schema
    outputSchema: Optional[Dict[str, Any]] = None  # JSON Schema


class A2AAgentCard(BaseModel):
    """
    A2A Agent Card - industry standard for agent discovery.
    
    Ref: https://google.github.io/agent-to-agent/
    """
    name: str
    description: str
    url: str  # Gateway URL for this agent
    version: str = "1.0.0"
    provider: Dict[str, str] = Field(default_factory=dict)
    capabilities: Dict[str, Any] = Field(default_factory=dict)
    skills: List[A2ASkill] = Field(default_factory=list)
    authentication: A2AAuthentication


class A2APart(BaseModel):
    """Part of an A2A message."""
    type: Literal["text", "data", "file"]
    text: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    mimeType: Optional[str] = None


class A2AMessage(BaseModel):
    """A2A Message in a task."""
    role: Literal["user", "agent"]
    parts: List[A2APart]


class A2ATask(BaseModel):
    """A2A Task - standard task format for external requests."""
    id: str
    sessionId: Optional[str] = None
    message: A2AMessage
    metadata: Optional[Dict[str, Any]] = None


class A2ATaskStatus(str, Enum):
    SUBMITTED = "submitted"
    WORKING = "working"
    INPUT_REQUIRED = "input-required"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class A2ATaskResponse(BaseModel):
    """A2A Task Response."""
    id: str
    sessionId: Optional[str] = None
    status: A2ATaskStatus
    message: Optional[A2AMessage] = None
    error: Optional[str] = None
```

---

## SDK Re-exports

```python
# sdk/python/soorma/models.py - add new imports
from soorma_common import (
    # ... existing ...
    
    # State Machine (new)
    StateConfig, StateTransition, StateAction,
    PlanDefinition, PlanRegistrationRequest,
    
    # A2A (new)  
    A2AAgentCard, A2ATask, A2ATaskResponse, A2ASkill, A2AAuthentication,
)
```

---

## Tracker Event Types

Standard events on `system-events` topic:

| Event Type | Published By | Data |
|------------|-------------|------|
| `task.started` | Worker | `{task_id, plan_id, event_type}` |
| `task.progress` | Worker | `{task_id, plan_id, progress: 0.0-1.0}` |
| `task.completed` | Worker | `{task_id, plan_id, result}` |
| `task.failed` | Worker | `{task_id, plan_id, error}` |
| `plan.started` | Planner | `{plan_id, goal_event, session_id}` |
| `plan.state_changed` | Planner | `{plan_id, old_state, new_state}` |
| `plan.completed` | Planner | `{plan_id, result}` |
| `plan.failed` | Planner | `{plan_id, error}` |
| `plan.paused` | Planner | `{plan_id, reason}` |
| `plan.resumed` | Planner | `{plan_id}` |

---

## Usage Examples

### Publishing Task Progress (instead of API call)

```python
# Before (direct API call - DEPRECATED)
await context.tracker.emit_progress(task.task_id, 0.5)

# After (event publishing)
await context.bus.publish(
    topic="system-events",
    event_type="task.progress",
    data={
        "plan_id": task.plan_id,
        "task_id": task.task_id,
        "progress": 0.5,
    },
)
```

### Using Common DTOs

```python
from soorma_common import StateConfig, StateTransition, StateAction

# Define state machine using common DTOs
research_plan = {
    "searching": StateConfig(
        state_name="searching",
        description="Searching for information",
        action=StateAction(
            event_type="web.search.requested",
            response_event="web.search.completed",
        ),
        transitions=[
            StateTransition(on_event="web.search.completed", to_state="analyzing"),
        ]
    ),
}
```

---

## Tests to Add

```python
# test/test_tracker_events.py

async def test_worker_emits_progress_event():
    """Worker should emit task.progress on system-events topic."""
    pass

async def test_worker_emits_completed_event():
    """Worker should emit task.completed on completion."""
    pass

async def test_planner_emits_state_change_event():
    """Planner should emit plan.state_changed on transition."""
    pass

# test/test_common_dtos.py

def test_state_config_serialization():
    """StateConfig should serialize to/from JSON."""
    pass

def test_a2a_agent_card_serialization():
    """A2AAgentCard should serialize to JSON for HTTP response."""
    pass
```

---

## Implementation Checklist

### RF-SDK-011: Tracker via Events

- [ ] **Remove** `tracker.emit_progress()` from TrackerClient
- [ ] **Remove** `tracker.complete_task()` from TrackerClient
- [ ] **Remove** `tracker.fail_task()` from TrackerClient
- [ ] **Update** Worker to publish `task.*` events
- [ ] **Update** Planner to publish `plan.*` events
- [ ] **Keep** read-only methods (`get_plan_status`, `list_tasks`)
- [ ] **Update** Tracker Service to subscribe to `system-events`

### RF-SDK-012: Common Library DTOs

- [ ] **Create** `soorma-common/state.py` with state machine DTOs
- [ ] **Create** `soorma-common/a2a.py` with A2A DTOs
- [ ] **Update** `soorma-common/__init__.py` to export new modules
- [ ] **Update** SDK `models.py` to re-export common DTOs
- [ ] **Update** Planner to import StateConfig from soorma-common
- [ ] **Update** State Tracker Service to import from soorma-common

---

## Dependencies

- **Depends on:** Nothing (foundational)
- **Blocks:** [06-PLANNER-MODEL.md](06-PLANNER-MODEL.md) (StateConfig DTOs)
- **Blocks:** [07-DISCOVERY.md](07-DISCOVERY.md) (A2A DTOs)

---

## Open Questions

None currently - design is settled.

---

## Related Documents

- [06-PLANNER-MODEL.md](06-PLANNER-MODEL.md) - Uses StateConfig DTOs
- [07-DISCOVERY.md](07-DISCOVERY.md) - Uses A2A DTOs
- [A2A Protocol](https://google.github.io/agent-to-agent/) - External reference
