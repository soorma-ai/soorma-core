# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.7.5] - 2026-01-30

### Added
- **Stage 2.1 Phase 1 & 2 - Semantic Memory Enhancements (January 27-30, 2026)** [RF-ARCH-012, RF-ARCH-014]
  - **Semantic Memory Upsert Support** [RF-ARCH-012]:
    - Added `external_id` VARCHAR(255) column for application-controlled versioning
    - Added `content_hash` VARCHAR(64) column for automatic deduplication
    - Implemented `upsert_semantic_memory()` CRUD function with PostgreSQL INSERT...ON CONFLICT...DO UPDATE
    - Dual-constraint logic: external_id takes precedence over content_hash when both provided
    - Conditional unique indexes prevent duplicates for both upsert paths
    - Auto-generates SHA-256 content_hash when external_id not provided
    - Alembic migration 002: Adds external_id, content_hash columns with conditional unique indexes
  - **Semantic Memory Privacy Model** [RF-ARCH-014]:
    - Added `user_id` VARCHAR(255) NOT NULL column for user-scoped isolation
    - Added `is_public` BOOLEAN DEFAULT FALSE flag for tenant-wide sharing
    - Updated RLS policies for private-by-default with optional public visibility
    - Private knowledge: unique per (tenant_id, user_id, external_id/content_hash)
    - Public knowledge: unique per (tenant_id, external_id/content_hash)
    - Updated `search_semantic_memory()` to return union of user's private + public knowledge
    - User_id extracted from auth context (query param), preventing impersonation attacks
    - Alembic migration 002: Adds user_id and is_public columns with updated RLS policies
  - **API Updates**:
    - All semantic endpoints now require `user_id` query parameter for multi-user isolation
    - `/POST /v1/semantic`: Accept external_id, user_id, is_public parameters
    - `/GET /v1/semantic/search`: Filter by user_id, optionally include public knowledge
  - **Test Coverage**: 96 tests passing
    - 13 model validation tests for upsert/privacy schema
    - 6 search tests for privacy filtering and public knowledge
    - 3 critical RLS tests validating user isolation at database level
    - 77 integration tests for all endpoints
    - 8 PostgreSQL-dependent tests (skipped in SQLite environment)

### Removed
- **Plan/Session Context Removal from Semantic Memory** [Architectural Fix]:
  - Removed `plan_id` from SemanticMemoryCreate DTO
  - Removed `session_id` from SemanticMemoryCreate DTO
  - Rationale: Semantic memory is timeless knowledge (CoALA agent memory), not contextual to plans/sessions
  - Note: plan_id belongs to working memory, session_id belongs to episodic memory


## [0.7.3] - 2026-01-26
    - All keys deletion (success/empty)
    - Tenant isolation enforcement
    - User isolation enforcement (prevents user B from deleting user A's state)
    - Plan isolation enforcement
    - Idempotent deletions
    - Multiple plans isolation
    - Invalid plan ID handling
    - Exact count verification
  - All 108 Memory Service tests passing

## [0.7.0] - 2026-01-21

### Added
- **Stage 2 - Memory Service Foundation (January 21, 2026)**
  - **Task Context Storage** for async Worker completion:
    - Database table: `task_context` with tenant isolation via RLS
    - POST `/v1/memory/task-context`: Store task state
    - GET `/v1/memory/task-context/{id}`: Retrieve task state
    - PUT `/v1/memory/task-context/{id}`: Update task state/subtasks
    - DELETE `/v1/memory/task-context/{id}`: Cleanup completed tasks
    - GET `/v1/memory/task-context/by-subtask/{id}`: Find parent by subtask
  - **Plan Context Storage** for Planner state machines:
    - Database table: `plan_context` with state machine support
    - POST `/v1/memory/plan-context`: Store plan state
    - GET `/v1/memory/plan-context/{id}`: Retrieve plan state
    - PUT `/v1/memory/plan-context/{id}`: Update plan state
    - DELETE `/v1/memory/plan-context/{id}`: Cleanup completed plans
    - GET `/v1/memory/plan-context/by-correlation/{id}`: Find by correlation ID
  - **Plans & Sessions Management**:
    - Database tables: `plans`, `sessions`
    - POST `/v1/memory/plans`: Create plan record
    - GET `/v1/memory/plans`: List plans with status/session filters
    - GET `/v1/memory/plans/{id}`: Get plan details
    - PUT `/v1/memory/plans/{id}`: Update plan status
    - DELETE `/v1/memory/plans/{id}`: Delete plan
    - POST `/v1/memory/sessions`: Create conversation session
    - GET `/v1/memory/sessions`: List active sessions
    - GET `/v1/memory/sessions/{id}`: Get session details
    - DELETE `/v1/memory/sessions/{id}`: Delete session
  - **Service Layer Architecture**:
    - Refactored all 8 endpoint files to API → Service → CRUD pattern
    - Created 8 service classes with transaction boundaries
    - TenantContext dependency injection eliminates auth boilerplate
    - PostgreSQL RLS enforced via set_session_context
  - **Tests**: 37 Memory Service tests passing (29 unit + 8 validation)

### Fixed
- Authentication handling: user_id now extracted from query params or X-User-ID header
- Validation tests now properly test 422 errors for missing/invalid parameters
- Session.metadata renamed to session_metadata (SQLAlchemy reserved field conflict)

## [0.5.1] - 2025-12-24

### Added
- **Stage 2 - Memory Service Foundation (January 21, 2026)**
  - **Task Context Storage** for async Worker completion:
    - Database table: `task_context` with tenant isolation via RLS
    - POST `/v1/memory/task-context`: Store task state
    - GET `/v1/memory/task-context/{id}`: Retrieve task state
    - PUT `/v1/memory/task-context/{id}`: Update task state/subtasks
    - DELETE `/v1/memory/task-context/{id}`: Cleanup completed tasks
    - GET `/v1/memory/task-context/by-subtask/{id}`: Find parent by subtask
  - **Plan Context Storage** for Planner state machines:
    - Database table: `plan_context` with state machine support
    - POST `/v1/memory/plan-context`: Store plan state
    - GET `/v1/memory/plan-context/{id}`: Retrieve plan state
    - PUT `/v1/memory/plan-context/{id}`: Update plan state
    - DELETE `/v1/memory/plan-context/{id}`: Cleanup completed plans
    - GET `/v1/memory/plan-context/by-correlation/{id}`: Find by correlation ID
  - **Plans & Sessions Management**:
    - Database tables: `plans`, `sessions`
    - POST `/v1/memory/plans`: Create plan record
    - GET `/v1/memory/plans`: List plans with status/session filters
    - GET `/v1/memory/plans/{id}`: Get plan details
    - PUT `/v1/memory/plans/{id}`: Update plan status
    - DELETE `/v1/memory/plans/{id}`: Delete plan
    - POST `/v1/memory/sessions`: Create conversation session
    - GET `/v1/memory/sessions`: List active sessions
    - GET `/v1/memory/sessions/{id}`: Get session details
    - DELETE `/v1/memory/sessions/{id}`: Delete session
  - **Service Layer Architecture**:
    - Refactored all 8 endpoint files to API → Service → CRUD pattern
    - Created 8 service classes with transaction boundaries
    - TenantContext dependency injection eliminates auth boilerplate
    - PostgreSQL RLS enforced via set_session_context
  - **Tests**: 37 Memory Service tests passing (29 unit + 8 validation)

### Fixed
- Authentication handling: user_id now extracted from query params or X-User-ID header
- Validation tests now properly test 422 errors for missing/invalid parameters
- Session.metadata renamed to session_metadata (SQLAlchemy reserved field conflict)

## [0.5.1] - 2025-12-24

### Changed
- Bumped version to 0.5.1 to align with unified platform release

## [0.5.0] - 2025-12-23

### Added
- Initial release of Memory Service for Soorma platform
- CoALA (Cognitive Architectures for Language Agents) framework implementation
- Four memory types: Working, Episodic, Semantic, and Procedural
- PostgreSQL with pgvector for semantic search capabilities
- Row Level Security (RLS) for native multi-tenancy isolation
- Tenant and user replica tables for data integrity
- Automatic embedding generation via OpenAI API
- REST API endpoints for all memory operations
- Local development mode with default tenant
- Production-ready multi-tenant authentication middleware
- HNSW indexes for high-performance vector search
- Comprehensive API documentation
- Docker Compose integration via soorma dev CLI
