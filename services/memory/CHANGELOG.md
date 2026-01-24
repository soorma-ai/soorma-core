# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
