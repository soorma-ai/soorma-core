# Component Dependency Model

## Dependency Matrix

| From Component | Depends On | Dependency Type | Why |
|---|---|---|---|
| Memory API Validation Boundary | Identity Context Validator | Runtime validation | Enforce required service identity before route logic |
| Memory Domain Services | Memory API Validation Boundary | Input contract | Assume validated identity context is present |
| Memory CRUD Scope Engine | Memory Domain Services | Call orchestration | Receive full identity tuple from service layer |
| Memory CRUD Scope Engine | Schema and Index Governance | Data contract | Query/upsert semantics must match DB uniqueness/index definitions |
| Isolation Test Harness | All above components | Verification | Prove behavior and isolation correctness end to end |

## Communication Patterns

### Pattern 1: Dependency-injected validation
- API routes use shared dependency to enforce identity context
- Validation failure short-circuits with HTTP 400
- Success passes through original context object

### Pattern 2: Identity tuple propagation
- The tuple (platform_tenant_id, service_tenant_id, service_user_id) is treated as inseparable for user-scoped operations
- Each service and CRUD boundary preserves the full tuple

### Pattern 3: Constraint-aligned writes
- Upsert conflict targets reference concrete constraints/indexes
- Migrations update constraints/indexes first, then runtime logic consumes them

## Data Flow

1. HTTP request enters memory endpoint
2. TenantContext resolved via tenancy middleware/dependencies
3. require_user_context validates service_tenant_id + service_user_id
4. Endpoint forwards tuple to service method
5. Service forwards tuple to CRUD method
6. CRUD executes scoped SQL predicates/upsert targets
7. DB RLS enforces platform_tenant isolation
8. DB uniqueness/indexes enforce service-tenant/user scoping and collision prevention

## Boundary Rules

- Platform-level isolation: DB RLS
- Service tenant and user isolation: API + service + CRUD predicates and constraints
- Admin endpoints: explicit exception, no user-context dependency

## Failure Mode Dependencies

- If require_user_context missing on a user-scoped endpoint: potential ambiguous writes/reads
- If CRUD predicates omit one identity column: cross-scope visibility risk
- If constraints/indexes omit identity columns: upsert collision risk
- If conflict targets mismatch indexes: runtime SQL errors and nondeterministic behavior
