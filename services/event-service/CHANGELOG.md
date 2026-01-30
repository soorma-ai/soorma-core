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
- Bumped version to 0.5.0 to align with unified platform release

## [0.4.0] - 2025-12-21

### Changed
- Bumped version to 0.4.0 to align with unified platform release.

## [0.3.0] - 2025-12-20

### Changed
- Bumped version to 0.3.0 to align with unified platform release.

## [0.2.0] - 2025-12-20

### Added
- Implemented NATS Queue Groups using `agent_name` for load balancing subscribers.
- Added `agent_name` query parameter support to `/v1/events/stream` endpoint.
- Added integration tests for SSE streaming with `uvicorn` background server.
- Added `test_queue_groups.py` to verify load balancing behavior.

### Changed
- Refactored project structure to standard `api`, `core`, `services`, `adapters` layout.
- Updated `EventTopic` serialization in NATS subjects to use string values instead of Enum objects.
- Suppressed `uvicorn` and `websockets` deprecation warnings in `pyproject.toml`.

### Fixed
- Fixed "Hello World" event delivery issue where subscribers were not receiving events due to incorrect NATS subject format.
- Fixed SSE integration tests hanging by replacing `ASGITransport` with a real background server.
