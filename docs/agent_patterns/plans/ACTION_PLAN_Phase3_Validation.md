# Action Plan: Phase 3 - Validation & Tracker Service (SOOR-PLAN-003)

**Status:** 📋 Planning  
**Parent Plan:** [MASTER_PLAN_Stage4_Planner.md](MASTER_PLAN_Stage4_Planner.md)  
**Phase:** 3 of 4 (Validation - Examples & Tracker Service)  
**Estimated Duration:** 3 days (8-10 hours/day)  
**Dependencies:** ✅ Phase 2 Complete (ChoreographyPlanner, PlannerDecision, PlanContext)  
**Created:** February 21, 2026

---

## 1. Requirements & Core Objective

### Summary

Implement end-to-end validation of Stage 4 Planner Model by:
1. **Refactoring research-advisor example** from manual orchestration (~472 lines) to ChoreographyPlanner (~50 lines)
2. **Building Tracker Service** for event-driven observability
3. **Adding TrackerClient wrapper** to PlatformContext (two-layer SDK compliance)
4. **Integration testing** across Planner → Workers → Tracker flow

### Acceptance Criteria

- [x] ✅ **Phase 2 Complete:** ChoreographyPlanner, PlannerDecision, PlanContext implemented and tested (51 tests passing)
- [ ] **Example Refactor:** research-advisor planner reduced from 472 lines → ≤60 lines
- [ ] **Code Reduction:** Achieves ≥85% reduction in orchestration code
- [ ] **Tracker Service:** Subscribes to events and stores progress in PostgreSQL
- [ ] **TrackerClient Wrapper:** Exists in PlatformContext with query methods
- [ ] **Integration Tests:** ≥4 tests covering goal → completion → tracker query flow
- [ ] **Documentation:** README.md and CHANGELOG.md updated
- [ ] **No Regressions:** All existing tests still pass
- [ ] **Example Runs:** `soorma dev` + example demonstrates autonomous choreography

### Success Metrics

| Metric | Target | Validation |
|--------|--------|------------|
| **Code Reduction** | 472 → ≤60 lines (87%+) | `wc -l planner.py` |
| **Test Coverage** | ≥85% on new code | `pytest --cov` |
| **Integration Tests** | ≥4 passing | `pytest tests/integration/` |
| **API Response Time** | Tracker queries <200ms | Manual curl tests |
| **Memory Overhead** | Plan storage ≤15KB | Database query inspection |

---

## 2. Technical Design

### Components Modified

| Component | Type | Files | Change Type |
|-----------|------|-------|-------------|
| **Tracker Service** | Backend Service | `services/tracker/` (NEW) | Major - New Service |
| **TrackerClient Wrapper** | SDK | `sdk/python/soorma/context.py` | Medium - Add wrapper class |
| **research-advisor** | Example | `examples/research-advisor/planner.py` | Major - Refactor |
| **soorma-common** | DTOs | ✅ Already exists: `tracking.py` | No change (schemas exist) |
| **Integration Tests** | Tests | `sdk/python/tests/test_planner_flow.py` (NEW) | Medium - New tests |

### Architecture Alignment (ARCHITECTURE_PATTERNS.md)

**Section 1: Authentication**
- ✅ Tracker Service MUST accept `X-Tenant-ID` and `X-User-ID` headers
- ✅ Set PostgreSQL session variables for RLS enforcement
- ✅ All queries filtered by tenant_id automatically via RLS policies

**Section 2: Two-Layer SDK Architecture** 🔴 CRITICAL
- ✅ TrackerServiceClient (Layer 1): Low-level HTTP client for Tracker endpoints
- ✅ TrackerClient (Layer 2): High-level wrapper in PlatformContext
- ✅ Example MUST use `context.tracker.*`, NOT `TrackerServiceClient` directly
- ✅ Wrapper delegates to `self._client` after `_ensure_client()`

**Section 3: Event Choreography**
- ✅ Tracker subscribes to: `system-events`, `action-requests`, `action-results`
- ✅ Uses `response_event` for query responses (N/A - read-only service)
- ✅ Event envelopes include `tenant_id`, `user_id`, `correlation_id`

**Section 4: Multi-Tenancy**
- ✅ RLS policies on `task_executions`, `state_transitions`, `event_timeline`
- ✅ Session variables: `app.tenant_id`, `app.user_id`
- ✅ Automatic tenant isolation at database layer

**Section 5: State Management**
- ✅ Tracker stores task/plan state in dedicated tables (not working memory)
- ✅ PlanContext used by Planner (not Tracker - passive consumer only)

**Section 6: Error Handling**
- ✅ Tracker queries return 404 if plan_id not found
- ✅ Service client raises HTTPError, wrapper converts to None/empty list
- ✅ Event subscriber errors logged, don't crash service

**Section 7: Testing**
- ✅ Unit tests: Mock TrackerServiceClient in TrackerClient wrapper tests
- ✅ Integration tests: Use live Tracker Service + Event Bus + Memory Service
- ✅ Fixtures: `tracker_service`, `example_plan_id`, `example_task_id`

---

### SDK Layer Verification (Two-Layer Pattern Compliance)

#### Layer 1: TrackerServiceClient (Low-Level HTTP Client)

**File:** `sdk/python/soorma/tracker/client.py` (NEW)

**Methods Required:**
```python
class TrackerServiceClient:
    async def get_plan_progress(
        self, 
        plan_id: str, 
        tenant_id: str, 
        user_id: str
    ) -> PlanProgress
    
    async def get_plan_tasks(
        self, 
        plan_id: str, 
        tenant_id: str, 
        user_id: str
    ) -> List[TaskExecution]
    
    async def get_plan_timeline(
        self, 
        plan_id: str, 
        tenant_id: str, 
        user_id: str
    ) -> EventTimeline
    
    async def query_agent_metrics(
        self, 
        agent_id: str, 
        period: str,
        tenant_id: str, 
        user_id: str
    ) -> AgentMetrics
```

**Status:** ⬜ Missing - Task 2.1 will create

#### Layer 2: TrackerClient (High-Level Wrapper)

**File:** `sdk/python/soorma/context.py` (MODIFY)

**Wrapper Methods Required:**
```python
@dataclass
class TrackerClient:
    """High-level Tracker Service client wrapper."""
    
    base_url: str = field(default_factory=lambda: os.getenv(...))
    _client: Optional[TrackerServiceClient] = field(default=None, repr=False, init=False)
    
    async def get_plan_progress(self, plan_id: str) -> Optional[PlanProgress]:
        """Get plan execution status.
        
        Tenant/user context extracted from event envelope automatically.
        
        Returns:
            PlanProgress or None if not found
        """
        client = await self._ensure_client()
        # tenant_id/user_id extracted from context (NOT parameters)
        return await client.get_plan_progress(plan_id, tenant_id, user_id)
    
    async def get_plan_tasks(self, plan_id: str) -> List[TaskExecution]:
        """Get task history for plan."""
        # Similar delegation pattern
    
    async def get_plan_timeline(self, plan_id: str) -> Optional[EventTimeline]:
        """Get event execution timeline."""
        # Similar delegation pattern
    
    async def query_agent_metrics(
        self, 
        agent_id: str, 
        period: str = "7d"
    ) -> Optional[AgentMetrics]:
        """Query agent performance metrics."""
        # Similar delegation pattern
```

**Status:** ⬜ Missing - Task 2.2 will create

#### Layer 2: PlatformContext Integration

**File:** `sdk/python/soorma/context.py` (MODIFY)

**Add to PlatformContext dataclass:**
```python
@dataclass
class PlatformContext:
    registry: RegistryClient = field(...)
    memory: MemoryClient = field(...)
    bus: BusClient = field(...)
    tracker: TrackerClient = field(...)  # ← ADD THIS
    
    # Existing fields...
```

**Status:** ⬜ Missing - Task 2.3 will add

#### Examples Compliance Check

**File:** `examples/research-advisor/planner.py` (REFACTOR)

**Before (WRONG - 472 lines with manual code):**
```python
# Manual event discovery, LLM calls, validation, publishing
response = await registry.query_events(...)
decision = await get_next_action(...)  # Custom LLM function
# ~400 lines of orchestration boilerplate
```

**After (CORRECT - ≤60 lines with ChoreographyPlanner):**
```python
from soorma.ai.choreography import ChoreographyPlanner
from soorma.plan_context import PlanContext

planner = ChoreographyPlanner(name="orchestrator", reasoning_model="gpt-4o")

@planner.on_goal("research.goal")
async def handle_goal(goal, context):
    plan = await PlanContext.create_from_goal(
        goal=goal, context=context,
        state_machine={}, current_state="reasoning", status="running"
    )
    decision = await planner.reason_next_action(
        trigger=f"New goal: {goal.data['objective']}",
        context=context,
    )
    await planner.execute_decision(decision, context, goal_event=goal, plan=plan)

@planner.on_transition()
async def handle_result(event, context):
    plan = await PlanContext.restore_by_correlation(event.correlation_id, context)
    if not plan:
        return
    
    # Optional: Query tracker for progress
    progress = await context.tracker.get_plan_progress(plan.plan_id)
    print(f"Progress: {progress.completed_tasks}/{progress.task_count}")
    
    decision = await planner.reason_next_action(
        trigger=f"Received {event.event_type}",
        context=context,
        custom_context={"previous_result": event.data}
    )
    await planner.execute_decision(decision, context, goal_event=event, plan=plan)
```

**Compliance Verification:**
- [x] ✅ Uses `ChoreographyPlanner` from SDK
- [x] ✅ Uses `context.tracker.*` for queries (NOT `TrackerServiceClient`)
- [x] ✅ Uses `PlanContext.create_from_goal()` and `restore_by_correlation()`
- [x] ✅ No manual LLM calls (delegated to `reason_next_action`)
- [x] ✅ No manual event validation (delegated to `execute_decision`)
- [x] ✅ Total lines: ~50 (87% reduction from 472)

**Status:** ⬜ Pending - Task 3 will refactor

---

### Data Models

#### Existing DTOs (soorma-common/tracking.py)

✅ **Already implemented in Phase 1:**

```python
class TaskState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DELEGATED = "delegated"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskProgressEvent(BaseModel):
    task_id: str
    plan_id: Optional[str]
    state: TaskState
    progress: Optional[float]  # 0.0-1.0
    message: Optional[str]

class TaskStateChanged(BaseModel):
    task_id: str
    plan_id: Optional[str]
    previous_state: TaskState
    new_state: TaskState
    reason: Optional[str]
```

#### New Response DTOs (soorma-common/tracker.py - NEW)

**File:** `libs/soorma-common/src/soorma_common/tracker.py` (NEW)

```python
class PlanProgress(BaseModel):
    """Plan execution progress summary."""
    plan_id: str
    status: str  # running, completed, failed
    started_at: datetime
    completed_at: Optional[datetime]
    task_count: int
    completed_tasks: int
    failed_tasks: int
    current_state: Optional[str]

class TaskExecution(BaseModel):
    """Task execution record."""
    task_id: str
    event_type: str
    state: TaskState
    started_at: datetime
    completed_at: Optional[datetime]
    duration_seconds: Optional[float]
    progress: Optional[float]

class EventTimelineEntry(BaseModel):
    """Event timeline entry."""
    event_id: str
    event_type: str
    timestamp: datetime
    parent_event_id: Optional[str]

class EventTimeline(BaseModel):
    """Event execution timeline."""
    trace_id: str
    events: List[EventTimelineEntry]

class AgentMetrics(BaseModel):
    """Agent performance metrics."""
    agent_id: str
    period: str
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    avg_duration_seconds: float
    success_rate: float
```

**Status:** ⬜ Missing - Task 1 will create

---

### Database Schema

**Service:** Tracker Service  
**Database:** PostgreSQL (shared with Memory Service)  
**Schema:** `tracker` (new schema)

```sql
-- Task execution records
CREATE TABLE tracker.task_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL,
    user_id UUID NOT NULL,
    task_id VARCHAR(100) NOT NULL,
    plan_id VARCHAR(100),
    event_type VARCHAR(255) NOT NULL,
    state VARCHAR(50) NOT NULL,
    progress FLOAT CHECK (progress >= 0 AND progress <= 1),
    message TEXT,
    data JSONB DEFAULT '{}',
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    trace_id VARCHAR(100),
    parent_event_id VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, task_id)
);

CREATE INDEX task_executions_plan_idx ON tracker.task_executions (tenant_id, plan_id);
CREATE INDEX task_executions_trace_idx ON tracker.task_executions (tenant_id, trace_id);

-- RLS Policy (User-scoped isolation)
ALTER TABLE tracker.task_executions ENABLE ROW LEVEL SECURITY;

CREATE POLICY task_executions_user_isolation 
ON tracker.task_executions
USING (
    tenant_id = current_setting('app.tenant_id')::UUID
    AND user_id = current_setting('app.user_id')::UUID
);

-- Optional: Admin policy for platform operators to view all tenant data
CREATE POLICY task_executions_admin_view
ON tracker.task_executions
USING (
    current_setting('app.role', true) = 'admin'
    AND tenant_id = current_setting('app.tenant_id')::UUID
);

-- State transition history
CREATE TABLE tracker.state_transitions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL,
    user_id UUID NOT NULL,
    task_id VARCHAR(100) NOT NULL,
    plan_id VARCHAR(100),
    from_state VARCHAR(50) NOT NULL,
    to_state VARCHAR(50) NOT NULL,
    reason TEXT,
    transitioned_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX state_transitions_task_idx 
ON tracker.state_transitions (tenant_id, task_id, transitioned_at);

ALTER TABLE tracker.state_transitions ENABLE ROW LEVEL SECURITY;

CREATE POLICY state_transitions_user_isolation 
ON tracker.state_transitions
USING (
    tenant_id = current_setting('app.tenant_id')::UUID
    AND user_id = current_setting('app.user_id')::UUID
);

-- Event timeline
CREATE TABLE tracker.event_timeline (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL,
    user_id UUID NOT NULL,
    event_id VARCHAR(100) NOT NULL,
    event_type VARCHAR(255) NOT NULL,
    topic VARCHAR(100),
    trace_id VARCHAR(100),
    parent_event_id VARCHAR(100),
    correlation_id VARCHAR(100),
    data JSONB DEFAULT '{}',
    occurred_at TIMESTAMPTZ NOT NULL,
    UNIQUE(tenant_id, event_id)
);

CREATE INDEX event_timeline_trace_idx 
ON tracker.event_timeline (tenant_id, trace_id, occurred_at);

ALTER TABLE tracker.event_timeline ENABLE ROW LEVEL SECURITY;

CREATE POLICY event_timeline_user_isolation 
ON tracker.event_timeline
USING (
    tenant_id = current_setting('app.tenant_id')::UUID
    AND user_id = current_setting('app.user_id')::UUID
);
```

---

## 3. Task Tracking Matrix

### Pre-Implementation Gateway ✅

- [x] ✅ **Read ARCHITECTURE_PATTERNS.md** - Sections 1-7 verified above
- [x] ✅ **Phase 2 Complete** - ChoreographyPlanner, PlannerDecision, PlanContext (51 tests passing)
- [x] ✅ **Tracking DTOs Exist** - TaskState, TaskProgressEvent, TaskStateChanged in soorma-common
- [x] ✅ **Template Followed** - Action_Plan_Template.md structure used
- [x] ✅ **Wrapper Verification** - TrackerClient missing, will create in Task 2

### Task Sequence (TDD - RED → GREEN → REFACTOR)

#### Day 1: Foundation - Tracker DTOs & Service Client (3-4 hours)

**Task 1: Tracker Response DTOs (RF-ARCH-011 extension)**
- **Status:** ⏳ Not Started
- **Effort:** 1 hour
- **TDD Phase:** RED
- **Files:**
  - `libs/soorma-common/src/soorma_common/tracker.py` (NEW)
  - `libs/soorma-common/tests/test_tracker.py` (NEW)
- **Steps:**
  1. Write tests for PlanProgress, TaskExecution, EventTimeline, AgentMetrics models
  2. Implement Pydantic models with validation
  3. Add to `soorma_common/__init__.py` exports
  4. Update `CHANGELOG.md` (soorma-common)
- **Acceptance:** 8+ tests passing, models validate correctly

**Task 2: TrackerServiceClient (Low-Level - Layer 1)**
- **Status:** ⏳ Not Started
- **Effort:** 1.5 hours
- **TDD Phase:** RED → GREEN
- **Files:**
  - `sdk/python/soorma/tracker/client.py` (NEW)
  - `sdk/python/soorma/tracker/__init__.py` (NEW)
  - `sdk/python/tests/test_tracker_service_client.py` (NEW)
- **Steps:**
  1. Write tests with mocked HTTP responses (pytest-httpx)
  2. Implement `TrackerServiceClient` with httpx
  3. Methods: `get_plan_progress()`, `get_plan_tasks()`, `get_plan_timeline()`, `query_agent_metrics()`
  4. Include `X-Tenant-ID`, `X-User-ID` headers on all requests
  5. Refactor: Error handling, connection pooling
- **Acceptance:** 6+ tests passing, all methods tested

**Task 3: TrackerClient Wrapper (High-Level - Layer 2)**
- **Status:** ⏳ Not Started
- **Effort:** 1 hour
- **TDD Phase:** GREEN → REFACTOR
- **Dependencies:** Task 2 complete
- **Files:**
  - `sdk/python/soorma/context.py` (MODIFY - add TrackerClient class)
  - `sdk/python/tests/test_context_wrappers.py` (MODIFY - add tracker tests)
- **Steps:**
  1. Write tests for TrackerClient wrapper (mock TrackerServiceClient)
  2. Add `TrackerClient` dataclass in context.py
  3. Implement `_ensure_client()` pattern
  4. Implement wrapper methods (no tenant_id/user_id parameters)
  5. Add `tracker: TrackerClient` field to `PlatformContext`
  6. Refactor: Lazy initialization, error handling
- **Acceptance:** 5+ tests passing, wrapper delegates to service client

---

#### Day 2: Tracker Service Implementation (5-6 hours)

**Task 4: Tracker Service Scaffold**
- **Status:** ⏳ Not Started
- **Effort:** 1 hour
- **TDD Phase:** GREEN (service setup)
- **Files:**
  - `services/tracker/` (NEW directory)
  - `services/tracker/pyproject.toml` (NEW)
  - `services/tracker/src/main.py` (NEW)
  - `services/tracker/src/db.py` (NEW)
  - `services/tracker/Dockerfile` (NEW)
- **Steps:**
  1. Create service directory structure
  2. Initialize Poetry project
  3. Add dependencies: `soorma-sdk`, `soorma-common`, `fastapi`, `uvicorn`, `asyncpg`
  4. Create FastAPI app scaffold
  5. Database connection setup (PostgreSQL)
  6. Health check endpoint
- **Acceptance:** Service starts, health check returns 200

**Task 5: Database Schema Migration**
- **Status:** ⏳ Not Started
- **Effort:** 1 hour
- **TDD Phase:** GREEN
- **Dependencies:** Task 4 complete
- **Files:**
  - `services/tracker/migrations/001_initial_schema.sql` (NEW)
  - `services/tracker/src/db.py` (MODIFY - add table classes)
- **Steps:**
  1. Create SQL migration file (schema from Design section)
  2. Add Alembic configuration (or simple migration runner)
  3. Create RLS policies for all tables
  4. Add indexes for common queries
  5. Test migration: `make migrate-tracker` or similar
- **Acceptance:** Tables created, RLS policies active, indexes exist

**Task 6: Event Subscribers (RF-ARCH-010)**
- **Status:** ⏳ Not Started
- **Effort:** 2 hours
- **TDD Phase:** RED → GREEN
- **Dependencies:** Task 5 complete
- **Files:**
  - `services/tracker/src/subscribers/task_tracking.py` (NEW)
  - `services/tracker/tests/test_subscribers.py` (NEW)
- **Steps:**
  1. Write tests for subscriber handlers (mock event bus)
  2. Implement subscriber for `system-events` topic:
     - `task.progress` → upsert `task_executions`
     - `task.state_changed` → insert `state_transitions`
  3. Implement subscriber for `action-requests` topic:
     - `*` → record task start in `task_executions`
  4. Implement subscriber for `action-results` topic:
     - `*` → record task completion in `task_executions`
  5. Refactor: Error handling, tenant_id extraction from event envelope
- **Acceptance:** 8+ tests passing, subscribers insert correctly

**Task 7: Query API Endpoints**
- **Status:** ⏳ Not Started
- **Effort:** 1.5 hours
- **TDD Phase:** RED → GREEN
- **Dependencies:** Task 6 complete
- **Files:**
  - `services/tracker/src/routes/query.py` (NEW)
  - `services/tracker/tests/test_query_api.py` (NEW)
- **Steps:**
  1. Write tests for API endpoints (FastAPI TestClient)
  2. Implement `GET /v1/tracker/plans/{plan_id}` → PlanProgress
  3. Implement `GET /v1/tracker/plans/{plan_id}/tasks` → List[TaskExecution]
  4. Implement `GET /v1/tracker/plans/{plan_id}/timeline` → EventTimeline
  5. Implement `GET /v1/tracker/metrics?agent_id={id}&period={period}` → AgentMetrics
  6. Refactor: Pagination, 404 handling, tenant isolation via RLS
- **Acceptance:** 6+ tests passing, queries return correct data

**Task 48H: FDE Decision - Tracker UI**
- **Decision:** ✅ **DEFER Tracker UI to Post-Launch**
- **Rationale:** Query APIs sufficient for Phase 3 validation
- **FDE Alternative:** Use `curl` or Postman for manual queries during testing
- **Future Work:** Create Tracker Dashboard UI in Stage 5+ or post-launch
- **Impact:** Saves 2-3 days, no blocker for Phase 3 goals
- **Example FDE Query:**
  ```bash
  # Manual query during development
  curl -H "X-Tenant-ID: $TENANT_ID" \
       -H "X-User-ID: $USER_ID" \
       http://localhost:8084/v1/tracker/plans/$PLAN_ID
  ```

---

#### Day 3: Example Refactor & Integration Tests (4-5 hours)

**Task 8: Refactor research-advisor Planner**
- **Status:** ⏳ Not Started
- **Effort:** 2 hours
- **TDD Phase:** REFACTOR
- **Dependencies:** Phase 2 complete (ChoreographyPlanner exists)
- **Files:**
  - `examples/research-advisor/planner.py` (REFACTOR)
  - `examples/research-advisor/planner_legacy.py` (RENAME - backup)
  - `examples/research-advisor/README.md` (UPDATE)
- **Steps:**
  1. Rename current planner.py → planner_legacy.py (backup)
  2. Create new planner.py using ChoreographyPlanner
  3. Implement `on_goal` handler with `PlanContext.create_from_goal()`
  4. Implement `on_transition` handler with LLM reasoning
  5. Add optional tracker progress logging
  6. Verify line count: ≤60 lines (target: ~50)
  7. Update README with new usage
  8. Manual test: `soorma dev` + run example end-to-end
- **Acceptance:** Planner works, ≤60 lines, example README updated

**Task 9: Integration Tests (RF-SDK-006 + RF-ARCH-010)**
- **Status:** ⏳ Not Started
- **Effort:** 2 hours
- **TDD Phase:** RED → GREEN
- **Dependencies:** Tasks 1-8 complete
- **Files:**
  - `sdk/python/tests/test_planner_flow.py` (NEW)
  - `sdk/python/tests/conftest.py` (MODIFY - add tracker fixtures)
- **Steps:**
  1. Add pytest fixtures: `tracker_service`, `example_plan_id`, `example_task_id`
  2. Write integration test: `test_goal_to_completion_with_tracker()`
     - Publish goal event
     - Planner creates plan, publishes task
     - Worker completes task, publishes result
     - Planner completes goal
     - Query tracker for plan progress
     - Assert: plan marked complete, tasks recorded
  3. Write test: `test_tracker_records_state_transitions()`
  4. Write test: `test_tracker_event_timeline()`
  5. Write test: `test_tracker_query_404_handling()`
  6. Refactor: Shared fixtures, cleanup utilities
- **Acceptance:** ≥4 integration tests passing, end-to-end flow validated

**Task 10: Documentation & Polish**
- **Status:** ⏳ Not Started
- **Effort:** 1 hour
- **Dependencies:** All tasks complete
- **Files:**
  - `sdk/python/CHANGELOG.md` (UPDATE)
  - `libs/soorma-common/CHANGELOG.md` (UPDATE)
  - `services/tracker/README.md` (NEW)
  - `examples/research-advisor/ARCHITECTURE.md` (UPDATE)
  - `docs/agent_patterns/plans/MASTER_PLAN_Stage4_Planner.md` (UPDATE - mark Phase 3 complete)
- **Steps:**
  1. Add CHANGELOG entries for SDK (TrackerClient wrapper)
  2. Add CHANGELOG entries for soorma-common (tracker response DTOs)
  3. Create Tracker Service README (architecture, deployment, API docs)
  4. Update research-advisor ARCHITECTURE.md (new ChoreographyPlanner design)
  5. Update Master Plan: Phase 3 completion date, metrics
  6. Run full test suite: `pytest` (all tests passing)
  7. Run example: `soorma dev` + manual validation
- **Acceptance:** All docs updated, tests passing, example runs end-to-end

---

### Task Dependencies Graph

```
Phase 2 Complete ✅
    │
    ├──▶ Task 1: Tracker DTOs (1h)
    │        │
    │        ├──▶ Task 2: TrackerServiceClient (1.5h)
    │        │        │
    │        │        └──▶ Task 3: TrackerClient Wrapper (1h)
    │        │
    │        └──▶ Task 4: Tracker Service Scaffold (1h)
    │                 │
    │                 └──▶ Task 5: DB Migration (1h)
    │                      │
    │                      └──▶ Task 6: Event Subscribers (2h)
    │                           │
    │                           └──▶ Task 7: Query APIs (1.5h)
    │
    └──▶ Task 8: Refactor Example (2h)
         │
         └──▶ Task 9: Integration Tests (2h)
              │
              └──▶ Task 10: Docs & Polish (1h)
```

**Critical Path:** Tasks 1 → 2 → 3 → 4 → 5 → 6 → 7 → 9 → 10  
**Parallel Track:** Task 8 can start after Phase 2 (independent of Tasks 1-7)

---

## 4. TDD Strategy

### Unit Tests

#### soorma-common Tests

**File:** `libs/soorma-common/tests/test_tracker.py` (NEW)

```python
"""Unit tests for tracker response DTOs."""
from datetime import datetime
from soorma_common.tracker import (
    PlanProgress, TaskExecution, EventTimeline, AgentMetrics
)
from soorma_common.tracking import TaskState

def test_plan_progress_validation():
    """Test PlanProgress model."""
    progress = PlanProgress(
        plan_id="plan-123",
        status="running",
        started_at=datetime.now(),
        task_count=5,
        completed_tasks=3,
        failed_tasks=0,
        current_state="analyzing"
    )
    assert progress.plan_id == "plan-123"
    assert progress.task_count == 5

def test_task_execution_duration_calculation():
    """Test TaskExecution with duration."""
    start = datetime(2026, 2, 21, 10, 0, 0)
    end = datetime(2026, 2, 21, 10, 2, 30)
    
    task = TaskExecution(
        task_id="task-1",
        event_type="search.requested",
        state=TaskState.COMPLETED,
        started_at=start,
        completed_at=end,
        duration_seconds=150.0
    )
    assert task.duration_seconds == 150.0

# 6 more tests...
```

**Coverage Target:** 90%+

#### SDK Tests (Service Client)

**File:** `sdk/python/tests/test_tracker_service_client.py` (NEW)

```python
"""Unit tests for TrackerServiceClient (Layer 1)."""
import pytest
from unittest.mock import AsyncMock, patch
from soorma.tracker.client import TrackerServiceClient
from soorma_common.tracker import PlanProgress

@pytest.fixture
def tracker_client():
    return TrackerServiceClient(base_url="http://localhost:8084")

@pytest.mark.asyncio
async def test_get_plan_progress_success(tracker_client):
    """Test get_plan_progress with valid response."""
    mock_response = {
        "plan_id": "plan-123",
        "status": "running",
        "started_at": "2026-02-21T10:00:00Z",
        "task_count": 5,
        "completed_tasks": 3,
        "failed_tasks": 0,
        "current_state": "analyzing"
    }
    
    with patch.object(tracker_client._client, 'get') as mock_get:
        mock_get.return_value = AsyncMock(
            status_code=200,
            json=lambda: mock_response
        )
        
        result = await tracker_client.get_plan_progress(
            plan_id="plan-123",
            tenant_id="tenant-uuid",
            user_id="user-uuid"
        )
        
        assert isinstance(result, PlanProgress)
        assert result.plan_id == "plan-123"
        
        # Verify headers
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args.kwargs
        assert call_kwargs["headers"]["X-Tenant-ID"] == "tenant-uuid"
        assert call_kwargs["headers"]["X-User-ID"] == "user-uuid"

@pytest.mark.asyncio
async def test_get_plan_progress_404(tracker_client):
    """Test get_plan_progress when plan not found."""
    with patch.object(tracker_client._client, 'get') as mock_get:
        mock_get.return_value = AsyncMock(status_code=404)
        
        with pytest.raises(HTTPError):
            await tracker_client.get_plan_progress(
                plan_id="missing-plan",
                tenant_id="tenant-uuid",
                user_id="user-uuid"
            )

# 4 more tests...
```

**Coverage Target:** 85%+

#### SDK Tests (Wrapper)

**File:** `sdk/python/tests/test_context_wrappers.py` (MODIFY - add tracker section)

```python
"""Unit tests for TrackerClient wrapper (Layer 2)."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from soorma.context import TrackerClient, PlatformContext
from soorma_common.tracker import PlanProgress

@pytest.fixture
def mock_tracker_service_client():
    """Mock TrackerServiceClient for wrapper tests."""
    client = AsyncMock()
    client.get_plan_progress = AsyncMock(return_value=PlanProgress(...))
    client.get_plan_tasks = AsyncMock(return_value=[])
    return client

@pytest.mark.asyncio
async def test_tracker_wrapper_delegates_to_service_client(
    mock_tracker_service_client
):
    """Test TrackerClient delegates to TrackerServiceClient."""
    wrapper = TrackerClient()
    wrapper._client = mock_tracker_service_client
    
    # Call wrapper method (NO tenant_id/user_id parameters)
    result = await wrapper.get_plan_progress(plan_id="plan-123")
    
    # Verify delegation to service client (WITH tenant_id/user_id)
    mock_tracker_service_client.get_plan_progress.assert_called_once_with(
        plan_id="plan-123",
        tenant_id=ANY,  # Extracted from context
        user_id=ANY
    )
    assert isinstance(result, PlanProgress)

@pytest.mark.asyncio
async def test_tracker_wrapper_in_platform_context():
    """Test TrackerClient accessible via PlatformContext."""
    context = PlatformContext()
    assert hasattr(context, 'tracker')
    assert isinstance(context.tracker, TrackerClient)

# 3 more tests...
```

**Coverage Target:** 85%+

---

### Integration Tests

**File:** `sdk/python/tests/test_planner_flow.py` (NEW)

```python
"""Integration tests for Planner → Workers → Tracker flow."""
import pytest
import asyncio
from soorma import Planner, Worker, PlatformContext
from soorma.ai.choreography import ChoreographyPlanner
from soorma.plan_context import PlanContext
from soorma_common.tracking import TaskState

@pytest.fixture
async def tracker_service():
    """Start Tracker Service for integration tests."""
    # Assume service runs on localhost:8084
    # Verify health check
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8084/health")
        assert response.status_code == 200
    yield
    # Cleanup if needed

@pytest.fixture
def example_goal_event():
    """Sample goal event for testing."""
    return EventEnvelope(
        event_type="research.goal",
        data={"objective": "Test research topic"},
        correlation_id="test-correlation-123",
        response_event="research.fulfilled"
    )

@pytest.mark.asyncio
@pytest.mark.integration
async def test_goal_to_completion_with_tracker(
    tracker_service, example_goal_event
):
    """Test complete flow: goal → planner → worker → tracker query."""
    # Create planner
    planner = ChoreographyPlanner(name="test-planner", reasoning_model="gpt-4o")
    
    # Create mock worker
    worker = Worker(name="test-worker")
    
    @worker.on_task("mock.task")
    async def handle_task(task, context):
        await context.bus.respond(
            event_type=task.response_event,
            correlation_id=task.correlation_id,
            data={"result": "Task completed"}
        )
    
    # Start agents
    await planner.start()
    await worker.start()
    
    try:
        # Publish goal
        context = PlatformContext()
        await context.bus.publish(
            topic="action-requests",
            event_type="research.goal",
            data=example_goal_event.data
        )
        
        # Wait for processing
        await asyncio.sleep(2)
        
        # Query tracker for plan progress
        progress = await context.tracker.get_plan_progress(
            plan_id=example_goal_event.correlation_id
        )
        
        # Assertions
        assert progress is not None
        assert progress.plan_id == example_goal_event.correlation_id
        assert progress.status in ["running", "completed"]
        assert progress.task_count > 0
        
        # Query task history
        tasks = await context.tracker.get_plan_tasks(
            plan_id=example_goal_event.correlation_id
        )
        assert len(tasks) > 0
        assert tasks[0].state in [TaskState.COMPLETED, TaskState.RUNNING]
        
    finally:
        await planner.stop()
        await worker.stop()

@pytest.mark.asyncio
@pytest.mark.integration
async def test_tracker_records_state_transitions():
    """Test Tracker records state changes."""
    # Publish task.state_changed event
    context = PlatformContext()
    await context.bus.publish(
        topic="system-events",
        event_type="task.state_changed",
        data={
            "task_id": "task-456",
            "plan_id": "plan-789",
            "previous_state": "pending",
            "new_state": "running"
        }
    )
    
    # Wait for Tracker to process
    await asyncio.sleep(0.5)
    
    # Query task execution
    tasks = await context.tracker.get_plan_tasks(plan_id="plan-789")
    assert len(tasks) > 0
    assert tasks[0].task_id == "task-456"
    assert tasks[0].state == TaskState.RUNNING

# 2 more integration tests...
```

**Coverage Target:** Critical paths validated

---

### Test Fixtures

**File:** `sdk/python/tests/conftest.py` (MODIFY - add tracker fixtures)

```python
@pytest.fixture
def example_plan_id():
    """Sample plan ID for tests."""
    return f"plan-{uuid.uuid4()}"

@pytest.fixture
def example_task_id():
    """Sample task ID for tests."""
    return f"task-{uuid.uuid4()}"

@pytest.fixture
async def tracker_service():
    """Ensure Tracker Service is running for integration tests."""
    # Health check
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get("http://localhost:8084/health")
            assert response.status_code == 200
        except httpx.ConnectError:
            pytest.skip("Tracker Service not running - skipping integration test")
    yield

@pytest.fixture
def mock_tracker_client():
    """Mock TrackerServiceClient for unit tests."""
    client = AsyncMock()
    client.get_plan_progress = AsyncMock(return_value=None)
    client.get_plan_tasks = AsyncMock(return_value=[])
    client.get_plan_timeline = AsyncMock(return_value=None)
    client.query_agent_metrics = AsyncMock(return_value=None)
    return client
```

---

### Test Execution Plan

**Day 1:**
- Task 1: 8+ unit tests (Tracker DTOs)
- Task 2: 6+ unit tests (TrackerServiceClient)
- Task 3: 5+ unit tests (TrackerClient wrapper)

**Day 2:**
- Task 6: 8+ unit tests (Event subscribers)
- Task 7: 6+ unit tests (Query API endpoints)

**Day 3:**
- Task 9: 4+ integration tests (End-to-end flow)

**Total Tests:** 37+ new tests  
**Existing Tests:** 51 passing (Phase 2)  
**Phase 3 Target:** 88+ total tests passing

---

## 5. Forward Deployed Logic (FDE) Decisions

### FDE Decision 1: Tracker Service UI

**Question:** Build UI for Tracker Service visualization?

**Decision:** ✅ **DEFER to Post-Launch**

**Rationale:**
- **Scope:** UI would add 2-3 days (React frontend, charts, real-time updates)
- **Necessity:** Query APIs sufficient for Phase 3 validation
- **Alternative:** Use `curl` / Postman for manual testing during Phase 3
- **Future:** Build Tracker Dashboard UI in Stage 5+ or post-launch

**FDE Implementation:**

Instead of:
```bash
# Full UI (deferred)
- Tracker Dashboard React app
- Real-time progress charts
- Event timeline visualization
- Agent performance graphs
```

Use:
```bash
# FDE: Manual queries
curl -H "X-Tenant-ID: $TENANT_ID" \
     -H "X-User-ID: $USER_ID" \
     http://localhost:8084/v1/tracker/plans/$PLAN_ID | jq

# Or Postman collection for manual testing
```

**Impact:** Saves 2-3 days, no blocker for Phase 3 goals

---

### FDE Decision 2: Advanced Tracker Features

**Question:** Implement advanced features (metrics aggregation, alerting)?

**Decision:** ✅ **DEFER to Stage 5+**

**Rationale:**
- **Scope:** Metrics aggregation (cron job), alerting (webhooks) would add 2-4 days
- **MVP:** Basic progress tracking sufficient for Stage 4 validation
- **Future:** Add advanced features when platform scales

**Deferred Features:**
- Agent metrics aggregation (hourly/daily rollups)
- Alerting on task failures (webhooks, email)
- Performance anomaly detection
- SLA monitoring

**Impact:** Saves 2-4 days, can add later as needed

---

### FDE Decision 3: Conditional State Transitions

**Question:** Add conditional transitions to state machine (from Master Plan deferred work)?

**Decision:** ✅ **REMAIN DEFERRED (already in DEFERRED_WORK.md)**

**Rationale:**
- Phase 3 focuses on validation, not new features
- Simple event-based transitions sufficient for research-advisor example
- Conditional transitions documented for Stage 5+

**No Action:** This was already deferred in Phase 2, continues to be deferred

---

## 6. Risks & Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Tracker Service lag** | Medium | Low | Async event processing, no blocking operations |
| **PostgreSQL RLS overhead** | Low | Low | RLS policies use indexed columns (tenant_id) |
| **Example refactor breaks functionality** | Medium | High | Keep planner_legacy.py backup, integration tests validate |
| **TrackerClient wrapper missing methods** | Medium | Medium | Follow pattern from MemoryClient, comprehensive tests |
| **Integration test flakiness** | Medium | Medium | Add retries, increase timeouts, isolate test data |

---

## 7. Dependencies & Coordination

### Upstream Dependencies (Must be complete)

- [x] ✅ **Phase 1:** PlanContext state machine (51 tests passing)
- [x] ✅ **Phase 2:** ChoreographyPlanner, PlannerDecision, PlanContext.create_from_goal()
- [x] ✅ **Tracking DTOs:** TaskState, TaskProgressEvent, TaskStateChanged (soorma-common)
- [x] ✅ **PostgreSQL:** Database running for Tracker storage
- [x] ✅ **Event Bus:** RedPanda/Kafka topics for event subscriptions

### Downstream Enablement (Unblocks)

- **Stage 5:** EventSelector utility (RF-SDK-017) can use Tracker metrics
- **Examples Phase 4:** Future examples can use Tracker for observability
- **Production Readiness:** Tracker enables workflow monitoring at scale

---

## 8. Definition of Done

### Code Complete

- [ ] All 10 tasks completed
- [ ] 37+ new tests passing (88+ total including Phase 1+2)
- [ ] Test coverage ≥85% on new code
- [ ] research-advisor planner refactored: ≤60 lines (≥85% reduction)
- [ ] TrackerClient wrapper exists in PlatformContext
- [ ] Tracker Service running and subscribing to events
- [ ] Integration tests validate end-to-end flow

### Documentation Complete

- [ ] CHANGELOG.md updated (SDK, soorma-common, Tracker Service)
- [ ] Tracker Service README.md created (API docs, deployment)
- [ ] research-advisor README.md updated (new ChoreographyPlanner usage)
- [ ] research-advisor ARCHITECTURE.md updated (design changes)
- [ ] Master Plan updated (Phase 3 completion date, metrics)

### Validation Complete

- [ ] Example runs end-to-end: `soorma dev` + `python planner.py`
- [ ] Manual tracker query returns plan progress: `curl http://localhost:8084/v1/tracker/plans/{id}`
- [ ] No regressions: All existing tests still pass
- [ ] Code review: Architectural patterns verified (ARCHITECTURE_PATTERNS.md compliance)

### Metrics Achieved

- [ ] **Code Reduction:** 472 → ≤60 lines (≥85%)
- [ ] **Test Count:** 88+ tests passing
- [ ] **Coverage:** ≥85% on new code
- [ ] **API Latency:** Tracker queries <200ms (manual test)

---

## 9. Success Criteria

Phase 3 is complete when:

1. ✅ **Example Validates Design:** research-advisor demonstrates ChoreographyPlanner reducing code from ~472 lines to ≤60 lines
2. ✅ **Tracker Service Operational:** Service subscribes to events, stores progress, responds to queries
3. ✅ **SDK Two-Layer Compliance:** TrackerClient wrapper in PlatformContext, examples use `context.tracker.*`
4. ✅ **Integration Tests Pass:** End-to-end flow (goal → planner → worker → tracker query) validated
5. ✅ **Documentation Complete:** READMEs, CHANGELOGs, ARCHITECTURE.md updated
6. ✅ **No Regressions:** All Phase 1+2 tests still pass (51+ tests)
7. ✅ **Developer Approval:** PR reviewed and merged

---

## 10. Next Steps After Phase 3

**Phase 4: Polish - Documentation & Migration (Days 11-12)**
- Update `docs/agent_patterns/README.md` with Planner patterns
- Update `docs/agent_patterns/ARCHITECTURE.md` with design details
- Create `docs/refactoring/sdk/09-PLANNER-MIGRATION.md` migration guide
- Update refactoring README with Stage 4 completion status
- Final testing and release preparation

**Post-Stage 4 Enhancements (Deferred Work):**
- Tracker Service UI (deferred from Phase 3)
- EventSelector utility (RF-SDK-017, deferred from Phase 2)
- Conditional state transitions (deferred from Phase 2)
- Advanced metrics aggregation (deferred from Phase 3)

---

## 11. Approval & Sign-Off

**Action Plan Created:** February 21, 2026  
**Created By:** AI Assistant (Senior Architect)  
**Status:** 📋 Awaiting Developer Approval

**Developer Checklist:**
- [ ] Action Plan reviewed for completeness
- [ ] Two-layer SDK verification confirmed
- [ ] TDD strategy approved
- [ ] FDE decisions accepted
- [ ] Task sequence makes sense
- [ ] Approval to proceed with implementation

**Next Action:** Developer commits this plan, agent proceeds with Task 1 (Tracker DTOs)

---

**End of Action Plan**
