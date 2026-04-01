# Business Overview

## Business Context (Text)
The soorma-core platform provides an agent runtime where developers build multi-agent applications and connect them to shared platform services. The core business responsibility is to support secure multi-tenant agent execution with isolated state, event choreography, and service discovery.

## Business Description
- **Business Description**: Soorma-core is a platform for building agentic systems using Planner/Worker/Tool patterns, with platform APIs for registry, memory, tracker, and eventing.
- **Business Transactions**:
  - Register and discover agents/schemas per developer tenant.
  - Publish/consume events across planner-worker workflows.
  - Store and retrieve tenant/user scoped memory and execution context.
  - Track plan/task execution status and timelines.
- **Business Dictionary**:
  - **Developer Tenant (Tier 1)**: Platform tenant that owns registered agents and schemas.
  - **Client Tenant + User (Tier 2)**: Tenant/user dimensions of the developer's end-customer domain.
  - **PlatformContext**: High-level SDK wrapper layer used by agent handlers.
  - **Service Client**: Low-level HTTP client used internally by wrappers.

## Component Level Business Descriptions
### sdk/python/soorma
- **Purpose**: Exposes developer-facing APIs for agent logic and service interaction.
- **Responsibilities**: Agent execution primitives, wrappers over platform services, event choreography APIs.

### services/registry
- **Purpose**: Manages agent and schema registry in developer-tenant scope.
- **Responsibilities**: Register/query agents, capability discovery, schema operations.

### services/memory
- **Purpose**: Persists CoALA-style memory for tenant/user scoped application data.
- **Responsibilities**: Semantic/episodic/procedural/working memory and task/plan context.

### services/tracker
- **Purpose**: Exposes plan/task observability APIs.
- **Responsibilities**: Query plan progress, execution events, and action history.

### services/event-service
- **Purpose**: Publishes and streams platform events.
- **Responsibilities**: Event ingress, tenant-aware propagation, topic-based transport.

### libs/soorma-common
- **Purpose**: Shared DTO and event model contracts.
- **Responsibilities**: Pydantic models, envelope schemas, cross-component type consistency.

### libs/soorma-service-common
- **Purpose**: Shared service middleware and tenancy/RLS infrastructure.
- **Responsibilities**: Header extraction, tenant context dependencies, DB session config for RLS.

### examples
- **Purpose**: Reference workflows for planner-worker choreography and memory patterns.
- **Responsibilities**: Implementation examples and operational usage guidance.