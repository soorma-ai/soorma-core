# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
## [Unreleased]

### Added
- `TenantAdminCredentialRotateResponse` DTO for identity-service tenant-admin key rotation responses.

### Changed
- Identity onboarding/admin DTO contracts now support tenant-admin bootstrap and rotation flows used by the stricter persisted credential model.

## [0.9.0] - 2026-04-17

### Changed
- Version alignment: bumped to 0.9.0 (shared DTO/runtime package synchronized with monorepo release)

## [0.8.2] - 2026-03-14

### Changed
- Version alignment: bumped to 0.8.2 (all components synchronized)

### Documentation
- README: Fixed `AgentCapability` code example — `consumed_event` and `produced_events` now shown using `EventDefinition` objects (v0.8.1+ breaking change); string-based example removed
- README: Added **Schema Registry** models section (`PayloadSchema`, `PayloadSchemaRegistration`, `PayloadSchemaResponse`, `PayloadSchemaRegistrationRequest`, `PayloadSchemaListResponse`)
- README: Added `DiscoveredAgent` to Agent Registry models section
- README: Added **A2A** models section (`A2AAgentCard`, `A2ATask`, `A2AMessage`, `A2APart`, `A2ATaskResponse`, `A2ATaskStatus`, `A2AAuthType`, `A2AAuthentication`, `A2ASkill`)



### Fixed
- **`PayloadSchemaRegistrationRequest.schema` field renamed to `payload_schema`** (March 2, 2026)
  - Pydantic v2 `BaseModel` has a `schema()` class method; a field named `schema` shadows it and raises `UserWarning`
  - Fix: field renamed to `payload_schema` with `alias="schema"` — JSON serialization unchanged (`model_dump(by_alias=True)` still produces `{"schema": ...}`)
  - Updated call sites: `registry_service/api/v1/schemas.py`, `sdk/python/soorma/registry/client.py`

### Added
- **Phase 1 - Schema Registry & DTOs Foundation (February 28, 2026)**
  - **Schema Registry models** for dynamic event type discovery (RF-ARCH-005)
    - `PayloadSchema` model with semantic versioning support
    - `PayloadSchemaRegistration` request model for schema submission
    - `PayloadSchemaResponse` response model with success/error details
    - Schema versioning pattern: "1.0.0" (semantic versioning for agent-to-agent compatibility)
  - **Enhanced EventDefinition** with schema references (RF-ARCH-006)
    - `payload_schema_name` field for referencing registered schemas by name
    - `response_schema_name` field for response schema references
    - Deprecated fields: `payload_schema`, `response_schema` (embedded schemas, will be removed in v1.0.0)
    - Enables dynamic event type discovery without code changes
  - **Enhanced AgentCapability** with structured event definitions
    - `consumed_event` now accepts `EventDefinition` object (backward compatible with strings during transition)
    - `produced_events` now accepts `List[EventDefinition]` (backward compatible with string lists)
    - Enables rich event metadata for discovery and validation
  - **DiscoveredAgent** model for agent discovery results
    - Full capability metadata with structured event definitions
    - `get_consumed_schemas()` helper method to extract payload schema names
    - `get_produced_schemas()` helper method to extract response schema names
    - Supports A2A discovery protocol patterns
  - **22 validation tests** covering all new DTOs and helper methods
  - All tests passing (93/93 tests across entire soorma-common library)

### Changed
- **BREAKING: AgentCapability structure** (v0.8.1 clean break for pre-launch)
  - `consumed_event` field now requires `EventDefinition` object (strings no longer accepted)
  - `produced_events` field now requires `List[EventDefinition]` (string lists no longer accepted)
  - Migration required: All agent registration code must be updated
  - Rationale: Pre-launch phase allows clean architectural break for long-term maintainability
  - Impact: All 10 examples require updates (Day 4 of Phase 1 implementation)

### Migration Guide
- **Agent Registration Updates Required:**
  ```python
  # OLD (v0.8.0)
  AgentCapability(
      consumed_event="research.requested",
      produced_events=["research.completed"]
  )
  
  # NEW (v0.8.1+)
  AgentCapability(
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
  ```

## [0.8.0] - 2026-02-23

### Added
- **Stage 4 Phase 3 - Tracker Response DTOs (RF-ARCH-011 extension)** (February 22, 2026)
  - **Tracker Service response models** for plan/task observability
    - `PlanProgress` model for plan execution summary
    - `TaskExecution` model for task execution records
    - `EventTimelineEntry` and `EventTimeline` for event tracing
    - `AgentMetrics` model for agent performance metrics
    - `PlanExecution` model for plan hierarchy tracking (parent_plan_id, session_id)
    - `DelegationGroup` model for parallel task fan-out/fan-in tracking
  - **11 validation tests** covering all response models
  - Separate from `tracking.py` (events) - these are read-only query responses

- **Stage 4 Phase 2 - Type-Safe Decisions (RF-SDK-015)** (February 21, 2026)
  - **PlannerDecision types** for LLM-based autonomous planning
    - `PlanAction` enum: PUBLISH, COMPLETE, WAIT, DELEGATE
    - `PublishAction` model for event publication decisions
    - `CompleteAction` model for plan completion
    - `WaitAction` model for human-in-the-loop workflows
    - `DelegateAction` model for hierarchical planning
    - `PlannerDecision` union type with discriminated actions
  - **JSON schema generation** for LLM structured outputs
    - `PlannerDecision.model_json_schema()` for prompt templates
    - Prevents LLM hallucinations via event validation
  - **Confidence scoring** (0.0-1.0) for decision quality tracking

## [0.7.7] - 2026-02-19

### Changed
- Version bump to align with unified platform release 0.7.7

## [0.7.6] - 2026-02-07

### Changed
- Version bump to align with unified platform release 0.7.6

## [0.7.5] - 2026-01-30

### Added
- **Stage 2.1 Phase 1 & 2 - Semantic Memory Enhancements (January 27-30, 2026)**
  - **Semantic Memory Upsert Support** (RF-SDK-019):
    - Added `external_id` parameter to `SemanticMemoryCreate` for versioned knowledge updates
    - Supports dual upsert strategy: by external_id (application-controlled) OR content_hash (auto-deduplication)
    - Backward compatible (external_id optional, defaults to null)
  - **Semantic Memory Privacy Model** (RF-SDK-021):
    - **User-scoped privacy by default**: Semantic memory is now private to individual users
    - Added `user_id` (required) parameter for multi-user isolation
    - Added `is_public` (optional, default False) flag for explicit tenant-wide sharing
    - Rationale: Semantic memory is agent memory (CoALA framework), not a general RAG solution
    - Private knowledge unique per (tenant_id, user_id, external_id/content_hash)
    - Public knowledge unique per (tenant_id, external_id/content_hash)
  - **RLS Enforcement**: Database-level Row Level Security prevents unauthorized access
  - **Breaking Change**: Existing semantic memory calls now require user_id parameter

### Fixed
- **Registry Service**: Fixed test_agent_deduplication_by_name to expect versioned agent names (":1.0.0")
  - Agent names now include version suffix per AgentDefinition design
  - Test updated to expect "planner-agent:1.0.0" instead of "planner-agent"


## [0.7.3] - 2026-01-26

### Changed
- Version bump to align with SDK 0.7.3 release
- No functional changes to soorma-common library

## [0.7.0] - 2026-01-21

### Changed
- Version bump to align with SDK 0.7.3 release
- No functional changes to soorma-common library

## [0.7.0] - 2026-01-21

### Added
- **Stage 2 - Memory & Common DTOs Foundation (January 21, 2026)**
  - **Task/Plan Context DTOs** for async worker and planner persistence:
    - `TaskContextCreate`, `TaskContextUpdate`, `TaskContextResponse`: Async task state
    - `PlanContextCreate`, `PlanContextUpdate`, `PlanContextResponse`: Planner state machine
    - `PlanCreate`, `PlanUpdate`, `PlanSummary`: Plan lifecycle management
    - `SessionCreate`, `SessionSummary`: Conversation session grouping
  - **State Machine DTOs** (`state.py`):
    - `StateAction`: Action to execute on state entry
    - `StateTransition`: Transition between states with conditions
    - `StateConfig`: Complete state definition in state machine
    - `PlanDefinition`, `PlanRegistrationRequest`, `PlanInstanceRequest`: Plan type registration
  - **A2A Protocol DTOs** (`a2a.py`):
    - `A2AAuthType`, `A2AAuthentication`: Authentication types and config
    - `A2ASkill`, `A2AAgentCard`: Agent capability discovery (A2A standard)
    - `A2APart`, `A2AMessage`, `A2ATask`: Task structure
    - `A2ATaskStatus`, `A2ATaskResponse`: Task lifecycle
  - **Progress Tracking DTOs** (`tracking.py`):
    - `TaskState`: Standard task states enum (pending, running, delegated, completed, etc.)
    - `TaskProgressEvent`: Progress update event payload
    - `TaskStateChanged`: State transition event payload
  - **Tests**: 44 soorma-common tests passing, comprehensive DTO validation

### Changed
- Total exports increased to 61 (from ~40), supporting Stage 2 foundation

## [0.5.1] - 2025-12-24

### Changed
- Bumped version to 0.5.1 to align with unified platform release

## [0.5.0] - 2025-12-23

### Added
- **Memory Service DTOs**: Added comprehensive data models for Memory Service
  - SemanticMemoryCreate, SemanticMemoryResponse - Knowledge storage with vector search
  - EpisodicMemoryCreate, EpisodicMemoryResponse - Interaction history
  - ProceduralMemoryResponse - Skills and procedures
  - WorkingMemorySet, WorkingMemoryResponse - Plan-scoped shared state

### Changed
- Bumped version to 0.5.0 to align with unified platform release

## [0.4.0] - 2025-12-21

### Changed
- Bumped version to 0.4.0 to align with unified platform release.

## [0.3.0] - 2025-12-20

### Changed
- Bumped version to 0.3.0 to align with unified platform release.

## [0.2.0] - 2025-12-20

### Added
- Initial release of common models and DTOs.
