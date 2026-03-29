# Services and Orchestration

## Service Definitions

### Service A: Shared Identity Validation Service
- **Implementation location**: libs/soorma-service-common
- **Responsibility**: centralize reusable identity-context validation for user-scoped routes
- **Primary API**: require_user_context dependency
- **Error policy**:
  - Immediate 400 on missing service_tenant_id or service_user_id
  - Generic response wording to avoid coupling to transport/auth mechanism

### Service B: Memory API Service
- **Implementation location**: services/memory/api/v1
- **Responsibility**: enforce route-level identity requirements and delegate to domain services
- **Orchestration behavior**:
  - User-scoped routers include require_user_context
  - Admin router excludes require_user_context
  - Downstream call chain always receives full identity tuple

### Service C: Memory Domain Services
- **Implementation location**: services/memory/services
- **Responsibility**: domain orchestration around CRUD operations
- **Orchestration behavior**:
  - Accept and propagate full identity tuple through all methods
  - Preserve behavior contract for all existing endpoints while strengthening validation and scope

### Service D: Persistence/CRUD Services
- **Implementation location**: services/memory/crud
- **Responsibility**: perform scoped reads/writes and conflict-safe upserts
- **Orchestration behavior**:
  - Full identity predicates on all user-scoped resources
  - Conflict targets and constraints aligned to identity semantics

### Service E: Schema Migration Service
- **Implementation location**: services/memory/alembic/versions
- **Responsibility**: evolve schema/index constraints to enforce new identity scope model
- **Orchestration behavior**:
  - Apply constraint/index migration before runtime logic assumes new model
  - Ensure downgrade path exists

## Service Interaction Sequence

1. API route receives request with TenantContext
2. require_user_context validates service_tenant_id + service_user_id
3. Route delegates to memory domain service with full identity tuple
4. Domain service delegates to CRUD with full identity tuple
5. CRUD executes full-identity predicates/upserts
6. DB constraints/indexes enforce final collision/isolation guarantees

## Cross-Service Reuse Strategy

- require_user_context is service-agnostic and reusable beyond memory
- No memory-specific semantics embedded in shared dependency
- Future services can adopt same dependency to converge identity enforcement behavior
