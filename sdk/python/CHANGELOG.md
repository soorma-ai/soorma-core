# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

