# Changelog

All notable changes to the Soorma Core project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
