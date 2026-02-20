# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
