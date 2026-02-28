# Action Plan: Phase 1 - Schema Registry & DTOs (SOOR-DISC-P1)

**Status:** 📋 Planning  
**Parent Plan:** [MASTER_PLAN_Enhanced_Discovery.md](MASTER_PLAN_Enhanced_Discovery.md)  
**Phase:** 1 of 5  
**Estimated Duration:** 2-3 days (16 hours)  
**Target Release:** v0.8.1  
**Last Updated:** February 28, 2026

---

## 1. Requirements & Core Objective

### Phase Objective

Establish the foundational data models, database schema, and multi-tenancy layer for the Discovery & Schema Registry system.

**From Master Plan Section 3 - Phase 1:**
- Create new Pydantic DTOs in `soorma-common` for schema registry
- Design and implement database schema for `payload_schemas` table
- Add multi-tenancy columns (`tenant_id`, `user_id`, `version`) to existing `agents` and `events` tables
- Implement PostgreSQL Row-Level Security (RLS) policies
- Create Alembic migration scripts
- Implement unit tests for DTOs and migration

### Acceptance Criteria

- [ ] New DTOs defined in `soorma-common` with proper type hints and docstrings
- [ ] `payload_schemas` table created with version support
- [ ] Multi-tenancy columns added to `agents` and `events` tables
- [ ] RLS policies enforce tenant isolation at database level
- [ ] Alembic migration script completes successfully
- [ ] Migration rollback tested and documented
- [ ] 100% unit test coverage for new DTOs
- [ ] No breaking changes to existing code (DTOs are additive)

### Refactoring Tasks Addressed

| Task ID | Description | Status |
|---------|-------------|--------|
| RF-ARCH-005 | Schema registration by name (foundation) | 🟡 In Progress |
| RF-ARCH-006 | Structured capabilities with EventDefinition (DTOs) | 🟡 In Progress |

---

## 2. Technical Design

### Component Overview

**Primary Components:**
- `libs/soorma-common/src/soorma_common/models.py` - New DTOs
- `services/registry/alembic/versions/003_schema_registry.py` - Database migration
- `services/registry/src/registry_service/models/schema.py` - SQLAlchemy model (NEW)

**Dependency Chain:**
```
soorma-common (DTOs)
    ↓
Registry Service (Database Models)
    ↓
Alembic Migration (Schema Changes)
```

### Data Models

#### New DTOs in `soorma-common`

**1. PayloadSchema**
```python
class PayloadSchema(BaseDTO):
    """Payload schema definition with versioning."""
    schema_name: str = Field(..., description="Unique schema name (e.g., 'research_request_v1')")
    version: str = Field(..., description="Semantic version (e.g., '1.0.0')")
    json_schema: Dict[str, Any] = Field(..., description="JSON Schema definition")
    description: Optional[str] = Field(None, description="Human-readable description")
    owner_agent_id: Optional[str] = Field(None, description="Agent ID that owns this schema")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
```

**2. PayloadSchemaRegistration**
```python
class PayloadSchemaRegistration(BaseDTO):
    """Request to register a payload schema."""
    schema_name: str = Field(..., description="Unique schema name")
    version: str = Field(..., description="Schema version (semantic versioning)")
    json_schema: Dict[str, Any] = Field(..., description="JSON Schema object")
    description: Optional[str] = Field(None, description="Schema description")
    # Note: tenant_id/user_id come from authentication headers, not request body
```

**3. PayloadSchemaResponse**
```python
class PayloadSchemaResponse(BaseDTO):
    """Response after schema registration."""
    schema_name: str = Field(..., description="Registered schema name")
    version: str = Field(..., description="Schema version")
    success: bool = Field(..., description="Whether registration was successful")
    message: str = Field(..., description="Success or error message")
```

**4. Enhanced EventDefinition** (modify existing)
```python
class EventDefinition(BaseDTO):
    """Defines a single event in the system."""
    event_name: str = ...  # Existing
    topic: str = ...  # Existing
    description: str = ...  # Existing
    
    # NEW: Schema references (replaces embedded schemas)
    payload_schema_name: Optional[str] = Field(
        None, 
        description="Reference to registered payload schema by name"
    )
    response_schema_name: Optional[str] = Field(
        None,
        description="Reference to registered response schema by name"
    )
    
    # DEPRECATED (keep for backward compatibility during migration)
    payload_schema: Optional[Dict[str, Any]] = Field(
        None, 
        description="[DEPRECATED] Embedded JSON schema - use payload_schema_name instead"
    )
    response_schema: Optional[Dict[str, Any]] = Field(
        None,
        description="[DEPRECATED] Embedded JSON schema - use response_schema_name instead"
    )
```

**5. Enhanced AgentCapability** (modify existing)
```python
class AgentCapability(BaseDTO):
    """Agent capability with structured event definitions."""
    task_name: str = ...  # Existing
    description: str = ...  # Existing
    
    # BREAKING CHANGE: consumed_event becomes EventDefinition object
    consumed_event: Union[str, EventDefinition] = Field(
        ...,
        description="Event that triggers this capability (string for backward compat, EventDefinition for v0.8.1+)"
    )
    
    # BREAKING CHANGE: produced_events become EventDefinition objects
    produced_events: Union[List[str], List[EventDefinition]] = Field(
        ...,
        description="Events produced by this capability (strings for backward compat, EventDefinition for v0.8.1+)"
    )
```

**6. DiscoveredAgent** (NEW)
```python
class DiscoveredAgent(BaseDTO):
    """Agent discovery result with full capability metadata."""
    agent_id: str = Field(..., description="Agent identifier")
    name: str = Field(..., description="Agent name with version")
    description: str = Field(..., description="Agent description")
    version: str = Field(..., description="Agent version")
    capabilities: List[AgentCapability] = Field(..., description="Capabilities with full event definitions")
    
    # Helper methods for schema access
    def get_consumed_schemas(self) -> List[str]:
        """Extract all payload schema names from consumed events."""
        pass
    
    def get_produced_schemas(self) -> List[str]:
        """Extract all payload schema names from produced events."""
        pass
```

#### Database Schema Changes

**New Table: `payload_schemas`**
```sql
CREATE TABLE payload_schemas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Schema identification
    schema_name VARCHAR(255) NOT NULL,
    version VARCHAR(50) NOT NULL,
    
    -- Schema content
    json_schema JSONB NOT NULL,
    description TEXT,
    
    -- Ownership and multi-tenancy
    owner_agent_id VARCHAR(255),  -- Foreign key to agents.agent_id (optional)
    tenant_id UUID NOT NULL,
    user_id UUID NOT NULL,
    
    -- Constraints
    CONSTRAINT uq_schema_name_version_tenant UNIQUE (schema_name, version, tenant_id)
);

-- Indexes
CREATE INDEX idx_payload_schemas_schema_name ON payload_schemas(schema_name);
CREATE INDEX idx_payload_schemas_tenant_id ON payload_schemas(tenant_id);
CREATE INDEX idx_payload_schemas_owner_agent_id ON payload_schemas(owner_agent_id);
```

**Alter Table: `agents`** (add multi-tenancy)
```sql
ALTER TABLE agents 
    ADD COLUMN tenant_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000',
    ADD COLUMN user_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000',
    ADD COLUMN version VARCHAR(50) DEFAULT '1.0.0';

-- Indexes
CREATE INDEX idx_agents_tenant_id ON agents(tenant_id);
CREATE INDEX idx_agents_version ON agents(version);

-- After migration, remove defaults
ALTER TABLE agents ALTER COLUMN tenant_id DROP DEFAULT;
ALTER TABLE agents ALTER COLUMN user_id DROP DEFAULT;
```

**Alter Table: `events`** (add multi-tenancy and schema references)
```sql
ALTER TABLE events
    ADD COLUMN owner_agent_id VARCHAR(255),
    ADD COLUMN tenant_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000',
    ADD COLUMN user_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000',
    ADD COLUMN payload_schema_name VARCHAR(255),
    ADD COLUMN response_schema_name VARCHAR(255);

-- Indexes
CREATE INDEX idx_events_tenant_id ON events(tenant_id);
CREATE INDEX idx_events_owner_agent_id ON events(owner_agent_id);
CREATE INDEX idx_events_payload_schema_name ON events(payload_schema_name);

-- After migration, remove defaults
ALTER TABLE events ALTER COLUMN tenant_id DROP DEFAULT;
ALTER TABLE events ALTER COLUMN user_id DROP DEFAULT;
```

#### Row-Level Security Policies

**RLS for `payload_schemas`**
```sql
-- Enable RLS
ALTER TABLE payload_schemas ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see their tenant's schemas
CREATE POLICY payload_schemas_tenant_isolation ON payload_schemas
    USING (tenant_id = current_setting('app.tenant_id')::UUID);

-- Policy: Users can only modify their own schemas
CREATE POLICY payload_schemas_user_write ON payload_schemas
    FOR INSERT
    WITH CHECK (
        tenant_id = current_setting('app.tenant_id')::UUID 
        AND user_id = current_setting('app.user_id')::UUID
    );
```

**RLS for `agents`**
```sql
-- Enable RLS
ALTER TABLE agents ENABLE ROW LEVEL SECURITY;

-- Policy: Tenant isolation
CREATE POLICY agents_tenant_isolation ON agents
    USING (tenant_id = current_setting('app.tenant_id')::UUID);

-- Policy: User can register agents in their tenant
CREATE POLICY agents_user_write ON agents
    FOR INSERT
    WITH CHECK (
        tenant_id = current_setting('app.tenant_id')::UUID 
        AND user_id = current_setting('app.user_id')::UUID
    );
```

**RLS for `events`**
```sql
-- Enable RLS
ALTER TABLE events ENABLE ROW LEVEL SECURITY;

-- Policy: Tenant isolation
CREATE POLICY events_tenant_isolation ON events
    USING (tenant_id = current_setting('app.tenant_id')::UUID);

-- Policy: User can register events in their tenant
CREATE POLICY events_user_write ON events
    FOR INSERT
    WITH CHECK (
        tenant_id = current_setting('app.tenant_id')::UUID 
        AND user_id = current_setting('app.user_id')::UUID
    );
```

### SDK Layer Verification

**Phase 1 Impact:** ❌ **No SDK changes in this phase**

Phase 1 focuses on **foundation only** (DTOs and database):
- DTOs are defined in `soorma-common` (no SDK wrapper methods)
- Database schema created in Registry Service
- No new service endpoints in Phase 1
- SDK integration happens in Phase 2 and Phase 3

**Future SDK Work (Phase 2-3):**
- Phase 2: Add service endpoints (`POST /v1/schemas`, `GET /v1/schemas/{name}`)
- Phase 3: Add SDK wrapper methods (`context.registry.register_schema()`, `context.registry.get_schema()`)

**Verification Checklist:**
- [x] **Service Client:** No changes in Phase 1
- [x] **PlatformContext Wrapper:** No changes in Phase 1
- [x] **Examples:** No changes in Phase 1

---

## 3. Task Tracking Matrix

### Task Sequence

**Design Phase**
- [x] **Task 1.1:** Review ARCHITECTURE_PATTERNS.md (Gateway verification) ⏱️ 30 min
- [ ] **Task 1.2:** Design DTOs (Pydantic models) ⏱️ 2 hours
- [ ] **Task 1.3:** Design database schema (ERD) ⏱️ 2 hours
- [ ] **Task 1.4:** Design RLS policies ⏱️ 1 hour

**TDD Cycle Phase**
- [ ] **Task 2.1:** STUB - Create DTO skeletons with `NotImplementedError` ⏱️ 1 hour
- [ ] **Task 2.2:** RED - Write DTO validation tests (expect failure) ⏱️ 2 hours
- [ ] **Task 2.3:** GREEN - Implement DTO logic (pass tests) ⏱️ 1 hour
- [ ] **Task 2.4:** REFACTOR - Clean up DTO code ⏱️ 30 min

**Database Phase**
- [ ] **Task 3.1:** STUB - Create migration file with schema comments ⏱️ 1 hour
- [ ] **Task 3.2:** RED - Write migration tests (expect failure) ⏱️ 1.5 hours
- [ ] **Task 3.3:** GREEN - Implement migration script ⏱️ 2 hours
- [ ] **Task 3.4:** REFACTOR - Test rollback and document ⏱️ 1 hour

**SQLAlchemy Models Phase**
- [ ] **Task 4.1:** STUB - Create SQLAlchemy model stub ⏱️ 30 min
- [ ] **Task 4.2:** RED - Write model tests (expect failure) ⏱️ 1 hour
- [ ] **Task 4.3:** GREEN - Implement SQLAlchemy models ⏱️ 1 hour
- [ ] **Task 4.4:** REFACTOR - Align with base model patterns ⏱️ 30 min

**Documentation Phase**
- [ ] **Task 5.1:** Update `soorma-common` CHANGELOG.md ⏱️ 15 min
- [ ] **Task 5.2:** Update Registry Service CHANGELOG.md ⏱️ 15 min
- [ ] **Task 5.3:** Document migration guide (breaking changes) ⏱️ 30 min
- [ ] **Task 5.4:** Plan review and approval ⏱️ 30 min

**48-Hour Filter Decision:**
- [ ] **Task 48H:** FDE Decision - All components are CRITICAL (see Section 5)

---

## 4. TDD Strategy

### Test Structure

```
libs/soorma-common/tests/
    test_registry_dtos.py          # New DTO validation tests

services/registry/tests/
    test_migrations.py             # New migration tests
    test_rls_policies.py           # New RLS policy tests
    models/
        test_schema_model.py       # New SQLAlchemy model tests
```

### Unit Tests: DTOs (libs/soorma-common)

**File:** `libs/soorma-common/tests/test_registry_dtos.py`

**Test Cases:**
1. **PayloadSchema Validation**
   ```python
   def test_payload_schema_valid():
       """Valid schema passes validation."""
       schema = PayloadSchema(
           schema_name="research_request_v1",
           version="1.0.0",
           json_schema={"type": "object", "properties": {"query": {"type": "string"}}}
       )
       assert schema.schema_name == "research_request_v1"
       assert schema.version == "1.0.0"
   
   def test_payload_schema_invalid_name():
       """Schema name must not be empty."""
       with pytest.raises(ValidationError):
           PayloadSchema(schema_name="", version="1.0.0", json_schema={})
   
   def test_payload_schema_camel_case_serialization():
       """DTO serializes to camelCase."""
       schema = PayloadSchema(
           schema_name="test_v1",
           version="1.0.0",
           json_schema={}
       )
       json_data = schema.model_dump(by_alias=True)
       assert "schemaName" in json_data
       assert "jsonSchema" in json_data
   ```

2. **Enhanced EventDefinition**
   ```python
   def test_event_definition_with_schema_reference():
       """EventDefinition with schema_name reference."""
       event = EventDefinition(
           event_name="research.requested",
           topic="action-requests",
           description="Research request event",
           payload_schema_name="research_request_v1"
       )
       assert event.payload_schema_name == "research_request_v1"
       assert event.payload_schema is None  # Deprecated field
   
   def test_event_definition_backward_compat():
       """EventDefinition accepts embedded schema (deprecated)."""
       event = EventDefinition(
           event_name="research.requested",
           topic="action-requests",
           description="Research request event",
           payload_schema={"type": "object"}
       )
       assert event.payload_schema is not None
       assert event.payload_schema_name is None
   ```

3. **Enhanced AgentCapability**
   ```python
   def test_agent_capability_with_event_definition():
       """AgentCapability with EventDefinition objects."""
       capability = AgentCapability(
           task_name="web_research",
           description="Performs web research",
           consumed_event=EventDefinition(
               event_name="research.requested",
               topic="action-requests",
               description="...",
               payload_schema_name="research_request_v1"
           ),
           produced_events=[
               EventDefinition(
                   event_name="research.completed",
                   topic="action-results",
                   description="...",
                   payload_schema_name="research_result_v1"
               )
           ]
       )
       assert isinstance(capability.consumed_event, EventDefinition)
       assert len(capability.produced_events) == 1
   
   def test_agent_capability_backward_compat_strings():
       """AgentCapability accepts strings (deprecated)."""
       capability = AgentCapability(
           task_name="web_research",
           description="Performs web research",
           consumed_event="research.requested",
           produced_events=["research.completed"]
       )
       assert isinstance(capability.consumed_event, str)
       assert isinstance(capability.produced_events[0], str)
   ```

4. **DiscoveredAgent**
   ```python
   def test_discovered_agent_schema_extraction():
       """DiscoveredAgent extracts schema names."""
       agent = DiscoveredAgent(
           agent_id="worker-001",
           name="Research Worker:1.0.0",
           description="...",
           version="1.0.0",
           capabilities=[
               AgentCapability(
                   task_name="research",
                   description="...",
                   consumed_event=EventDefinition(
                       event_name="research.requested",
                       topic="action-requests",
                       description="...",
                       payload_schema_name="research_request_v1"
                   ),
                   produced_events=[
                       EventDefinition(
                           event_name="research.completed",
                           topic="action-results",
                           description="...",
                           payload_schema_name="research_result_v1"
                       )
                   ]
               )
           ]
       )
       consumed_schemas = agent.get_consumed_schemas()
       assert "research_request_v1" in consumed_schemas
       
       produced_schemas = agent.get_produced_schemas()
       assert "research_result_v1" in produced_schemas
   ```

**Expected Test Count:** 15-20 unit tests

### Integration Tests: Database Migration

**File:** `services/registry/tests/test_migrations.py`

**Test Cases:**
1. **Migration Execution**
   ```python
   @pytest.mark.asyncio
   async def test_migration_003_creates_payload_schemas_table(db_engine):
       """Migration creates payload_schemas table."""
       # Run migration
       alembic_cfg = Config("alembic.ini")
       command.upgrade(alembic_cfg, "003")
       
       # Verify table exists
       async with db_engine.begin() as conn:
           result = await conn.execute(text(
               "SELECT table_name FROM information_schema.tables "
               "WHERE table_name = 'payload_schemas'"
           ))
           assert result.scalar() == "payload_schemas"
   
   @pytest.mark.asyncio
   async def test_migration_003_adds_tenant_columns_to_agents(db_engine):
       """Migration adds tenant_id/user_id to agents table."""
       async with db_engine.begin() as conn:
           result = await conn.execute(text(
               "SELECT column_name FROM information_schema.columns "
               "WHERE table_name = 'agents' AND column_name IN ('tenant_id', 'user_id', 'version')"
           ))
           columns = [row[0] for row in result]
           assert "tenant_id" in columns
           assert "user_id" in columns
           assert "version" in columns
   
   @pytest.mark.asyncio
   async def test_migration_003_rollback(db_engine):
       """Migration rollback removes changes."""
       alembic_cfg = Config("alembic.ini")
       command.downgrade(alembic_cfg, "-1")
       
       async with db_engine.begin() as conn:
           result = await conn.execute(text(
               "SELECT table_name FROM information_schema.tables "
               "WHERE table_name = 'payload_schemas'"
           ))
           assert result.scalar() is None
   ```

**Expected Test Count:** 6-8 integration tests

### Integration Tests: RLS Policies

**File:** `services/registry/tests/test_rls_policies.py`

**Test Cases:**
1. **Tenant Isolation**
   ```python
   @pytest.mark.asyncio
   async def test_rls_payload_schemas_tenant_isolation(db_session):
       """RLS enforces tenant isolation for payload_schemas."""
       # Set session variables for tenant A
       await db_session.execute(text("SET app.tenant_id = 'tenant-a-uuid'"))
       await db_session.execute(text("SET app.user_id = 'user-a-uuid'"))
       
       # Insert schema for tenant A
       await db_session.execute(text(
           "INSERT INTO payload_schemas (schema_name, version, json_schema, tenant_id, user_id) "
           "VALUES ('schema_a', '1.0.0', '{}', 'tenant-a-uuid', 'user-a-uuid')"
       ))
       
       # Switch to tenant B
       await db_session.execute(text("SET app.tenant_id = 'tenant-b-uuid'"))
       
       # Verify tenant B cannot see tenant A's schema
       result = await db_session.execute(text(
           "SELECT COUNT(*) FROM payload_schemas WHERE schema_name = 'schema_a'"
       ))
       assert result.scalar() == 0
   
   @pytest.mark.asyncio
   async def test_rls_agents_tenant_isolation(db_session):
       """RLS enforces tenant isolation for agents."""
       # Similar test for agents table
       pass
   
   @pytest.mark.asyncio
   async def test_rls_events_tenant_isolation(db_session):
       """RLS enforces tenant isolation for events."""
       # Similar test for events table
       pass
   ```

**Expected Test Count:** 6-9 integration tests

### Test Fixtures

**PostgreSQL Test Container** (required for RLS testing)
```python
# services/registry/tests/conftest.py

import pytest
from testcontainers.postgres import PostgresContainer

@pytest.fixture(scope="session")
def postgres_container():
    """PostgreSQL container for RLS testing."""
    with PostgresContainer("postgres:15") as postgres:
        yield postgres

@pytest.fixture(scope="session")
def db_engine(postgres_container):
    """Database engine with test database."""
    from sqlalchemy.ext.asyncio import create_async_engine
    engine = create_async_engine(
        postgres_container.get_connection_url().replace("postgresql://", "postgresql+asyncpg://")
    )
    yield engine
    engine.sync_engine.dispose()

@pytest.fixture
async def db_session(db_engine):
    """Database session with transaction rollback."""
    async with db_engine.begin() as conn:
        yield conn
        await conn.rollback()
```

---

## 5. Forward Deployed Logic Decision

### FDE Analysis: Full Implementation (NO Deferrals)

**Decision:** ✅ **Implement all Phase 1 components as specified**

**Rationale:**
All Phase 1 components are foundational and interdependent. Deferring any component would block subsequent phases.

| Component | Effort | FDE Option | Impact if Deferred | Decision |
|-----------|--------|------------|-------------------|----------|
| **DTOs** | 4h | ❌ None | Blocks all phases | IMPLEMENT |
| **`payload_schemas` Table** | 3h | Skip table, use embedded schemas | ❌ Loses dynamic event support (core Stage 5 value) | IMPLEMENT |
| **Multi-Tenancy Columns** | 2h | Skip tenant isolation | ❌ Critical security vulnerability | IMPLEMENT |
| **RLS Policies** | 2h | Use app-level filtering | ❌ Perpetuates security debt | IMPLEMENT |
| **Migration Script** | 3h | Manual SQL scripts | ❌ Deployment complexity, no rollback | IMPLEMENT |
| **Tests** | 6h | Skip tests | ❌ No validation, regression risk | IMPLEMENT |

**Conclusion:**
- **Time Estimate:** 16 hours (2 days)
- **FDE Savings:** 0 hours (no deferrals)
- **Risk:** Low (all components are well-scoped)

**This phase is already minimal and cannot be reduced further without compromising the entire Stage 5 goals.**

---

## 6. Implementation Plan (Day-by-Day)

### Day 1: DTOs and Design (6-7 hours)

**Morning (3-4 hours):**
1. Task 1.1: Review ARCHITECTURE_PATTERNS.md (✅ COMPLETED)
2. Task 1.2: Design and document DTOs
3. Task 2.1: STUB - Create DTO skeletons in `soorma-common`
4. Task 2.2: RED - Write DTO validation tests

**Afternoon (3 hours):**
5. Task 2.3: GREEN - Implement DTO logic
6. Task 2.4: REFACTOR - Clean up and validate
7. Task 1.3: Design database schema (ERD and SQL)
8. Task 1.4: Design RLS policies

**Deliverables:**
- [ ] DTOs in `libs/soorma-common/src/soorma_common/models.py`
- [ ] DTO tests in `libs/soorma-common/tests/test_registry_dtos.py`
- [ ] Database schema design document (embedded in migration file comments)

### Day 2: Database Schema and Migration (6-7 hours)

**Morning (3-4 hours):**
1. Task 3.1: STUB - Create migration file structure
2. Task 3.2: RED - Write migration tests
3. Task 4.1: STUB - Create SQLAlchemy model stubs

**Afternoon (3 hours):**
4. Task 3.3: GREEN - Implement migration script
5. Task 4.3: GREEN - Implement SQLAlchemy models
6. Task 3.4: REFACTOR - Test rollback

**Deliverables:**
- [ ] Migration: `services/registry/alembic/versions/003_schema_registry.py`
- [ ] SQLAlchemy model: `services/registry/src/registry_service/models/schema.py`
- [ ] Migration tests: `services/registry/tests/test_migrations.py`

### Day 3: RLS and Documentation (3-4 hours)

**Morning (2 hours):**
1. Task 4.2: RED - Write RLS policy tests
2. Implement RLS policies in migration

**Afternoon (1-2 hours):**
3. Task 4.4: REFACTOR - Integration testing
4. Task 5.1-5.4: Documentation updates

**Deliverables:**
- [ ] RLS tests: `services/registry/tests/test_rls_policies.py`
- [ ] Updated CHANGELOGs
- [ ] Migration guide for breaking changes

---

## 7. Breaking Changes & Migration Guide

### Breaking Changes in v0.8.1

**1. AgentCapability Structure**
- **Old:** `consumed_event` is a `string`
- **New:** `consumed_event` is an `EventDefinition` object
- **Backward Compatibility:** Union type `Union[str, EventDefinition]` during transition
- **Migration Deadline:** v1.0.0 (strings will be removed)

**2. EventDefinition Schema References**
- **Old:** `payload_schema` is an embedded JSON object
- **New:** `payload_schema_name` is a string reference to registered schema
- **Backward Compatibility:** Both fields supported during transition
- **Migration Deadline:** v1.0.0 (embedded schemas will be removed)

**3. Database Schema**
- **Breaking:** `agents` and `events` tables require `tenant_id` and `user_id`
- **Migration Strategy:** Pre-launch phase allows clean break (no backfill)
- **Action Required:** Users must recreate agent/event registrations with new authentication headers

### Migration Steps for Developers

**Step 1: Update `soorma-common`**
```bash
pip install --upgrade soorma-common==0.8.1
```

**Step 2: Update Agent Registration Code**
```python
# OLD (v0.8.0)
agent = AgentDefinition(
    agent_id="worker-001",
    capabilities=[
        {
            "taskName": "research",
            "description": "...",
            "consumedEvent": "research.requested",  # String
            "producedEvents": ["research.completed"]
        }
    ]
)

# NEW (v0.8.1+)
from soorma_common import AgentDefinition, AgentCapability, EventDefinition

agent = AgentDefinition(
    agent_id="worker-001",
    version="1.0.0",  # Required
    capabilities=[
        AgentCapability(
            task_name="research",
            description="...",
            consumed_event=EventDefinition(
                event_name="research.requested",
                topic="action-requests",
                description="...",
                payload_schema_name="research_request_v1"  # Schema reference
            ),
            produced_events=[
                EventDefinition(
                    event_name="research.completed",
                    topic="action-results",
                    description="...",
                    payload_schema_name="research_result_v1"
                )
            ]
        )
    ]
)
```

**Step 3: Register Schemas Separately**
```python
# Register payload schema (Phase 3 SDK wrapper - placeholder for now)
await registry_client.register_schema(
    schema_name="research_request_v1",
    version="1.0.0",
    json_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "max_results": {"type": "integer"}
        },
        "required": ["query"]
    }
)
```

**Step 4: Run Database Migration**
```bash
cd services/registry
alembic upgrade head
```

---

## 8. Dependencies & Blockers

### External Dependencies

| Dependency | Version | Purpose | Status |
|------------|---------|---------|--------|
| PostgreSQL | 15+ | Database with RLS support | ✅ Available |
| SQLAlchemy | 2.0+ | ORM for database models | ✅ Installed |
| Alembic | 1.13+ | Database migrations | ✅ Installed |
| Pydantic | 2.0+ | DTO validation | ✅ Installed |
| pytest | 8.0+ | Testing framework | ✅ Installed |
| testcontainers | 3.7+ | PostgreSQL test container | ⚠️ Need to install |

### Blockers

❌ **No blockers for Phase 1**

### Prerequisites

- [x] ARCHITECTURE_PATTERNS.md reviewed (mandatory gateway)
- [x] Master Plan approved by developer
- [x] PostgreSQL 15+ database available for testing
- [ ] `testcontainers` Python package installed for RLS tests

---

## 9. Success Metrics

### Code Quality

- [ ] 100% type hint coverage (all functions have proper types)
- [ ] 100% docstring coverage (Google-style)
- [ ] All DTOs validated with Pydantic
- [ ] All SQLAlchemy models inherit from `Base`

### Test Coverage

- [ ] Unit tests: 100% coverage for DTOs
- [ ] Integration tests: Migration script tested with rollback
- [ ] Integration tests: RLS policies verified for tenant isolation
- [ ] Total test count: 25+ tests

### Documentation

- [ ] CHANGELOG.md updated in `soorma-common`
- [ ] CHANGELOG.md updated in `services/registry`
- [ ] Migration guide documented for breaking changes
- [ ] Database schema documented in migration file

### Performance

- [ ] Migration completes in <10 seconds (empty database)
- [ ] RLS overhead <10% query time increase

---

## 10. Phase Completion Checklist

Before marking Phase 1 complete and proceeding to Phase 2:

- [ ] All tasks marked as completed in Section 3
- [ ] All tests passing (unit + integration)
- [ ] Migration tested forward and backward (upgrade + downgrade)
- [ ] RLS policies verified (no cross-tenant leakage)
- [ ] CHANGELOGs updated
- [ ] Code review completed (if applicable)
- [ ] Breaking changes documented
- [ ] Tag release: `v0.8.1-alpha.1` (Phase 1 complete)

**Next Phase:** [ACTION_PLAN_Phase2_Service.md](ACTION_PLAN_Phase2_Service.md) (to be created)

---

## 11. Notes & Decisions

### Design Decisions

**Decision 1: Union Types for Backward Compatibility**
- **Rationale:** Allow gradual migration from string-based to object-based event definitions
- **Tradeoff:** Slightly more complex validation logic
- **Expiration:** v1.0.0 (remove string support)

**Decision 2: Breaking Changes Acceptable in Pre-Launch**
- **Rationale:** Per refactoring principles, architectural correctness > backward compatibility
- **Impact:** Small user base (mostly internal), clean break simplifies future maintenance
- **Mitigation:** Comprehensive migration guide in documentation

**Decision 3: RLS at Database Layer**
- **Rationale:** PostgreSQL RLS enforces tenant isolation at query level (bulletproof)
- **Tradeoff:** Minor performance overhead (~5-10%)
- **Alternative Rejected:** App-level filtering (error-prone, security gaps)

**Decision 4: Schema Registry as Separate Table**
- **Rationale:** Enables dynamic event types with discoverable schemas
- **Tradeoff:** Additional JOIN queries for schema lookups
- **Alternative Rejected:** Embedded schemas (loses core Stage 5 value)

### Technical Debt

**Debt Item 1: Union Types (Temporary)**
- **Location:** `AgentCapability` consumed_event/produced_events
- **Cleanup:** v1.0.0 - remove string support, require EventDefinition objects
- **Tracking:** DEFERRED_WORK.md

**Debt Item 2: Deprecated Fields**
- **Location:** `EventDefinition` payload_schema/response_schema
- **Cleanup:** v1.0.0 - remove embedded schema fields
- **Tracking:** DEFERRED_WORK.md

### Questions & Answers

**Q1: Why not defer multi-tenancy to v0.9.0?**
- **A:** Multi-tenancy is a foundational security requirement. Retrofitting later creates migration complexity and security debt. Implementing now (with RLS) is the "right architecture."

**Q2: Why PostgreSQL-specific (RLS)?**
- **A:** RLS is the gold standard for tenant isolation. SQLite alternative would require app-level filtering (less secure, more code). Stage 5 targets production readiness.

**Q3: Can we skip schema versioning?**
- **A:** No. Schema versioning is core to A2A protocol compatibility and allows schema evolution without breaking existing agents.

---

**Plan Status:** 📋 Awaiting Developer Approval  
**Estimated Start Date:** TBD  
**Estimated Completion Date:** TBD (2-3 days after approval)  
**Author:** GitHub Copilot (Senior Architect)  
**Reviewer:** [Pending]
