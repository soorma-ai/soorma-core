# Changelog

All notable changes to the Soorma Core project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.7.7] - 2026-02-19

### Added
- **Stage 3 Phase 3 - Test Suite Expansion & Documentation (February 15, 2026)**
  - **Test Coverage Expansion (RF-SDK-004)**:
    - Added comprehensive TaskContext test suite (17 tests) covering persistence, delegation, parallel execution, error handling
    - Added Worker integration test suite (14 tests) covering decorators, assignment filtering, error handling, state management
    - Added Tool ↔ Worker integration test suite (7 tests) covering delegation chains, end-to-end workflows
    - **Total SDK Tests**: 294 (was 254, +40 new tests)
    - **Worker/TaskContext Coverage**: ~80% (was ~10%)
  - **Documentation Updates**:
    - Added Section 5 to ARCHITECTURE.md: Agent Models (Tool, Worker, Planner comparison)
    - Added TaskContext lifecycle diagram with mermaid
    - Updated README.md with Stage 3 progress indicator and example links
    - Updated SDK README.md with Tool and Worker model sections with code examples
    - Updated examples/README.md learning path with 08-worker-basic entry
  - **End-to-End Validation**:
    - Validated 08-worker-basic example: Order processing with parallel delegation (inventory + payment)
    - Validated 01-hello-tool example: Calculator operations (add, multiply) with synchronous response
    - Confirmed Memory Service task persistence: TaskContext save/restore/delete operations working
    - Confirmed stateless Tool model: No task persistence, auto-publish to response_event
    - No errors or warnings in platform/agent logs during validation
  - **Quality Metrics**: All 294 SDK tests passing + 126 Memory Service tests passing = 420 total

### Fixed
- Planner `@on_transition()` now routes wildcard events correctly, scopes to action-results, and filters to state-machine transitions

### Changed
- **Memory Service - Database Schema Improvements (February 12, 2026)**
  - **Foreign Key Constraints with CASCADE Delete**:
    - Added FK constraint to `task_context.user_id` → `users.id` with CASCADE delete (Migration 006)
    - Added FK constraint to `working_memory.user_id` → `users.id` with CASCADE delete (Migration 007)
    - Converted `plan_context.plan_id` from String to UUID with FK → `plans.id` and CASCADE delete (Migration 007)
  - **Referential Integrity**:
    - Ensures task contexts, working memory, and plan contexts are automatically cleaned up when users or plans are deleted
    - Prevents orphaned data in async worker task tracking
    - Creates proper cascade chain: User deleted → Plans deleted → PlanContext deleted
  - **Data Type Consistency**:
    - `plan_context.plan_id` now uses UUID type for consistency with plans table
    - Updated unique constraint from `(tenant_id, plan_id)` to `(plan_id)` since plan_id is now a FK
  - **Code Updates**:
    - Updated PlanContext CRUD/service/API layers to use UUID type for plan_id
    - Added type conversion between DTOs (str) and database (UUID) in service layer
  - **Test Coverage**: All 126 memory service tests passing
    - 18 TaskContext tests (CRUD, service, sub-task tracking)
    - 15 WorkingMemory tests (value types, CRUD operations)
    - 12 WorkingMemory deletion tests (user/plan isolation)
    - Full coverage of FK cascade behavior and referential integrity

## [0.7.6] - 2026-02-07

### Added
- **Stage 3 Phase 1 - Tool Model Refactor (RF-SDK-005)**
  - New `InvocationContext` for tool invocations
  - `@on_invoke(event_type)` decorator with multi-handler support
  - Auto-publish to caller-specified response event/topic
  - Optional response schema validation
- **New Example: 01-hello-tool**
  - Minimal calculator tool (add/subtract/multiply/divide)
  - CLI client with operation flags and inputs
  - start.sh workflow aligned with platform health checks

## [0.7.5] - 2026-01-30

### Added
- **Stage 2.1 Phase 3 - Working Memory Deletion (January 29, 2026)**
  - **User Ownership Enforcement** (RF-ARCH-013): Working memory now scoped by user_id
    - Added `user_id` column to `working_memory` table (Alembic migration 003)
    - Updated RLS policy to enforce both tenant_id AND user_id match
    - Prevents users from deleting/reading other users' plan state within same tenant
    - All working memory operations require both tenant_id and user_id parameters
  - **Working Memory Deletion API** (RF-SDK-020):
    - DELETE `/v1/memory/working/{plan_id}/{key}`: Delete single key
    - DELETE `/v1/memory/working/{plan_id}`: Delete all keys for plan
    - Proper 404 responses for non-existent keys/plans
  - **Service Layer**:
    - CRUD functions: `delete_working_memory_key()`, `delete_working_memory_plan()`
    - Service layer returns typed DTOs: `WorkingMemoryDeleteKeyResponse`, `WorkingMemoryDeletePlanResponse`
    - User ownership verified at database level via RLS
  - **SDK Enhancements** (RF-SDK-020):
    - `MemoryClient.delete_plan_state(plan_id, tenant_id, user_id, key=None)`
    - `WorkflowState.delete(key)`: Delete single key from plan state
    - `WorkflowState.cleanup()`: Delete all state for plan (resource reclamation)
  - **Common DTOs**:
    - `WorkingMemoryDeleteKeyResponse`: Single-key deletion response (success, deleted, message)
    - `WorkingMemoryDeletePlanResponse`: Plan-wide deletion response (success, count_deleted, message)
  - **Examples**:
    - Updated example 04-memory-working with cleanup pattern in planner.py
    - Added delete pattern documentation to README (immediate vs. deferred cleanup)
    - Added raw API deletion examples to memory_api_demo.py
  - **Documentation**:
    - Added "Cleanup and Deletion" pattern section to MEMORY_PATTERNS.md
    - Documented when to cleanup (after completion, sensitive data, resource reclamation)
    - Removed cleanup from "Future Enhancements" (now implemented)
  - **Tests**: 
    - Memory Service: 13 deletion tests (single key, all keys, tenant/user/plan isolation, idempotent)
    - SDK: 8 deletion tests (MemoryClient and WorkflowState helpers)
    - Total: 108 Memory Service tests + 226 SDK tests passing

### Changed
- **All working memory operations now require user_id**: Ensures proper isolation and ownership
  - CRUD layer: Updated all `set_working_memory()`, `get_working_memory()` signatures
  - API layer: X-User-ID header now required for all working memory endpoints
  - SDK: MemoryClient and WorkflowState pass user_id to all operations

### Fixed
- Tool invocation now sources `tenant_id`, `user_id`, `response_event`, and `response_topic` from EventEnvelope
- Tool registry event tracking now stores event types (not topic names)

## [0.7.4] - 2026-01-28

### Added
- **Semantic Memory Upsert (RF-ARCH-012)**: Knowledge can now be upserted via external_id or content_hash
  - `external_id`: Application-managed versioning for knowledge updates
  - `content_hash`: Auto-deduplication via SHA-256 hash of content
  - Four conditional unique indexes support both private and public knowledge scenarios
  - ON CONFLICT...DO UPDATE pattern for atomic upserts
- **Semantic Memory Privacy (RF-ARCH-014)**: User-scoped knowledge with public/private visibility
  - Required `user_id` parameter for all semantic memory operations
  - `is_public` boolean flag (default: FALSE) controls visibility
  - Private knowledge: unique per (tenant_id, user_id, external_id/content_hash)
  - Public knowledge: unique per (tenant_id, external_id/content_hash)
  - Row-Level Security policies enforce privacy at database level
- **SDK - User Context**: MemoryClient methods now accept `user_id` parameter
  - `store_knowledge(user_id, ...)` - Required parameter for knowledge storage
  - `query_knowledge(user_id, include_public=True, ...)` - Query with privacy filters
  - `delete_knowledge(user_id, ...)` - User-scoped deletion (not yet implemented)

### Changed
- **BREAKING - Semantic Memory API**: All semantic memory operations now require user_id
  - `POST /memory/semantic/knowledge` requires `user_id` parameter
  - `GET /memory/semantic/knowledge` requires `user_id` parameter
  - `DELETE /memory/semantic/knowledge` requires `user_id` parameter
  - Migration path: Extract user_id from auth context and pass to all memory operations
- **Database Schema**: Added user_id and is_public columns to semantic_knowledge table
  - Migration `002_upsert_privacy` handles schema update with backward compatibility
  - Existing knowledge defaults to is_public=TRUE for backward compatibility
  - Duplicate cleanup before unique index creation

### Fixed
- **Memory Service Migration**: Fixed pgcrypto extension dependency for content_hash
  - Added `CREATE EXTENSION IF NOT EXISTS pgcrypto` for digest() function
  - Shortened revision ID to '002_upsert_privacy' (18 chars) to fit VARCHAR(32) constraint
  - Fixed duplicate cleanup using ctid instead of MAX(UUID)
- **SDK - Query Parameters**: Fixed MemoryClient.query_knowledge() to use query params
  - Changed from sending query/limit/include_public in JSON body to query parameters
  - Aligns with FastAPI Query() parameter expectations

### Documentation
- **Stage 2.1 Complete**: Phase 1 & 2 (Upsert + Privacy) implemented and tested
  - See `docs/refactoring/STAGE_2.1_WORKING_PLAN.md` for implementation details
  - RF-ARCH-012, RF-ARCH-014, RF-SDK-019, RF-SDK-021 marked complete

### Added
- **Semantic Memory Upsert (RF-ARCH-012)**: Knowledge can now be upserted via external_id or content_hash
  - `external_id`: Application-managed versioning for knowledge updates
  - `content_hash`: Auto-deduplication via SHA-256 hash of content
  - Four conditional unique indexes support both private and public knowledge scenarios
  - ON CONFLICT...DO UPDATE pattern for atomic upserts
- **Semantic Memory Privacy (RF-ARCH-014)**: User-scoped knowledge with public/private visibility
  - Required `user_id` parameter for all semantic memory operations
  - `is_public` boolean flag (default: FALSE) controls visibility
  - Private knowledge: unique per (tenant_id, user_id, external_id/content_hash)
  - Public knowledge: unique per (tenant_id, external_id/content_hash)
  - Row-Level Security policies enforce privacy at database level
- **SDK - User Context**: MemoryClient methods now accept `user_id` parameter
  - `store_knowledge(user_id, ...)` - Required parameter for knowledge storage
  - `query_knowledge(user_id, include_public=True, ...)` - Query with privacy filters
  - `delete_knowledge(user_id, ...)` - User-scoped deletion (not yet implemented)

### Changed
- **BREAKING - Semantic Memory API**: All semantic memory operations now require user_id
  - `POST /memory/semantic/knowledge` requires `user_id` parameter
  - `GET /memory/semantic/knowledge` requires `user_id` parameter
  - `DELETE /memory/semantic/knowledge` requires `user_id` parameter
  - Migration path: Extract user_id from auth context and pass to all memory operations
- **Database Schema**: Added user_id and is_public columns to semantic_knowledge table
  - Migration `002_upsert_privacy` handles schema update with backward compatibility
  - Existing knowledge defaults to is_public=TRUE for backward compatibility
  - Duplicate cleanup before unique index creation

### Fixed
- **Memory Service Migration**: Fixed pgcrypto extension dependency for content_hash
  - Added `CREATE EXTENSION IF NOT EXISTS pgcrypto` for digest() function
  - Shortened revision ID to '002_upsert_privacy' (18 chars) to fit VARCHAR(32) constraint
  - Fixed duplicate cleanup using ctid instead of MAX(UUID)
- **SDK - Query Parameters**: Fixed MemoryClient.query_knowledge() to use query params
  - Changed from sending query/limit/include_public in JSON body to query parameters
  - Aligns with FastAPI Query() parameter expectations

### Documentation
- **Stage 2.1 Complete**: Phase 1 & 2 (Upsert + Privacy) implemented and tested
  - See `docs/refactoring/STAGE_2.1_WORKING_PLAN.md` for implementation details
  - RF-ARCH-012, RF-ARCH-014, RF-SDK-019, RF-SDK-021 marked complete
  - Phase 3 (Working Memory Deletion) deferred to future release

## [0.7.3] - 2026-01-26

### Added
- **SDK - EventToolkit Integration**: EventToolkit now available via `context.toolkit`
  - No `async with` needed - toolkit shares context's registry client
  - `discover_actionable_events()`: Find events consumed by active agents
  - `format_for_llm()`: Convert EventDefinitions to LLM-friendly dicts
  - `format_as_prompt_text()`: Generate formatted text for LLM prompts
  - Enables dynamic event discovery in planners without manual async context management
- **SDK - EventEnvelope Strict Typing**: Handlers now receive strongly-typed EventEnvelope objects
  - All event handlers receive `EventEnvelope` instead of `dict`
  - Type-safe access to event fields: `event.data`, `event.correlation_id`, `event.tenant_id`, `event.user_id`
  - EventClient automatically deserializes incoming events to EventEnvelope
  - Added `user_id` field to EventEnvelope for user-specific event routing
- **SDK - EventTopic Enum**: Type-safe topic handling across all SDK methods
  - EventClient.connect() and publish() accept `EventTopic` enum or strings
  - BusClient.subscribe() accepts `EventTopic` enum or strings
  - All examples updated to use `EventTopic.ACTION_REQUESTS`, `EventTopic.ACTION_RESULTS`, etc.
  - Type hints and IDE autocomplete for all 8 Soorma topics
- **Tests**: 12 new test files validating EventEnvelope and EventTopic changes
  - `test_event_envelope_handlers.py`: EventEnvelope deserialization and handler typing
  - `test_on_event_decorator.py`: EventTopic enum validation
  - Updated 15+ existing test files for EventEnvelope compatibility

### Changed
- **SDK - BREAKING: Event Handler Signature**: All event handlers must accept EventEnvelope
  - Before: `async def handler(event: Dict[str, Any], context: PlatformContext)`
  - After: `async def handler(event: EventEnvelope, context: PlatformContext)`
  - Migration: Update type hints and change `event.get("data")` → `event.data or {}`
  - Migration: Change `event.get("correlation_id")` → `event.correlation_id`
- **SDK - BREAKING: RegistryClient Refactored**: Now uses full RegistryClient from soorma.registry.client
  - `register()` → `register_agent(agent: AgentDefinition)`
  - `deregister()` → Direct HTTP DELETE call
  - `heartbeat()` → Direct HTTP PUT call
  - All methods use proper Pydantic models (AgentDefinition, EventDefinition)
- **SDK - Agent Base Class**: Enhanced initialization with AgentDefinition
  - Converts string capabilities to AgentCapability objects automatically
  - Appends version to agent name (e.g., "my-agent:1.0.0")
  - Uses `register_agent()` with structured AgentDefinition
- **SDK - BusClient Response Methods**: Clarified request/response patterns
  - `request()`: Publishes to action-requests with response_event (request/response pattern)
  - `respond()`: Publishes to action-results with correlation_id (completes request)
  - `announce()`: Publishes to business-facts (fire-and-forget)
- **SDK - CLI Templates**: Updated `soorma init` templates for EventEnvelope pattern
  - Worker template uses `EventEnvelope` and `EventTopic.ACTION_REQUESTS`
  - Tool template uses `EventEnvelope` and `EventTopic.ACTION_REQUESTS`
  - Test templates validate `context.bus.publish()` calls instead of return values
  - Removed obsolete `TaskContext` and `ToolRequest` imports

### Fixed
- **Example 06 - Router Orchestration Pattern**: Fixed client response handling
  - Router now stores client's correlation_id and response_event in working memory
  - Worker handlers (knowledge.stored, question.answered, concierge.response) retrieve client info
  - Workers respond to original CLIENT using client's response_event (not intermediate events)
  - Demonstrates proper orchestrator pattern with state management
- **Example 06 - RAG Agent**: Fixed dual-context retrieval with correct SDK methods
  - Uses `context.memory.get_recent_history()` for episodic context
  - Uses `context.memory.search_knowledge()` for semantic context
  - Fixed response structure to match router's expectations
- **research-advisor Example**: Updated all agents for EventEnvelope and SDK correctness
  - Planner uses `context.toolkit.discover_actionable_events()` without async with
  - Planner uses `context.toolkit.format_for_llm()` and `format_as_prompt_text()`
  - All workers use `bus.respond()` with correlation_id propagation
  - All handlers use EventEnvelope with proper type hints
- **All Examples**: Corrected SDK method usage patterns
  - Example 06: Router uses `bus.request()` for worker coordination
  - Example 06: Workers use `bus.respond()` to complete requests
  - research-advisor: Workers use `bus.respond()` instead of `bus.publish()`
  - All examples: EventTopic enum instead of string literals

### Documentation
- **README Improvements**: Comprehensive documentation updates across Examples 01-06
  - Streamlined all example READMEs to focus on learning objectives over implementation details
  - Abbreviated code samples while maintaining SDK accuracy and key concepts
  - Added "How it applies concepts" sections emphasizing conceptual understanding
  - Reduced documentation length by ~25% overall while improving clarity:
    - Example 01: 168 → 123 lines (27% reduction)
    - Example 04: 427 → 310 lines (27% reduction)
    - Example 05: 543 → 365 lines (33% reduction)
    - Example 06: 478 → 399 lines (17% reduction)
  - Emphasized that full code is available in Python files, READMEs teach concepts
- **Version Alignment**: Updated all components to 0.7.3
  - SDK (soorma-core): 0.7.3
  - Common library (soorma-common): 0.7.3
  - All services (memory, registry, event-service): 0.7.3

## [0.7.2] - 2026-01-23

### Changed
- **Documentation**: Cleaned up SDK README for PyPI publication
  - Removed all broken/incomplete code sections that were causing formatting issues
  - Streamlined to focus on installation, quick start, and documentation links
  - Removed detailed agent pattern examples and architecture diagrams (available in GitHub repo)
  - Reduced length by ~40% while maintaining all essential information
  - PyPI page now serves as concise landing page that directs to GitHub for comprehensive docs

## [0.7.1] - 2026-01-23

### Changed
- **Documentation**: Updated SDK README for PyPI publication accuracy
  - Updated version references from Pre-Alpha to "Day 0 (Pre-Alpha)" with v0.7.1
  - Removed outdated DisCo Trinity section with Goal/Plan/Task classes that don't match actual SDK
  - Simplified agent examples to match real implementation (Worker, Tool, Planner patterns)
  - Fixed Platform Context API methods to match actual SDK (removed non-existent methods)
  - Converted all relative repository links to absolute GitHub URLs for PyPI compatibility
  - Updated CLI commands to reflect actual implementation (removed non-existent flags)
  - Updated roadmap to show v0.6.0 and v0.7.0 as complete
  - Added comprehensive links to docs/ directory and examples/
  - Updated Advanced Usage section with current EventDefinition and EventToolkit patterns
- **Examples Documentation**: Added explicit LLM dependency requirements
  - Added installation instructions for `litellm` and `openai` packages
  - Marked examples 03, 05, 06 as requiring LLM dependencies in tables
  - Clarified that examples 01-02 work with just soorma-core

## [0.7.0] - 2026-01-21

### Added
- **Stage 2 - Foundation: Memory & Common DTOs (Complete ✅)**
  - **Memory Service enhancements**:
    - Task Context storage for async Worker completion (6 new endpoints)
    - Plan Context storage for Planner state machines (6 new endpoints)
    - Plans & Sessions management for lifecycle tracking (11 new endpoints)
    - Service layer architecture refactoring (API → Service → CRUD pattern)
    - 5 new database tables with PostgreSQL RLS enforcement
    - 37 tests passing (29 unit + 8 validation)
  - **SDK MemoryClient enhancements**:
    - 13 new methods for task/plan context and session management
    - WorkflowState helper class with 12 convenience methods
    - Tracker integration via events (removed direct API calls)
    - 192 SDK tests passing
  - **soorma-common library expansion**:
    - State Machine DTOs (StateAction, StateTransition, StateConfig, PlanDefinition)
    - A2A Protocol DTOs (A2AAgentCard, A2ATask, A2ASkill, etc.)
    - Progress Tracking DTOs (TaskState, TaskProgressEvent, TaskStateChanged)
    - 61 total exports, 44 tests passing
  - **Total test coverage**: 273 tests passing across SDK, soorma-common, and Memory Service

### Changed
- **TrackerClient - Breaking**: Progress tracking now via events instead of API calls
  - Removed: `emit_progress()`, `complete_task()`, `fail_task()`
  - Kept: `get_plan_status()`, `list_tasks()` (read-only queries)
  - Workers/Planners now publish to `system-events` topic

### Fixed
- Memory Service authentication: user_id extracted from query params or X-User-ID header
- Session.metadata renamed to session_metadata (SQLAlchemy reserved field conflict)
- Duplicate exception handling and incorrect db.commit() calls in sessions endpoint

## [0.6.0] - 2026-01-17

### Added
- **Agent Auto-Recovery on Heartbeat Failure (Production Critical Fix)**
  - Agents now automatically re-register when heartbeat fails (e.g., after laptop sleep)
  - Added consecutive failure tracking to prevent tight retry loops
  - Enhanced heartbeat logging with status codes and response details
  - Registry service now returns proper 404 errors for failed heartbeats (was 200 with success=false)
  - Added timestamp logging to registry service matching event-service format
  - **Tests**: 5 new tests validating auto-recovery behavior (all passing ✅)
  - **Impact**: Fixes critical issue where agents would be deleted after sleep but never recover

- **Stage 1 - Foundation Event System Refactoring (January 17, 2026)**
  - Added new fields to `EventEnvelope` for response routing and distributed tracing:
    - `response_event`: Event type for response (DisCo pattern for dynamic response coupling)
    - `response_topic`: Topic for response (defaults to action-results)
    - `trace_id`: Root trace ID for entire workflow
    - `parent_event_id`: ID of parent event in trace tree
    - `payload_schema_name`: Registered schema name for payload (enables dynamic schema lookup)
  - Added convenience methods to `BusClient` for enforcing event contracts:
    - `request()`: Publishes to action-requests with mandatory response_event
    - `respond()`: Publishes to action-results with mandatory correlation_id
    - `announce()`: Publishes to business-facts (no response expected)
  - Added event creation utilities to `BusClient` for metadata propagation:
    - `create_child_request()`: Auto-propagates trace_id, tenant_id, session_id from parent event
    - `create_response()`: Auto-matches correlation_id and uses request.response_event
    - `publish_envelope()`: Publishes pre-constructed EventEnvelope
  - Created comprehensive documentation:
    - `docs/MESSAGING_PATTERNS.md`: Guide to queue/broadcast/load-balancing patterns
  - **Tests**: 64 new tests covering all event system changes (all passing ✅)

### Changed
- **BREAKING: BusClient.publish() now requires explicit topic parameter**
  - Removed `_infer_topic()` method - no more automatic topic inference
  - Migration: Add explicit `topic="business-facts"` (or appropriate topic) to all `bus.publish()` calls
- **BREAKING: Agent.on_event() now requires topic parameter (keyword-only)**
  - Base Agent class requires explicit topic: `@agent.on_event("event.type", topic="business-facts")`
  - Worker, Tool, and Planner classes provide defaults internally for their specialized decorators
  - Migration: Add `topic` parameter to all `@agent.on_event()` decorators
- **Registry Service Heartbeat Enhancement**
  - Heartbeat endpoint now returns 404 Not Found for nonexistent agents (was 200 OK with success=false)
  - Enables SDK to properly detect and recover from agent deletion
- Updated all examples to use new event system patterns:
  - `01-hello-world/`: Uses explicit topics and demonstrates `respond()` convenience method
  - `02-events-simple/`: Updated all event handlers with explicit topics
  - `03-events-structured/`: Updated ticket routing handlers with explicit topics
  - `research-advisor/`: Updated all agents (planner, researcher, advisor, validator) with explicit topics
- Updated `EventClient.on_event()` to accept optional `topic` parameter for API consistency

### Fixed
- **Critical: Agent auto-recovery after heartbeat failures**
  - Agents now automatically re-register when heartbeat fails (fixes laptop sleep issue)
  - SDK logs heartbeat failures with HTTP status and response details for debugging
  - Registry cleanup correctly deletes expired agents (TTL enforcement working as designed)

### Documentation
- **Stage 1 Completion**: All EventEnvelope, BusClient, and on_event() refactoring complete
- **Completion Criteria Met**:
  - ✅ EventEnvelope has new fields (including payload_schema_name)
  - ✅ Event Service messaging patterns documented (queue_group usage in MESSAGING_PATTERNS.md)
  - ✅ BusClient.publish() requires topic
  - ✅ BusClient has create_child_request() and create_response() utilities
  - ✅ on_event() requires topic for base Agent
  - ✅ All tests pass (64/64)
  - ✅ Examples updated with pattern usage

### Added
- **Documentation Restructure**: Separated concerns into focused documents
  - Created `docs/DEVELOPER_GUIDE.md` with developer experience patterns and workflows
  - Created `docs/DESIGN_PATTERNS.md` with Autonomous Choreography and Circuit Breakers
  - Created `docs/MEMORY_PATTERNS.md` with CoALA memory types and usage patterns
  - Created `docs/EVENT_PATTERNS.md` with event-driven communication patterns
  - All docs now cross-reference each other appropriately
- **Examples Refactor (Phase 1)**: Foundation examples with progressive learning path
  - Created `examples/README.md` with comprehensive learning path and pattern catalog
  - Updated `01-hello-world/` to use correct topics (action-requests/action-results)
  - Updated `02-events-simple/` to use correct topics (business-facts)
  - Refactored `03-events-structured/` with EventDefinition pattern and SDK auto-registration
  - Split LLM utilities into `llm_utils.py` (educational boilerplate) and `ticket_router.py` (agent logic)
  - Created `docs/TOPICS.md` documenting all 8 Soorma topics with usage guidance and decision tree
  - Updated `docs/EVENT_PATTERNS.md` with topics section

### Removed
- **Old examples/**: Removed legacy `examples/hello-world/` directory (replaced by `examples/01-hello-world/`)
  - `01-hello-world/` is now a simple Worker pattern example focused on event handling basics and DX
  - All documentation now references `01-hello-world` consistently
  - Updated README.md, SDK README, ARCHITECTURE.md to accurately describe the example

### Changed
- **ARCHITECTURE.md**: Refactored to focus exclusively on platform services
  - Removed developer experience sections (moved to DEVELOPER_GUIDE.md)
  - Removed agent patterns (moved to DESIGN_PATTERNS.md)
  - Removed testing strategy (moved to DEVELOPER_GUIDE.md)
  - Now focused on: Platform Services, Event Architecture, Deployment, Contributing
- **DESIGN_PATTERNS.md**: Enhanced with key architectural concepts
  - Added comprehensive "Autonomous Choreography" section explaining registration → discovery → reasoning → decision → execution flow
  - Added "Circuit Breakers & Safety" section with action limits, vague result detection, and timeout handling
- **MEMORY_PATTERNS.md**: Updated all examples to match actual SDK implementation
  - Fixed Semantic Memory to use `store_knowledge()` and `search_knowledge()`
  - Fixed Episodic Memory to use `log_interaction()`, `get_recent_history()`, `search_interactions()`
  - Fixed Working Memory characteristics (PostgreSQL-backed, not in-memory)
  - Updated anti-patterns with correct method signatures
- **DEVELOPER_GUIDE.md**: Comprehensive developer experience documentation
  - Corrected all service ports to 8000/8001/8002 (from incorrect 8081/8082/8083)
  - Updated Integration Developer example to use EventDefinition pattern with proper topics
  - Changed LLM examples to reference 03-events-structured (from research-advisor)
  - Fixed VS Code launch.json and curl commands with correct ports
- **AI_ASSISTANT_GUIDE.md**: Updated to match current patterns
  - Fixed 03-events-structured prompts to show EventDefinition pattern with Pydantic models
  - Emphasized SDK auto-registration (no manual registry_setup.py needed)
  - Removed incorrect registry_setup.py references
  - Added EventTopic enum usage in examples
- **03-events-structured**: Migrated from dict-based events to EventDefinition pattern
  - Created Pydantic payload models for all 6 support routing events
  - Workers now pass EventDefinition objects to events_consumed/events_produced
  - SDK automatically registers events on agent startup (no manual registration needed)
  - Removed `registry_setup.py` - superseded by SDK auto-registration
  - Removed `llm_event_selector.py` - split into `llm_utils.py` + `ticket_router.py`

### Fixed
- **All Documentation**: Corrected service ports across all docs
  - Registry Service: Port 8000 (was incorrectly shown as 8081)
  - Event Service: Port 8001 (was incorrectly shown as 8082)
  - Memory Service: Port 8002 (was incorrectly shown as 8083)
- **All Examples**: Corrected topic usage to match Soorma's 8 fixed topics
  - Examples were using arbitrary topics ("requests", "orders", "tickets", "results")
  - Now using proper EventTopic enum values from soorma_common
  - All EventClient.connect() calls now include topics parameter
- **Memory Patterns**: Fixed all API method calls to match actual SDK implementation
  - Corrected semantic memory methods (store_knowledge vs store with memory_type)
  - Corrected episodic memory methods (log_interaction vs store)
  - Updated working memory description (Redis planned, currently PostgreSQL)

## [0.5.1] - 2025-12-24

### Added
- **SDK - Memory Client**: New clean API methods for CoALA memory types
  - `store_knowledge()`: Store facts in Semantic Memory with automatic embeddings
  - `search_knowledge()`: Vector search Semantic Memory with similarity scores
  - `search_interactions()`: Vector search Episodic Memory for past interactions
  - Semantic search relevance threshold (0.7) in research-advisor example to prevent false cache hits
- **Research Advisor Example**: Complete memory architecture demonstration
  - Semantic memory caching with search-before-store pattern
  - Dual storage (Semantic + Working Memory) for cross-plan knowledge reuse
  - Memory usage documentation in agent files explaining CoALA patterns
  - Comprehensive memory architecture section in ARCHITECTURE.md (190+ lines)
- **Autonomous Orchestration**: Enhanced planner decision-making
  - LLM-driven intent detection for user feedback vs new questions
  - Validation critique passed to drafter via event schema descriptions
  - Self-documenting event schemas with field-level usage guidance
- **Documentation**: Memory Service integration across all docs
  - Updated top-level ARCHITECTURE.md with Memory Service section
  - Enhanced SDK README with CoALA memory examples
  - Updated services README with Memory Service overview
  - Memory Service SDK documentation with full API reference

### Changed
- **SDK - Memory Client API - Backward Compatible**: Simplified method signatures
  - `store()`: Removed `memory_type` parameter, now only handles Working Memory
  - Deprecated `search()`: Now delegates to `search_knowledge()` for semantic type
  - Context wrapper provides clean separation of memory types
- **Event Schemas**: Enhanced field descriptions for autonomous reasoning
  - `DraftRequestPayload.critique`: Added guidance on when to include validation feedback
  - Event descriptions now explain revision/retry use cases
- **Research Advisor Example**: Improved workflow resilience
  - Planner detects user feedback/corrections vs new questions
  - Explicit trigger context guides LLM on validation failure handling
  - Removed hardcoded keyword-based rules in favor of LLM reasoning
- **Documentation**: Consistent `soorma dev --build` command across all READMEs

### Fixed
- **Research Advisor**: Validation feedback loop
  - Planner now requests new drafts with critique when validation fails
  - Drafter receives and incorporates validation feedback
  - Eliminated infinite validation-only loops
- **Research Advisor**: Indentation errors in researcher.py
  - Fixed try-except block alignment
  - Corrected conditional logic indentation

### Version Bumps
- soorma-core (SDK): 0.5.1
- Research advisor example: 0.5.1

## [0.5.0] - 2025-12-23

### Added
- **Memory Service**: Complete implementation of persistent memory layer for autonomous agents
  - CoALA (Cognitive Architectures for Language Agents) framework with 4 memory types:
    - Semantic Memory: Knowledge base with RAG and vector search
    - Episodic Memory: User/Agent interaction history with temporal recall
    - Procedural Memory: Dynamic prompts, rules, and skills
    - Working Memory: Plan-scoped shared state for multi-agent collaboration
  - PostgreSQL with pgvector for semantic search (HNSW indexes)
  - Row Level Security (RLS) for native multi-tenancy isolation
  - Automatic embedding generation via OpenAI API
  - Local development mode with default tenant
  - Production-ready JWT authentication middleware
  - Comprehensive API documentation and architecture design docs
- **Shared DTOs**: Memory Service DTOs in soorma-common library
  - SemanticMemoryCreate, SemanticMemoryResponse
  - EpisodicMemoryCreate, EpisodicMemoryResponse
  - ProceduralMemoryResponse
  - WorkingMemorySet, WorkingMemoryResponse
- **SDK - Memory Client**: Full MemoryClient implementation in Python SDK with all CoALA memory types
- **SDK - Dev CLI**: PostgreSQL + Memory Service added to Docker Compose infrastructure
- **Services Overview**: Added comprehensive services/README.md documentation

### Changed
- **SDK - Dev CLI - Breaking**: Simplified `soorma dev` command
  - Removed agent execution functionality (AgentRunner, find_agent_entry_point)
  - Removed `--infra-only`, `--detach`, `--no-watch` flags
  - Default behavior: start infrastructure only, agents run separately
  - Added `--start` flag for consistency with `--stop`
- **Registry Service**: Now uses PostgreSQL instead of SQLite in dev environment
- **Documentation**: Updated all READMEs and examples for new CLI behavior

### Fixed
- **Dev CLI**: PostgreSQL healthcheck connection errors

### Version Bumps
- soorma-common: 0.5.0 across all dependent packages

## [0.4.0] - 2025-12-21

### Added
- Multi-provider LLM support in research-advisor example via `llm_utils.py`
  - Automatic model selection based on available API keys
  - Support for OpenAI, Anthropic, Google/Gemini, Azure, Together AI, and Groq
  - `get_llm_model()` and `has_any_llm_key()` helper functions

### Changed
- Updated research-advisor example agents to use dynamic model selection
  - `advisor.py`: Now uses `get_llm_model()` instead of hardcoded GPT-4.1-nano
  - `planner.py`: Now uses `get_llm_model()` instead of hardcoded GPT-4.1-nano
  - `researcher.py`: Now uses `get_llm_model()` instead of hardcoded GPT-4.1-nano
  - `validator.py`: Now uses `get_llm_model()` instead of hardcoded GPT-4.1-nano
- Major refactor of `planner.py` for autonomous choreography
  - Removed hardcoded workflow rules
  - Implemented LLM reasoning over dynamically discovered event metadata
  - Added circuit breakers (max actions limit, vague result detection)
  - Improved prompt engineering for autonomous agent orchestration
- Updated README.md with comprehensive documentation on:
  - Autonomous choreography vs traditional orchestration
  - LLM reasoning engine approach
  - Circuit breaker patterns
  - Multi-provider LLM configuration
- Updated ARCHITECTURE.md with deep technical details on:
  - Why to avoid hardcoded workflow rules
  - DisCo protocol implementation
  - Prompt engineering strategies
  - Circuit breaker implementations
  - Future Tracker service plans

### Fixed
- Infinite loop issues in planner (research → draft → research cycles)
- Payload mismatches in validation requests (`research_context` → `source_text`)
- Vague result detection preventing meta-descriptions instead of actual content
- LLM skipping required workflow steps (validation before completion)
