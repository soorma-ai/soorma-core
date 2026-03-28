# Components

## Overview
This initiative introduces one shared validation component and updates existing Memory Service components to enforce consistent three-column identity scope.

## Component Catalog

### 1) Identity Context Validator
- **Location**: libs/soorma-service-common
- **Type**: Shared FastAPI dependency component
- **Purpose**: Enforce presence of both service_tenant_id and service_user_id for user-scoped operations
- **Responsibilities**:
  - Validate required identity dimensions from request context
  - Raise HTTP 400 with generic, future-proof error messages when missing
  - Remain reusable for any service (memory, tracker, registry)
  - Provide extension point for future authorization checks

### 2) Memory API Validation Boundary
- **Location**: services/memory/api/v1
- **Type**: API layer boundary component
- **Purpose**: Apply shared identity dependency to all user-scoped endpoints
- **Responsibilities**:
  - Ensure user-scoped routers enforce require_user_context
  - Preserve admin endpoints as tenant/system-scoped without user dependency
  - Keep route-level behavior explicit and consistent

### 3) Memory CRUD Scope Engine
- **Location**: services/memory/crud
- **Type**: Persistence query component
- **Purpose**: Enforce full identity scoping in predicates and upsert conflict targets
- **Responsibilities**:
  - Align list/get/update/delete predicates to full identity tuple
  - Align upsert conflict targets with actual unique constraints/indexes
  - Prevent cross-tenant and cross-user collisions

### 4) Memory Schema and Index Governance
- **Location**: services/memory/alembic/versions + models
- **Type**: Data model governance component
- **Purpose**: Keep constraints/indexes in lockstep with CRUD and API semantics
- **Responsibilities**:
  - Update unique constraints for working_memory, task_context, plan_context
  - Ensure semantic private unique indexes include service_tenant_id + service_user_id
  - Keep migration upgrade/downgrade safe and deterministic

### 5) Isolation Test Harness
- **Location**: services/memory/tests and libs/soorma-service-common/tests
- **Type**: Verification component
- **Purpose**: Prove enforced identity requirements and data isolation behavior
- **Responsibilities**:
  - Validate 400 behavior for missing service_tenant_id/service_user_id
  - Validate cross-user and cross-service-tenant isolation
  - Validate migration and uniqueness behavior
