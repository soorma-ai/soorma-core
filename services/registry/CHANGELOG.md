# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.7.5] - 2026-01-22

### Changed
- **Stage 2.1 Refactoring**: Completed comprehensive codebase refactoring
  - Unified error handling with custom exception hierarchy
  - Standardized logging across all modules
  - Improved code organization and module structure
  - Enhanced documentation and code clarity
- Bumped version to 0.7.5 to align with unified platform release

## [0.7.0] - 2026-01-21

### Changed
- Bumped version to 0.7.0 to align with unified platform release

## [0.5.1] - 2025-12-24

### Changed
- Bumped version to 0.5.1 to align with unified platform release

## [0.5.0] - 2025-12-23

### Changed
- **Database**: Now uses PostgreSQL instead of SQLite in Docker Compose dev environment
  - Provides data persistence across container restarts
  - Production-parity configuration
  - Separate `registry` database with pgvector support
- Bumped version to 0.5.0 to align with unified platform release

## [0.4.0] - 2025-12-21

### Changed
- Bumped version to 0.4.0 to align with unified platform release.

## [0.3.0] - 2025-12-20

### Changed
- **API Update**: Updated `POST /api/v1/agents` to accept full `AgentRegistrationRequest` structure, enabling rich capability schemas and descriptions.
- **Data Model**: Removed `AgentRegistrationFlat` to prevent data loss during registration.

## [0.2.0] - 2025-12-20

### Changed
- Updated `query_agents` to deduplicate results by agent name, showing only the most recently active instance for each agent type. This improves scalability and readability of the registry listing.

