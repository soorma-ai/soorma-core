# Component Methods

## 1) Identity Context Validator (shared)

### Method: require_user_context
- **Layer**: Shared dependency (soorma-service-common)
- **Inputs**:
  - TenantContext with platform_tenant_id, service_tenant_id, service_user_id, db
- **Output**:
  - TenantContext (pass-through) when valid
- **Behavior**:
  - Validate service_tenant_id is present and non-empty
  - Validate service_user_id is present and non-empty
  - Raise HTTPException(400) with generic message on failure
- **Notes**:
  - Chosen as single dependency shape (Q1=A)
  - Immediate enforcement (Q4=A)

## 2) Memory API Validation Boundary

### Method Pattern: user-scoped route dependency application
- **Layer**: Memory API routers
- **Inputs**:
  - Route request context via Depends chain
- **Output**:
  - Route execution only when require_user_context passes
- **Behavior**:
  - Attach dependency at router module level for all user-scoped routers (Q2=A)
  - Do not attach on admin router

## 3) Memory CRUD Scope Engine

### Method Pattern: full identity predicates
- **Layer**: CRUD methods
- **Required identity inputs**:
  - platform_tenant_id
  - service_tenant_id
  - service_user_id
- **Query behavior**:
  - list/get/update/delete use full identity tuple
  - upsert conflict targets include full tuple where resource is user-scoped

### Method Group: plans CRUD
- list_plans(platform_tenant_id, service_tenant_id, service_user_id, ...)
- get_plan(platform_tenant_id, service_tenant_id, service_user_id, plan_id)
- update_plan(platform_tenant_id, service_tenant_id, service_user_id, plan_id, ...)
- delete_plan(platform_tenant_id, service_tenant_id, service_user_id, plan_id)

### Method Group: sessions CRUD
- list_sessions(platform_tenant_id, service_tenant_id, service_user_id, ...)
- get_session(platform_tenant_id, service_tenant_id, service_user_id, session_id)
- update_session_interaction(platform_tenant_id, service_tenant_id, service_user_id, session_id)
- delete_session(platform_tenant_id, service_tenant_id, service_user_id, session_id)

### Method Group: task_context CRUD
- upsert_task_context(..., platform_tenant_id, service_tenant_id, service_user_id, task_id, ...)
- get_task_context(platform_tenant_id, service_tenant_id, service_user_id, task_id)
- update_task_context(platform_tenant_id, service_tenant_id, service_user_id, task_id, ...)
- delete_task_context(platform_tenant_id, service_tenant_id, service_user_id, task_id)

### Method Group: plan_context CRUD
- upsert_plan_context(..., platform_tenant_id, service_tenant_id, service_user_id, plan_id, ...)
- get_plan_context(platform_tenant_id, service_tenant_id, service_user_id, plan_id)
- update_plan_context(platform_tenant_id, service_tenant_id, service_user_id, plan_id, ...)
- delete_plan_context(platform_tenant_id, service_tenant_id, service_user_id, plan_id)

### Method Group: semantic upsert/query
- upsert_semantic_memory(..., platform_tenant_id, service_tenant_id, service_user_id, ...)
- query/search use full identity for private scope filtering
- Public uniqueness decision (Q3=B): include service_tenant_id for public semantic uniqueness

## 4) Schema and Index Governance

### Migration methods
- upgrade(): add/drop/alter constraints/indexes to match identity scope model
- downgrade(): restore prior constraints/indexes safely

### Constraint/index targets
- working_memory unique: (platform_tenant_id, service_tenant_id, service_user_id, plan_id, key)
- task_context unique: (platform_tenant_id, service_tenant_id, service_user_id, task_id)
- plan_context unique: (platform_tenant_id, service_tenant_id, service_user_id, plan_id)
- semantic private unique indexes: include service_tenant_id + service_user_id
- semantic public unique indexes: include platform_tenant_id + service_tenant_id per Q3=B
