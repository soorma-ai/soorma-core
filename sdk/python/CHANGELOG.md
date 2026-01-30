# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.7.5] - 2026-01-30

### Added
- **Stage 2.1 Phase 1 & 2 - Semantic Memory Enhancements (January 27-30, 2026)** [RF-SDK-019, RF-SDK-021]
  - **Semantic Memory Upsert Support** [RF-SDK-019]:
    - Added `external_id` parameter to `store_knowledge()` method
    - Supports versioned knowledge updates via external_id (application-controlled)
    - Automatic deduplication via content_hash when external_id not provided
    - Backward compatible (external_id optional, defaults to None)
    - Enables update-or-insert patterns for document versioning
  - **Semantic Memory Privacy Model** [RF-SDK-021]:
    - Added `user_id` parameter (required) to `store_knowledge()` and `query_knowledge()` methods
    - Added `is_public` parameter (optional, default False) to `store_knowledge()`
    - Private knowledge: returned only to owning user + any user querying public knowledge
    - Public knowledge: returned to all users in tenant (when is_public=True)
    - Breaking change: user_id now required for all semantic memory operations
    - Rationale: Semantic memory is agent memory (CoALA), not a general RAG solution
  - **MemoryClient API Updates**:
    - `store_knowledge(content, embedding, user_id, is_public=False, external_id=None, ...)`
    - `query_knowledge(query_embedding, user_id, include_public=True, ...)`
    - All semantic operations now require user_id for multi-user isolation
  - **Type Safety**: Updated DTOs with new fields in SemanticMemoryCreate, SemanticMemoryResponse
  - **Tests**: 239 total SDK tests passing
    - 8 new Stage 2.1 specific tests (4 upsert + 4 privacy)
    - 210 existing tests maintained and passing
    - Full coverage of upsert, privacy, and query filtering scenarios

### Fixed
- **Registry Service Agent Deduplication Test**: Fixed test_agent_deduplication_by_name
  - Updated expectations for versioned agent names (now include ":1.0.0" suffix)
  - Test now expects "planner-agent:1.0.0" instead of plain "planner-agent"

## [0.7.3] - 2026-01-26

### Changed
- **Documentation improvements** for all examples (01-06):
  - Streamlined README files to focus on learning objectives and concepts
  - Abbreviated code samples while maintaining SDK method accuracy
  - Added "How it applies concepts" sections to each example
  - Removed verbose explanations in favor of directing developers to source code
  - Reduced total documentation by ~25% while improving clarity
  - Examples now emphasize patterns over implementation details
- **Example 01** (Hello World): Condensed from 168 to 123 lines (27% reduction)
- **Example 02** (Events Simple): Streamlined event publishing patterns
- **Example 03** (Structured Events): Clarified LLM routing and event discovery
- **Example 04** (Working Memory): Reduced from 427 to 310 lines (27% reduction)
- **Example 05** (Semantic Memory): Reduced from 543 to 365 lines (33% reduction)
- **Example 06** (Episodic Memory): Reduced from 478 to 399 lines (17% reduction)

## [0.7.0] - 2026-01-21

### Changed
- **Documentation improvements** for all examples (01-06):
  - Streamlined README files to focus on learning objectives and concepts
  - Abbreviated code samples while maintaining SDK method accuracy
  - Added "How it applies concepts" sections to each example
  - Removed verbose explanations in favor of directing developers to source code
  - Reduced total documentation by ~25% while improving clarity
  - Examples now emphasize patterns over implementation details
- **Example 01** (Hello World): Condensed from 168 to 123 lines (27% reduction)
- **Example 02** (Events Simple): Streamlined event publishing patterns
- **Example 03** (Structured Events): Clarified LLM routing and event discovery
- **Example 04** (Working Memory): Reduced from 427 to 310 lines (27% reduction)
- **Example 05** (Semantic Memory): Reduced from 543 to 365 lines (33% reduction)
- **Example 06** (Episodic Memory): Reduced from 478 to 399 lines (17% reduction)

## [0.7.0] - 2026-01-21

### Added
- **Stage 2 - Memory & Common DTOs Foundation (January 21, 2026)**
  - **MemoryClient enhancements** for task/plan context persistence:
    - `store_task_context()`, `get_task_context()`, `update_task_context()`, `delete_task_context()`: Async Worker state management
    - `get_task_by_subtask()`: Find parent task by subtask correlation ID
    - `store_plan_context()`, `get_plan_context()`, `update_plan_context()`: Planner state machine persistence
    - `get_plan_by_correlation()`: Find plan by task correlation ID
    - `create_plan()`, `list_plans()`: Plan lifecycle management
    - `create_session()`, `list_sessions()`: Conversation session grouping
    - `set_plan_state()`, `get_plan_state()`: Working memory key-value operations
  - **WorkflowState helper class** (`soorma.workflow.WorkflowState`):
    - `record_action()`, `get_action_history()`: Event timeline tracking
    - `set()`, `get()`, `delete()`, `clear()`: State management
    - `exists()`, `get_all()`: State inspection
    - `increment()`, `append()`, `update_dict()`: Convenience operations
    - `set_ttl()`: Expiration support
    - Reduces working memory boilerplate from 8+ lines to 1 line per operation
  - **TrackerClient event integration**: Removed direct API calls, agents now publish to system-events topic
    - Removed: `emit_progress()`, `complete_task()`, `fail_task()`
    - Kept: `get_plan_status()`, `list_tasks()` (read-only queries)
  - **Tests**: 192 SDK tests passing, comprehensive coverage for all memory operations

### Changed
- **TrackerClient - Breaking**: Progress tracking now via events instead of API calls
  - Workers/Planners publish to `system-events` topic
  - Tracker Service will subscribe (implemented in Stage 4)
  - Decouples SDK from direct service dependencies

## [0.5.1] - 2025-12-24

### Added
- **Memory Client API**: Clean CoALA-compliant methods for memory operations
  - `store_knowledge(content, metadata)`: Store facts in Semantic Memory
  - `search_knowledge(query, limit)`: Vector search with similarity scores
  - `search_interactions(agent_id, query, user_id, limit)`: Search Episodic Memory
- **Tests**: 22 new unit tests for memory client wrapper (33 total, 100% coverage)
- **Documentation**: Updated README with CoALA memory examples and patterns

### Changed
- **Memory Client API - Breaking**: Simplified `store()` method signature
  - Removed `memory_type` parameter - now only handles Working Memory
  - Use type-specific methods (`store_knowledge`, `log_interaction`) for other memory types
- **Memory Client API - Deprecated**: `search()` method deprecated in favor of `search_knowledge()`
  - Still functional for backward compatibility, delegates to `search_knowledge()`
  - Will be removed in version 1.0.0

### Fixed
- Memory client test coverage improved to 100% for all public methods

## [0.5.0] - 2025-12-23

### Added
- **Memory Service SDK**: Complete MemoryClient implementation with CoALA framework support
  - `store_knowledge()` / `search_knowledge()` - Semantic memory with vector search
  - `log_interaction()` / `get_recent_history()` / `search_interactions()` - Episodic memory
  - `get_relevant_skills()` - Procedural memory retrieval
  - `set_plan_state()` / `get_plan_state()` - Working memory management
- **Platform Context**: Updated MemoryClient in context.py to use real Memory Service with fallback to local storage
- **Dev CLI - PostgreSQL**: Added PostgreSQL + pgvector to Docker Compose infrastructure
  - Separate databases for Registry Service and Memory Service
  - Automatic database initialization with pgvector extension
  - Persistent volume for data across container restarts
- **Dev CLI - Memory Service**: Added Memory Service to Docker Compose stack
  - Auto-build support via SERVICE_DEFINITIONS
  - Health checks and proper service dependencies
  - Environment variable passthrough (OPENAI_API_KEY, DATABASE_URL)
- **Tests**: Comprehensive test suite for MemoryClient (11 tests covering all operations)

### Changed
- **Dev CLI - Breaking**: Simplified `soorma dev` command (removed agent execution)
  - Removed `--infra-only` flag (now default behavior)
  - Removed `--detach` flag (infrastructure always runs in background)
  - Removed `--no-watch` flag (hot reload feature removed)
  - Removed AgentRunner class and agent auto-detection
  - Added `--start` flag for consistency with `--stop`
  - Default behavior: start infrastructure only, developers run agents separately
- **Dev CLI - Database**: Registry Service now uses PostgreSQL instead of SQLite in dev environment
  - Prevents data loss on container restarts
  - Production-parity configuration
  - Database-level isolation between services
- **Documentation**: Updated all READMEs and examples to reflect new CLI behavior
  - Main README.md: Quick start and component status
  - SDK README.md: CLI usage and examples
  - hello-world example: Infrastructure startup instructions
  - research-advisor example: Infrastructure startup instructions

### Fixed
- **Dev CLI**: PostgreSQL healthcheck now uses `postgres` database to prevent connection errors
- **Platform Context**: Fixed dataclass field ordering in MemoryClient wrapper

## [0.4.0] - 2025-12-21

### Added
- **Examples**: Added `research-advisor` example demonstrating advanced "DisCo Trinity" pattern with dynamic choreography and circuit breakers.
- **Agent SDK**: Updated `Agent`, `Planner`, `Worker`, and `Tool` constructors to accept structured `AgentCapability` and `EventDefinition` objects.
- **Event Registration**: Added automatic registration of `EventDefinition`s during agent startup.
- **Registry Client**: Added `register_event()` method to `RegistryClient`.
- **Tests**: Added tests for Structured Agent definitions.

## [0.3.0] - 2025-12-20

### Added
- **Registry Client**: Added full `RegistryClient` implementation for interacting with the Registry Service.
- **AI Integration**: Added `EventToolkit` and `AI Tools` (OpenAI function calling) for dynamic event discovery and payload generation.
- **Structured Registration**: Added support for `AgentCapability` objects in `context.register()` for defining rich capability schemas.
- **Models**: Added `AgentCapability`, `EventDefinition`, and related DTOs in `soorma.models`.
- **Tests**: Added comprehensive tests for Registry Client, AI Event Toolkit, and AI Tools.

### Changed
- Enhanced `context.register()` to automatically convert legacy string-based capabilities to structured `AgentCapability` objects for backward compatibility.

## [0.2.0] - 2025-12-20

### Added
- Added `agent_name` query parameter to SSE stream connection URL to support subscriber groups.
- Added `agent_name` parameter to `EventClient.subscribe` method (optional).

### Changed
- Updated `_stream_events` to include `agent_name` in the connection URL.

