# Action Plan: Phase 1 - Schema Registry & DTOs (SOOR-DISC-P1)

**Status:** ✅ Approved  
**Parent Plan:** [MASTER_PLAN_Enhanced_Discovery.md](MASTER_PLAN_Enhanced_Discovery.md)  
**Phase:** 1 of 5  
**Estimated Duration:** 3-4 days (18-20 hours including examples update)  
**Target Release:** v0.8.1  
**Last Updated:** February 28, 2026  
**Approved By:** Developer  
**Approval Date:** February 28, 2026

### Approved Decisions Summary

| # | Decision | Approach | Impact |
|---|----------|----------|---------|
| 1 | Breaking Changes | **Clean break** (no Union types) | All examples must be updated |
| 2 | Uniqueness Scope | **Tenant-scoped** unique constraints | Multi-tenant namespaces |
| 3 | Migration Strategy | **Default UUIDs** approach | Safe rollback, no data loss |
| 4 | Test Infrastructure | **testcontainers** (Docker PostgreSQL) | Automatic setup/teardown |
| 5 | Schema Versioning | **Semantic versioning** (e.g., "1.0.0") | A2A compatibility |
| 6 | Timeline | **2-3 days** (16 hours) | Accepted |
| 7 | RLS Pattern | **PostgreSQL session variables** | Consistent with Memory/Tracker |
| 8 | FK Constraints | **No FK** to agents.agent_id | Simpler lifecycle management |

**Merge Readiness:** All affected components identified (DTOs, services, SDK, examples, docs)

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
    
    # BREAKING CHANGE: consumed_event must be EventDefinition object (no backward compatibility)
    consumed_event: EventDefinition = Field(
        ...,
        description="Event that triggers this capability (EventDefinition object required in v0.8.1+)"
    )
    
    # BREAKING CHANGE: produced_events must be EventDefinition objects (no backward compatibility)
    produced_events: List[EventDefinition] = Field(
        ...,
        description="Events produced by this capability (List[EventDefinition] required in v0.8.1+)"
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
    owner_agent_id VARCHAR(255),  -- Reference to agents.agent_id (optional, no FK constraint)
    tenant_id UUID NOT NULL,      -- Authentication context from JWT (validated by Identity service upstream)
    user_id UUID NOT NULL,        -- Authentication context from JWT (validated by Identity service upstream)
    
    -- Constraints
    CONSTRAINT uq_schema_name_version_tenant UNIQUE (schema_name, version, tenant_id)
);

-- Add column comments for clarity
COMMENT ON COLUMN payload_schemas.tenant_id IS 'Tenant identifier from validated JWT/API Key (no FK - Identity service owns tenant entity)';
COMMENT ON COLUMN payload_schemas.user_id IS 'User identifier from validated JWT/API Key (no FK - Identity service owns user entity)';

-- Indexes optimized for RLS query patterns
-- Composite index: RLS queries filter by tenant_id first, then schema_name
CREATE INDEX idx_payload_schemas_tenant_schema ON payload_schemas(tenant_id, schema_name);
CREATE INDEX idx_payload_schemas_owner_agent_id ON payload_schemas(owner_agent_id);

-- Note: Standalone tenant_id index is redundant (covered by composite index above)
```

**Alter Table: `agents`** (add multi-tenancy)
```sql
ALTER TABLE agents 
    ADD COLUMN tenant_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000',
    ADD COLUMN user_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000',
    ADD COLUMN version VARCHAR(50) DEFAULT '1.0.0';

-- Add column comments for clarity
COMMENT ON COLUMN agents.tenant_id IS 'Tenant identifier from validated JWT/API Key (no FK - Identity service owns tenant entity)';
COMMENT ON COLUMN agents.user_id IS 'User identifier from validated JWT/API Key (no FK - Identity service owns user entity)';

-- Indexes optimized for RLS query patterns
-- Composite index: RLS queries filter by tenant_id first, then agent_id
CREATE INDEX idx_agents_tenant_agent ON agents(tenant_id, agent_id);
CREATE INDEX idx_agents_tenant_name ON agents(tenant_id, name);
CREATE INDEX idx_agents_version ON agents(version);

-- BREAKING CHANGE: Remove global unique constraint on agent_id
DROP INDEX IF EXISTS ix_agents_agent_id;

-- Add tenant-scoped unique constraint
CREATE UNIQUE INDEX uq_agents_agent_tenant ON agents(agent_id, tenant_id);

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

-- Add column comments for clarity
COMMENT ON COLUMN events.tenant_id IS 'Tenant identifier from validated JWT/API Key (no FK - Identity service owns tenant entity)';
COMMENT ON COLUMN events.user_id IS 'User identifier from validated JWT/API Key (no FK - Identity service owns user entity)';

-- Indexes optimized for RLS query patterns
-- Composite indexes: RLS queries filter by tenant_id first
CREATE INDEX idx_events_tenant_event ON events(tenant_id, event_name);
CREATE INDEX idx_events_tenant_topic ON events(tenant_id, topic);
CREATE INDEX idx_events_owner_agent_id ON events(owner_agent_id);
CREATE INDEX idx_events_payload_schema_name ON events(payload_schema_name);

-- BREAKING CHANGE: Remove global unique constraint on event_name
DROP INDEX IF EXISTS ix_events_event_name;

-- Add tenant-scoped unique constraint
CREATE UNIQUE INDEX uq_events_event_tenant ON events(event_name, tenant_id);

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
- [ ] **Task 5.4:** Update all examples (01-10) with new DTO format ⏱️ 2 hours
- [ ] **Task 5.5:** Update docs/discovery/README.md ⏱️ 30 min
- [ ] **Task 5.6:** Plan review and approval ⏱️ 30 min

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
   async def test_migration_003_creates_optimized_indexes(db_engine):
       """Migration creates composite indexes for RLS query patterns."""
       async with db_engine.begin() as conn:
           # Check payload_schemas composite index
           result = await conn.execute(text(
               "SELECT indexname FROM pg_indexes "
               "WHERE tablename = 'payload_schemas' AND indexname = 'idx_payload_schemas_tenant_schema'"
           ))
           assert result.scalar() == "idx_payload_schemas_tenant_schema"
           
           # Check agents composite index
           result = await conn.execute(text(
               "SELECT indexname FROM pg_indexes "
               "WHERE tablename = 'agents' AND indexname = 'idx_agents_tenant_agent'"
           ))
           assert result.scalar() == "idx_agents_tenant_agent"
   
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

**Expected Test Count:** 7-9 integration tests

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
from alembic import command
from alembic.config import Config

@pytest.fixture(scope="session")
def postgres_container():
    """PostgreSQL container for RLS testing.
    
    Setup/teardown is automatic:
    - Container starts when first test runs
    - Creates temporary PostgreSQL instance in Docker
    - Container stops and removes when pytest session ends
    - No manual cleanup needed
    """
    with PostgresContainer("postgres:15") as postgres:
        yield postgres

@pytest.fixture(scope="session")
def db_engine(postgres_container):
    """Database engine with test database.
    
    Runs Alembic migrations automatically before tests.
    """
    from sqlalchemy.ext.asyncio import create_async_engine
    
    # Create async engine
    engine = create_async_engine(
        postgres_container.get_connection_url().replace("postgresql://", "postgresql+asyncpg://")
    )
    
    # Run migrations
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", postgres_container.get_connection_url())
    command.upgrade(alembic_cfg, "head")
    
    yield engine
    
    # Cleanup
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

**Afternoon (3-4 hours):**
3. Task 4.4: REFACTOR - Integration testing
4. Task 5.1-5.3: Documentation updates (CHANGELOGs, migration guide)

**Deliverables:**
- [ ] RLS tests: `services/registry/tests/test_rls_policies.py`
- [ ] Updated CHANGELOGs (soorma-common, Registry Service)
- [ ] Migration guide for breaking changes

### Day 4: Examples Update (2-3 hours) - CRITICAL FOR MAIN MERGE

**All Day:**
1. Task 5.4: Update all examples with new DTO format
   - Update `AgentCapability` to use `EventDefinition` objects (not strings)
   - Add `version` field to agent definitions
   - Verify all examples run successfully after changes

**Deliverables:**
- [ ] All 10 examples updated and tested
- [ ] `examples/README.md` updated with migration notes

**Note:** This day is CRITICAL - examples serve as documentation and must work before merge to main.

---

## 7. Breaking Changes & Migration Guide

### Breaking Changes in v0.8.1 (APPROVED: Clean Break)

**Decision:** Pre-launch phase allows clean break with no backward compatibility.

**1. AgentCapability Structure (BREAKING)**
- **Old (v0.8.0):** `consumed_event` is a `string`
- **New (v0.8.1):** `consumed_event` MUST be an `EventDefinition` object
- **No Backward Compatibility:** Strings will raise `ValidationError`
- **Action Required:** All agent registration code must be updated

**2. EventDefinition Schema References (BREAKING)**
- **Old (v0.8.0):** `payload_schema` is an embedded JSON object
- **New (v0.8.1):** `payload_schema_name` is a string reference to registered schema
- **Backward Compatibility:** Both fields supported during transition (keep deprecated fields)
- **Deprecation Timeline:** v1.0.0 will remove embedded schema fields

**3. Database Schema (BREAKING)**
- **Breaking:** `agents` and `events` tables require `tenant_id` and `user_id`
- **Migration Strategy:** Default UUIDs during migration, then drop defaults
- **Action Required:** Users must recreate agent/event registrations with valid tenant/user headers

**4. Uniqueness Scope (BREAKING)**
- **Old (v0.8.0):** `agent_id` and `event_name` globally unique across all tenants
- **New (v0.8.1):** `agent_id` and `event_name` unique within tenant only
- **Impact:** Different tenants can now use same agent_id/event_name
- **Benefit:** True multi-tenancy isolation

### Affected Components Checklist (Main Merge Readiness)

All components must be updated to maintain compatibility:

#### ✅ Core Libraries
- [ ] `libs/soorma-common/src/soorma_common/models.py` - Updated DTOs
- [ ] `libs/soorma-common/CHANGELOG.md` - Document breaking changes
- [ ] `libs/soorma-common/tests/` - All tests passing

#### ✅ Registry Service
- [ ] `services/registry/alembic/versions/003_*.py` - Migration script
- [ ] `services/registry/src/registry_service/models/schema.py` - New SQLAlchemy model
- [ ] `services/registry/CHANGELOG.md` - Document schema changes
- [ ] `services/registry/tests/` - All tests passing (unit + integration + RLS)

#### ✅ SDK (No Changes in Phase 1, but verify compatibility)
- [ ] `sdk/python/soorma/registry/client.py` - Verify works with new DTOs
- [ ] `sdk/python/tests/` - Existing tests still pass

#### ✅ Examples (CRITICAL - All must be updated)
- [ ] `examples/01-hello-world/` - Update agent registration
- [ ] `examples/02-events-simple/` - Update event definitions
- [ ] `examples/03-events-structured/` - Update capabilities
- [ ] `examples/04-memory-working/` - Update agent/event registration
- [ ] `examples/05-memory-semantic/` - Update agent/event registration
- [ ] `examples/06-tool-basic/` - Update agent registration
- [ ] `examples/07-tool-weather/` - Update agent registration
- [ ] `examples/08-worker-basic/` - Update capabilities
- [ ] `examples/09-planner-basic/` - Update planner registration
- [ ] `examples/10-planner-tracker/` - Update planner registration
- [ ] `examples/README.md` - Update documentation

#### ✅ Documentation
- [ ] `docs/discovery/README.md` - Update with new patterns
- [ ] `docs/discovery/ARCHITECTURE.md` - Document schema registry
- [ ] `docs/ARCHITECTURE_PATTERNS.md` - Update Section 4 (multi-tenancy)
- [ ] `CHANGELOG.md` (root) - Release notes for v0.8.1
- [ ] Migration guide document (new)

#### ✅ Infrastructure
- [ ] `services/registry/Dockerfile` - Verify no changes needed
- [ ] `services/registry/entrypoint.sh` - Verify migration runs
- [ ] **CI/CD** - Deferred to Docker image publishing phase (see DEFERRED_WORK.md)
  - Phase 1: Tests run locally with Docker
  - Future: Add `.github/workflows/ci-registry-service.yaml` when publishing images

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
| **Docker** | 20.10+ | **Required for testcontainers** | ⚠️ Must be running |
| PostgreSQL | 15+ | Database with RLS support | ✅ Available |
| SQLAlchemy | 2.0+ | ORM for database models | ✅ Installed |
| Alembic | 1.13+ | Database migrations | ✅ Installed |
| Pydantic | 2.0+ | DTO validation | ✅ Installed |
| pytest | 8.0+ | Testing framework | ✅ Installed |
| testcontainers | 3.7+ | PostgreSQL test container | ⚠️ Need to install |

**CRITICAL: Docker Requirement**
- testcontainers spawns PostgreSQL container during tests
- Docker daemon must be running when executing `pytest`
- Container lifecycle is automatic (pytest manages start/stop)
- Installation: `pip install testcontainers[postgres]`

**CI/CD Note:**
- GitHub Actions `ubuntu-latest` includes Docker (testcontainers works out-of-the-box)
- Registry Service CI workflow deferred until Docker image publishing phase
- See: [docs/refactoring/DEFERRED_WORK.md](../../refactoring/DEFERRED_WORK.md) (Stage 5 deferrals)
- For Phase 1: Run tests locally with Docker

### Blockers

❌ **No blockers for Phase 1**

### Prerequisites

- [x] ARCHITECTURE_PATTERNS.md reviewed (mandatory gateway)
- [x] Master Plan approved by developer
- [x] All design decisions approved (see Approved Decisions Summary above)
- [ ] PostgreSQL 15+ database available for local development
- [ ] Docker installed and running (required for testcontainers)
- [ ] `testcontainers` Python package installed: `pip install testcontainers[postgres]`

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
- [ ] Integration tests: Composite indexes verified for correct creation
- [ ] Total test count: 27-30 tests (15-20 unit, 7-9 migration, 6-9 RLS)

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

**Core Implementation:**
- [ ] All tasks marked as completed in Section 3
- [ ] All tests passing (unit + integration + RLS)
- [ ] Migration tested forward and backward (upgrade + downgrade)
- [ ] RLS policies verified (no cross-tenant leakage)
- [ ] Tenant-scoped uniqueness verified (different tenants can use same agent_id)

**Documentation:**
- [ ] CHANGELOGs updated (soorma-common, Registry Service)
- [ ] Migration guide documented for breaking changes
- [ ] Database schema documented in migration file

**Examples (CRITICAL for Main Merge):**
- [ ] All 10 examples updated with new DTO format
- [ ] All examples execute successfully
- [ ] `examples/README.md` updated

**Quality Gates:**
- [ ] Code review completed (if applicable)
- [ ] Breaking changes clearly documented
- [ ] Docker/testcontainers requirement documented
- [ ] Tests run successfully locally (Docker required)

**Note:** CI/CD workflow for Registry Service deferred to Docker image publishing phase (not a blocker for Phase 1 completion).

**Release:**
- [ ] Tag release: `v0.8.1-alpha.1` (Phase 1 complete)

**Next Phase:** [ACTION_PLAN_Phase2_Service.md](ACTION_PLAN_Phase2_Service.md) (to be created)

---

## 11. Notes & Decisions

### Design Decisions

**Decision 1: Clean Break (No Backward Compatibility) - APPROVED**
- **Rationale:** Pre-launch phase allows breaking changes for architectural correctness
- **Implementation:** `AgentCapability` requires `EventDefinition` objects (no Union types)
- **Tradeoff:** All examples must be updated immediately
- **Benefit:** Simpler code, no technical debt from deprecated patterns
- **Migration:** All agent registration code must be updated in v0.8.1
- **Developer Approved:** February 28, 2026

**Decision 2: Breaking Changes Acceptable in Pre-Launch - APPROVED**
- **Rationale:** Per refactoring principles, architectural correctness > backward compatibility
- **Impact:** Small user base (mostly internal), clean break simplifies future maintenance
- **Mitigation:** Comprehensive migration guide in documentation
- **Developer Approved:** February 28, 2026

**Decision 3: Tenant-Scoped Uniqueness - APPROVED**
- **Rationale:** True multi-tenancy requires independent namespaces per tenant
- **Implementation:** `(agent_id, tenant_id)` and `(event_name, tenant_id)` unique constraints
- **Benefit:** Different tenants can use same agent_id/event_name without conflicts
- **Tradeoff:** Cannot enforce global naming conventions
- **Developer Approved:** February 28, 2026

**Decision 4: RLS at Database Layer - APPROVED**
- **Rationale:** PostgreSQL RLS enforces tenant isolation at query level (bulletproof)
- **Tradeoff:** Minor performance overhead (~5-10%)
- **Alternative Rejected:** App-level filtering (error-prone, security gaps)
- **Developer Approved:** February 28, 2026

**Decision 5: Schema Registry as Separate Table - APPROVED**
- **Rationale:** Enables dynamic event types with discoverable schemas
- **Tradeoff:** Additional JOIN queries for schema lookups
- **Alternative Rejected:** Embedded schemas (loses core Stage 5 value)
- **Developer Approved:** February 28, 2026

**Decision 6: Composite Indexes for RLS Queries - APPROVED**
- **Rationale:** RLS policies automatically filter by `tenant_id` first, then by query criteria
- **Optimization:** Composite indexes `(tenant_id, column_name)` match query patterns exactly
- **Example:** `SELECT * FROM payload_schemas WHERE tenant_id = ? AND schema_name = ?`
- **Performance:** Avoids table scans, reduces index size (tenant subset), improves cache locality
- **Pattern Applied:** All multi-tenant tables (payload_schemas, agents, events)
- **Developer Approved:** February 28, 2026

**Decision 7: No Foreign Keys to tenants/users Tables - APPROVED**
- **Rationale:** Microservices pattern - Identity service owns tenant/user entities (separate database)
- **Design:** tenant_id/user_id are cached authentication context from validated JWT/API Keys
- **Validation:** Identity service validates tenant/user existence before issuing tokens
- **Isolation:** RLS policies enforce tenant isolation using cached IDs (no FK needed)
- **Tradeoff:** No cascading deletes, no referential integrity at database level
- **Acceptable:** Tenant lifecycle managed by Identity service, not Registry service
- **Future-proof:** No cross-database FK constraints (violates microservices independence)
- **Developer Approved:** February 28, 2026

**Decision 8: testcontainers for RLS Testing - APPROVED**
- **Rationale:** Docker-based PostgreSQL for isolated integration tests
- **Setup/Teardown:** Automatic via pytest fixtures (no manual cleanup)
- **Requirement:** Docker must be running locally during test execution
- **Container Lifecycle:** Starts on first test, stops after pytest session ends
- **Developer Approved:** February 28, 2026

### Technical Debt

**Debt Item 1: Deprecated Fields**
- **Location:** `EventDefinition` payload_schema/response_schema
- **Cleanup:** v1.0.0 - remove embedded schema fields
- **Tracking:** DEFERRED_WORK.md

**Debt Item 2: Registry Service CI Workflow**
- **Location:** `.github/workflows/` (missing)
- **Cleanup:** Add when publishing service Docker images
- **Currently:** Tests run locally with Docker/testcontainers
- **Tracking:** [DEFERRED_WORK.md](../../refactoring/DEFERRED_WORK.md) (Stage 5 deferrals)
- **Impact:** Low - testcontainers works on GitHub Actions when workflow added

### Questions & Answers

**Q1: Why not defer multi-tenancy to v0.9.0?**
- **A:** Multi-tenancy is a foundational security requirement. Retrofitting later creates migration complexity and security debt. Implementing now (with RLS) is the "right architecture."

**Q2: Why PostgreSQL-specific (RLS)?**
- **A:** RLS is the gold standard for tenant isolation. SQLite alternative would require app-level filtering (less secure, more code). Stage 5 targets production readiness.

**Q3: Can we skip schema versioning?**
- **A:** No. Schema versioning is core to A2A protocol compatibility and allows schema evolution without breaking existing agents.

**Q4: Should agent_id and event_name be globally unique or tenant-scoped? - RESOLVED**
- **A:** **APPROVED: Tenant-scoped unique**
  - **Decision:** `(agent_id, tenant_id)` and `(event_name, tenant_id)` unique constraints
  - **Breaking Change:** Migration drops global unique indexes on `agent_id` and `event_name`
  - **Rationale:** True multi-tenancy requires independent namespaces per tenant
  - **Benefit:** Different tenants can use same agent_id/event_name (e.g., all tenants can have "worker-001")
  - **Implementation:** Phase 1 migration script removes global unique constraints
  - **Developer Approved:** February 28, 2026

**Q5: Why no foreign key constraints to tenants/users tables?**
- **A:** **Microservices pattern - tenant_id/user_id are authentication context, not relational data**
  - **Identity Service** (future): Separate infrastructure service owns tenant/user data
  - **Registry Service** (current): Receives validated tenant_id/user_id from JWT/API Key headers
  - **Authentication flow:**
    1. Client authenticates with Identity Service → receives JWT
    2. JWT contains `{"tenant_id": "...", "user_id": "..."}` (already validated)
    3. Registry Service extracts tenant_id/user_id from JWT (trusted context)
    4. RLS policies enforce isolation using these cached IDs
  - **No FK constraints needed:** tenant_id/user_id validation happens upstream
  - **No cross-database FKs:** Services maintain separate databases (microservices best practice)
  - **RLS enforces isolation:** Even if invalid tenant_id exists, RLS prevents cross-tenant queries

**Q6: Will testcontainers work with GitHub Actions CI?**
- **A:** **Yes - GitHub Actions fully supports testcontainers**
  - **Environment:** `ubuntu-latest` runners include Docker daemon (pre-installed and running)
  - **No configuration needed:** testcontainers auto-detects GitHub Actions environment
  - **Container cleanup:** Ryuk container handles automatic cleanup between test runs
  - **Performance:** PostgreSQL image cached after first run
  - **Deferral:** Registry Service CI workflow deferred to Docker image publishing phase
  - **Phase 1 approach:** Run tests locally with Docker (manual validation)
  - **Future workflow:** See example in [DEFERRED_WORK.md](../../refactoring/DEFERRED_WORK.md)

---

**Plan Status:** 📋 Awaiting Developer Approval  
**Estimated Start Date:** TBD  
**Estimated Completion Date:** TBD (2-3 days after approval)  
**Author:** GitHub Copilot (Senior Architect)  
**Reviewer:** [Pending]
