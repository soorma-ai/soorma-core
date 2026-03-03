# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.8.1] - 2026-03-02

### Added
- **Phase 2 - Schema Registry Service Endpoints**
  - `POST /v1/schemas` — Register a new payload schema (returns 409 on duplicate name+version per tenant)
  - `GET /v1/schemas/{name}` — Retrieve latest version of a schema by name (returns 404 if not found)
  - `GET /v1/schemas/{name}/versions/{version}` — Retrieve a specific (name, version) schema
  - `GET /v1/schemas` — List schemas for the tenant (optional `?owner_agent_id=` filter)
  - `GET /v1/agents/discover` — Discover active agents by consumed event (optional `?consumed_event=` filter)
- **`SchemaCRUD`** (`crud/schemas.py`) — SQLAlchemy async CRUD layer for `payload_schemas` table
- **`SchemaRegistryService`** (`services/schema_service.py`) — Business logic: duplicate detection, DTO mapping
- **`AgentRegistryService.discover_agents()`** — Capability-based agent discovery; delegates to `query_agents()` with TTL filtering and deduplication
- **SDK `RegistryClient`** — 4 new methods: `register_schema`, `get_schema`, `list_schemas`, `discover_agents`
- **Test coverage** — 30 new tests (20 schema endpoints + 10 discovery); 80 total passing

### Fixed
- **SQLite `created_at` ordering precision bug** in `SchemaCRUD.create_schema`
  - `server_default=func.now()` has second-level precision in SQLite; rapid sequential inserts within the same second share identical timestamps, making `ORDER BY created_at DESC LIMIT 1` non-deterministic
  - Fix: set `created_at=datetime.now(timezone.utc)` explicitly on the Python side (microsecond precision)

### Fixed (March 1, 2026)
- **SQLite UUID NUMERIC affinity bug** (discovered during test harness work)
  - `postgresql.UUID()` in `models/agent.py` and `models/event.py` caused SQLite to assign NUMERIC affinity to tenant_id columns
  - All-zeros UUID (`00000000-0000-0000-0000-000000000000`) was coerced to integer `0` on storage, making every tenant-scoped query return zero rows
  - Fix: replaced `postgresql.UUID()` with `Uuid(as_uuid=True, native_uuid=True)` — SQLite uses CHAR(32)/TEXT affinity, PostgreSQL uses native UUID (no DDL change in production)
- **`set(EventDefinition)` unhashable type error** in `agent_service.py`
  - `register_agent()` derived `consumed_events`/`produced_events` via `list(set(cap.consumed_event ...))` — fails because `EventDefinition` objects are not hashable
  - Fix: extract `.event_name` strings before deduplication
- **`agent_to_dto()` string-to-EventDefinition coercion** in `crud/agents.py`
  - `AgentCapabilityTable.consumed_event` stores event name strings; `AgentCapability` v0.8.1 requires `EventDefinition` objects
  - Fix: wrap DB varchar strings as `EventDefinition` objects when building `AgentCapability` in `agent_to_dto()`
- **Registry test suite**: all 50 tests now pass (was 35 failing + 7 errors pre-fix)
  - Added `TEST_TENANT_ID` sentinel (`00000000-0000-0000-0000-000000000000`) to `conftest.py`
  - Updated all test fixtures to use `EventDefinition` objects (v0.8.1 breaking change)
  - Added `developer_tenant_id` as required 3rd arg to all `register_agent()` and CRUD call sites

### Added (February 28, 2026)
- **Phase 1 - Schema Registry Foundation (February 28, 2026)**
  - **Database migration 003_schema_registry** (RF-ARCH-005, RF-ARCH-006)
    - New `payload_schemas` table for dynamic schema registration
      - Fields: id (UUID), schema_name, version, json_schema (JSONB), description, owner_agent_id
      - Semantic versioning support (e.g., "1.0.0")
      - Unique constraint: (schema_name, version, tenant_id)
    - Multi-tenancy columns added to existing tables:
      - `agents` table: tenant_id, user_id, version columns
      - `events` table: tenant_id, user_id, owner_agent_id, payload_schema_name, response_schema_name columns
    - **Row-Level Security (RLS) policies** for tenant isolation
      - Tenant read policy: Users can only query their tenant's data
      - User write policy: Users can only modify their own data
      - PostgreSQL session variables: `app.tenant_id`, `app.user_id`
    - **Optimized composite indexes** for RLS query patterns
      - `idx_payload_schemas_tenant_schema` on (tenant_id, schema_name)
      - `idx_agents_tenant_agent` on (tenant_id, agent_id)
      - `idx_events_tenant_event` on (tenant_id, event_name)
      - Matches RLS filter order for optimal query performance
  - **SQLAlchemy model**: `PayloadSchemaTable` in `models/schema.py`
    - UUID primary key with server-side generation
    - JSONB column for json_schema (PostgreSQL native type)
    - Timestamps: created_at, updated_at
    - No foreign key constraints (microservices pattern)

### Changed
- **BREAKING: Unique constraints now tenant-scoped** (v0.8.1)
  - `agents.agent_id`: globally unique → unique within tenant (agent_id, tenant_id)
  - `events.event_name`: globally unique → unique within tenant (event_name, tenant_id)
  - Impact: Different tenants can now use same agent_id/event_name
  - Benefit: True multi-tenancy isolation with independent namespaces
  - Migration: Uses default UUIDs during migration, then drops defaults
- **BREAKING: All tables require tenant_id and user_id** (v0.8.1)
  - Authentication context from JWT/API Key headers (validated by Identity service upstream)
  - No foreign key constraints to tenants/users tables (microservices independence)
  - RLS policies enforce isolation at database layer
  
### Migration Notes
- **Upgrade**: `alembic upgrade head` (applies migration 003)
- **Downgrade**: `alembic downgrade -1` (full rollback support)
- **Manual testing**: Standard approach (aligns with Memory/Event/Tracker services)
- **Breaking changes**: All agent/event registrations require valid tenant_id/user_id headers after migration

## [0.8.0] - 2026-02-23

### Changed
- Bumped version to 0.8.0 to align with unified platform release (Stage 4 - Planner & ChoreographyPlanner complete)
- Single source of truth for version: imports `__version__` from soorma-common
- No functional changes to registry service

### Changed
- Bumped version to 0.7.7 to align with unified platform release

## [0.7.6] - 2026-02-07

### Changed
- Bumped version to 0.7.6 to align with unified platform release

## [0.7.5] - 2026-01-22

### Changed
- **Stage 2.1 Refactoring**: Completed comprehensive codebase refactoring
  - Unified error handling with custom exception hierarchy
  - Standardized logging across all modules
  - Improved code organization and module structure
  - Enhanced documentation and code clarity
- Bumped version to 0.7.5 to align with unified platform release

## [0.7.0] - 2026-01-21

### Changed
- Bumped version to 0.7.0 to align with unified platform release

## [0.5.1] - 2025-12-24

### Changed
- Bumped version to 0.5.1 to align with unified platform release

## [0.5.0] - 2025-12-23

### Changed
- **Database**: Now uses PostgreSQL instead of SQLite in Docker Compose dev environment
  - Provides data persistence across container restarts
  - Production-parity configuration
  - Separate `registry` database with pgvector support
- Bumped version to 0.5.0 to align with unified platform release

## [0.4.0] - 2025-12-21

### Changed
- Bumped version to 0.4.0 to align with unified platform release.

## [0.3.0] - 2025-12-20

### Changed
- **API Update**: Updated `POST /api/v1/agents` to accept full `AgentRegistrationRequest` structure, enabling rich capability schemas and descriptions.
- **Data Model**: Removed `AgentRegistrationFlat` to prevent data loss during registration.

## [0.2.0] - 2025-12-20

### Changed
- Updated `query_agents` to deduplicate results by agent name, showing only the most recently active instance for each agent type. This improves scalability and readability of the registry listing.

