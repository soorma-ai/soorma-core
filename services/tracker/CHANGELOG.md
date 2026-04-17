# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.9.0] - 2026-04-17

### Changed — Three-Dimensional Tenancy (multi-tenancy initiative)
- **Version alignment**: bumped to 0.9.0 (tracker service synchronized with monorepo release)
- **Identity model**: replaced `tenant_id`/`user_id` columns with `platform_tenant_id`, `service_tenant_id`, `service_user_id` (all VARCHAR(64) NOT NULL) in `plan_progress` and `action_progress`
- **Scoped uniqueness**: `plan_progress` unique on `(platform_tenant_id, service_tenant_id, plan_id)`; `action_progress` unique on `(platform_tenant_id, service_tenant_id, action_id)`
- **Composite FK**: `action_progress` references `plan_progress` via `(platform_tenant_id, service_tenant_id, plan_id)`
- **HTTP path**: registered `TenancyMiddleware` from `soorma-service-common`; query endpoints use `TenantContext` dependency injection
- **NATS path**: `_extract_identity_dimensions()` maps `event.platform_tenant_id/tenant_id/user_id` to three-dim fields; fail-closed if `platform_tenant_id` missing; `set_config_for_session()` activates RLS per event
- **Validation**: identity dimensions enforced to ≤64 chars at API layer; all three required
- **Dependencies**: added `soorma-service-common`

### Added — Three-Dimensional Tenancy (multi-tenancy initiative)
- GDPR deletion service `TrackerDataDeletion` covering `ActionProgress` + `PlanProgress`
- Internal admin endpoints: `DELETE /v1/admin/platform/{ptid}`, `/tenant/{ptid}/{stid}`, `/user/{ptid}/{stid}/{suid}`
- Alembic migration `20260323_0712_f7a1c2b9d1e0` for identity column rename/addition

## [0.8.2] - 2026-03-14

### Changed
- Version alignment: bumped to 0.8.2 (all components synchronized)



### Changed
- **TECH-DEBT-001:** Replace `soorma-core` (SDK) dependency with `soorma-nats` (infrastructure library)
- Tracker Service now subscribes to NATS directly instead of via Event Service HTTP/SSE
- `start_event_subscribers` now accepts `nats_url: str` (was `event_service_url: str`)
- Add `NATS_URL` environment variable (default: `nats://localhost:4222`)

### Removed
- `EVENT_SERVICE_URL` environment variable removed from Tracker Service configuration
- `soorma-core` removed from runtime dependencies

## [0.8.0] - 2026-02-23

### Added
- **Initial Release - Event-Driven Observability Service** (Stage 4 Phase 3)
  - **Event Subscription**
    - Subscribes to `action-requests`, `action-results`, `system-events` topics
    - Automatic event processing via NATS JetStream
    - Event envelope parsing with tenant/user context extraction
  - **Progress Tracking**
    - `plan_progress` table: Plan execution state (running, completed, failed)
    - `action_progress` table: Task state transitions with timing
    - Hierarchical plan tracking via parent_plan_id
    - Session grouping for conversation workflows
    - Delegation group tracking for parallel task fan-out/fan-in
  - **Query APIs**
    - `GET /v1/tracker/plans/{plan_id}/progress`: Plan execution summary
    - `GET /v1/tracker/plans/{plan_id}/tasks`: Task history with state transitions
    - `GET /v1/tracker/plans/{plan_id}/timeline`: Event execution timeline
    - `GET /v1/tracker/agents/{agent_name}/metrics`: Agent performance metrics
    - `GET /v1/tracker/plans/{plan_id}/sub-plans`: Child plan hierarchy
    - `GET /v1/tracker/sessions/{session_id}/plans`: All plans in a session
    - `GET /v1/tracker/delegation-groups/{group_id}`: Parallel task status
  - **Multi-Tenancy**
    - PostgreSQL Row-Level Security (RLS) for tenant isolation
    - Required headers: `X-Tenant-ID`, `X-User-ID` on all requests
    - Database-level enforcement prevents cross-tenant data leaks
    - RLS policies automatically filter query results
  - **Docker Deployment**
    - Dockerfile with multi-stage build (dependencies + app layers)
    - Health check endpoint: `GET /health` (database + event service checks)
    - Environment variables: `DATABASE_URL`, `NATS_URL`, `EVENT_SERVICE_URL`
    - Alembic migrations for schema versioning
  - **Database Schema**
    - `plan_progress` table with indexes on plan_id, tenant_id, session_id
    - `action_progress` table with indexes on action_id, plan_id, agent_name
    - Foreign key relationships with CASCADE delete
    - Created/updated timestamps for audit trail
  - **Integration with SDK**
    - TrackerClient wrapper in PlatformContext (`context.tracker.*`)
    - Agent-friendly API with automatic tenant/user context
    - Example usage in 10-choreography-basic
  - **Test Coverage**
    - 28 passing tests (service integration + API endpoints)
    - Test coverage for multi-tenancy, RLS policies, error handling
    - Validation of event subscription and progress tracking

### Technical Details
- **Language**: Python 3.11+
- **Framework**: FastAPI with async/await
- **Database**: PostgreSQL with asyncpg driver
- **Message Bus**: NATS JetStream via Event Service
- **Dependencies**: soorma-common (DTOs), soorma-core (event client)
- **RLS Implementation**: PostgreSQL session variables (`app.tenant_id`, `app.user_id`)

### Documentation
- README.md with deployment guide, API examples, multi-tenancy explanation
- curl examples for all endpoints with response samples
- Docker Compose and Kubernetes health check configurations
- Integration pattern examples using TrackerClient wrapper

### Known Limitations
- No UI dashboard (curl/API only) - deferred to post-v0.8.0
- No real-time WebSocket streaming - events are poll-based
- No automated alerting/notifications - external systems must poll
- No historical data retention policy - grows unbounded
