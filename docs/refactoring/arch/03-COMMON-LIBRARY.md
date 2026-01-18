# Architecture Refactoring: Common Library

**Document:** 03-COMMON-LIBRARY.md  
**Status:** ⬜ Not Started  
**Priority:** 🔴 High (Foundation)  
**Last Updated:** January 11, 2026

---

## Quick Reference

| Aspect | Details |
|--------|----------|
| **Task** | Shared DTOs in soorma-common |
| **Files** | `soorma-common/state.py`, `soorma-common/a2a.py` |
| **Pairs With SDK** | [sdk/03-COMMON-DTOS.md](../sdk/03-COMMON-DTOS.md) |
| **Dependencies** | None (foundational) |
| **Blocks** | Planner, Tracker, Registry services |
| **Estimated Effort** | 1 day |

---

## Context

### Why This Matters

`soorma-common` is the **single source of truth** for data contracts:

1. Services import DTOs from `soorma-common`
2. SDK re-exports DTOs from `soorma-common`
3. Ensures consistency between services and SDK

### Current State

`soorma-common` has basic DTOs (AgentDefinition, EventDefinition, EventEnvelope) but lacks:
- State machine DTOs for Planner/Tracker
- A2A protocol DTOs for Gateway
- Progress/tracking DTOs

### Key Files

```
soorma-common/
├── models.py           # Existing: AgentDefinition, EventDefinition
├── events.py           # Existing: EventEnvelope
├── state.py            # NEW: StateConfig, StateTransition, StateAction
└── a2a.py              # NEW: A2A protocol DTOs
```

---

## Summary

This document defines shared DTOs for `soorma-common`:
- State machine DTOs (Planner, Tracker)
- A2A protocol DTOs (Gateway, Discovery)
- Progress/tracking DTOs

See [sdk/03-COMMON-DTOS.md](../sdk/03-COMMON-DTOS.md) for SDK re-export strategy.

---

## New DTOs

### 1. State Machine DTOs (`soorma-common/state.py`)

**Used By:**
- Planner SDK (defines state machines)
- State Tracker Service (subscribes to state events)
- Registry Service (stores plan definitions)

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
```

### 2. A2A Protocol DTOs (`soorma-common/a2a.py`)

**Used By:**
- Gateway Service (exposes agents to external A2A clients)
- Registry Service (A2A Agent Card format)
- Discovery SDK (converts internal format to A2A)

```python
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any

class A2AAgentCard(BaseModel):
    """Agent Card per A2A protocol specification."""
    name: str
    description: str
    url: str = Field(..., description="Agent endpoint URL")
    version: str = "1.0.0"
    capabilities: List[str] = Field(default_factory=list)
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None

class A2ATask(BaseModel):
    """Task per A2A protocol."""
    task_id: str
    goal: str
    context: Optional[Dict[str, Any]] = None
    artifacts: List[Dict[str, Any]] = Field(default_factory=list)

class A2AResult(BaseModel):
    """Task result per A2A protocol."""
    task_id: str
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    artifacts: List[Dict[str, Any]] = Field(default_factory=list)
```

### 3. Progress/Tracking DTOs (`soorma-common/tracking.py`)

**Used By:**
- Workers/Planners (publish progress events)
- Tracker Service (subscribes to progress events)

```python
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum

class TaskState(str, Enum):
    """Standard task states."""
    PENDING = "pending"
    RUNNING = "running"
    DELEGATED = "delegated"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskProgressEvent(BaseModel):
    """Progress update event payload."""
    task_id: str
    plan_id: Optional[str] = None
    state: TaskState
    progress: Optional[float] = Field(None, ge=0.0, le=1.0, description="0.0 to 1.0")
    message: Optional[str] = None

class TaskStateChanged(BaseModel):
    """State transition event payload."""
    task_id: str
    plan_id: Optional[str] = None
    previous_state: TaskState
    new_state: TaskState
    reason: Optional[str] = None
```

---

## Implementation Steps

### Step 1: Create New Files

```bash
cd soorma-common/

# Create state machine DTOs
touch state.py

# Create A2A DTOs
touch a2a.py

# Create tracking DTOs
touch tracking.py
```

### Step 2: Implement DTOs

Copy the DTO definitions above into respective files.

### Step 3: Update Exports

```python
# soorma-common/__init__.py
from .models import (
    AgentCapability,
    AgentDefinition,
    EventDefinition,
    # ... existing exports
)

from .events import (
    EventEnvelope,
    ActionRequestEvent,
    ActionResultEvent,
    # ... existing exports
)

# NEW exports
from .state import (
    StateAction,
    StateTransition,
    StateConfig,
)

from .a2a import (
    A2AAgentCard,
    A2ATask,
    A2AResult,
)

from .tracking import (
    TaskState,
    TaskProgressEvent,
    TaskStateChanged,
)
```

### Step 4: Services Import from Common

```python
# In services (Registry, Tracker, etc.)
from soorma_common import (
    StateConfig,
    StateTransition,
    A2AAgentCard,
    TaskProgressEvent,
)

# Use in service code
@tracker.on_event(topic="system-events", event_type="task.progress")
async def track_progress(event):
    progress = TaskProgressEvent(**event.data)
    await db.update_task_progress(progress)
```

### Step 5: SDK Re-exports

See [sdk/03-COMMON-DTOS.md](../sdk/03-COMMON-DTOS.md) for SDK re-export pattern.

```python
# sdk/python/soorma/models.py
from soorma_common import (
    StateConfig,
    StateTransition,
    TaskState,
    A2AAgentCard,
    # ... re-export all
)
```

---

## Testing Strategy

### Unit Tests

```python
async def test_state_config_validation():
    """StateConfig should validate properly."""
    state = StateConfig(
        state_name="search",
        description="Search the web",
        action=StateAction(
            event_type="web.search.requested",
            response_event="web.search.completed",
        ),
        transitions=[
            StateTransition(
                on_event="web.search.completed",
                to_state="analyze"
            )
        ]
    )
    
    assert state.state_name == "search"
    assert state.action.event_type == "web.search.requested"

async def test_task_progress_validation():
    """TaskProgressEvent should validate progress range."""
    # Valid progress
    progress = TaskProgressEvent(
        task_id="task-123",
        state=TaskState.RUNNING,
        progress=0.5
    )
    assert progress.progress == 0.5
    
    # Invalid progress (should raise)
    with pytest.raises(ValidationError):
        TaskProgressEvent(
            task_id="task-123",
            state=TaskState.RUNNING,
            progress=1.5  # > 1.0
        )

async def test_a2a_agent_card():
    """A2AAgentCard should match A2A spec."""
    card = A2AAgentCard(
        name="Research Agent",
        description="Performs web research",
        url="https://api.example.com/agents/research",
        capabilities=["web_search", "summarization"]
    )
    
    # Should serialize to A2A format
    json_data = card.model_dump()
    assert "name" in json_data
    assert "capabilities" in json_data
```

---

## DTO Ownership Summary

| DTO Category | Owner | Used By |
|--------------|-------|---------|
| Agent/Event Registry | soorma-common/models.py | Registry Service, SDK |
| Event Envelope | soorma-common/events.py | Event Service, SDK |
| State Machine | soorma-common/state.py | Planner SDK, Tracker, Registry |
| A2A Protocol | soorma-common/a2a.py | Gateway, Discovery SDK |
| Progress/Tracking | soorma-common/tracking.py | Workers/Planners SDK, Tracker |

**Principle:** Services import from `soorma-common`, SDK re-exports.

---

## Dependencies

- **Depends on:** Nothing (foundational)
- **Blocks:** Planner, Tracker, Registry services
- **Pairs with SDK:** [sdk/03-COMMON-DTOS.md](../sdk/03-COMMON-DTOS.md)

---

## Related Documents

- [00-OVERVIEW.md](00-OVERVIEW.md) - Common library strategy
- [../sdk/03-COMMON-DTOS.md](../sdk/03-COMMON-DTOS.md) - SDK re-export pattern
- [../sdk/06-PLANNER-MODEL.md](../sdk/06-PLANNER-MODEL.md) - Uses StateConfig
- [04-TRACKER-SERVICE.md](04-TRACKER-SERVICE.md) - Uses tracking DTOs
- [05-REGISTRY-SERVICE.md](05-REGISTRY-SERVICE.md) - Uses A2A DTOs
