# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.9.1] - 2026-04-18

### Changed
- Version alignment: bumped to 0.9.1 (event service synchronized with monorepo release)

## [0.9.0] - 2026-04-17

### Changed
- Version alignment: bumped to 0.9.0 (event service synchronized with monorepo release)
- Added TenancyMiddleware and DI-based platform tenant resolution for publish ingress.
- Enforced trust-boundary metadata policy on publish endpoint: authoritative platform_tenant_id overwrite, centralized tenant_id/user_id sanitization, required tenant_id/user_id checks, and max-length validation.
- Added fail-closed publish validation tests for spoofing overwrite, fallback behavior, mandatory identity fields, and oversized platform tenant IDs.
- Standardized Dockerfile to wheelhouse build/install strategy (`pip wheel`, `--find-links`, `--no-index`) so local shared packages are resolved consistently and runtime installs use prebuilt local artifacts.

## [0.8.2] - 2026-03-14

### Changed
- Version alignment: bumped to 0.8.2 (all components synchronized)



### Changed
- Version bumped to 0.8.1 to align with unified platform release (Stage 5 - Discovery & A2A Integration complete)
- No functional changes to event service

## [0.8.0] - 2026-02-23

### Changed
- Bumped version to 0.8.0 to align with unified platform release (Stage 4 - Planner & ChoreographyPlanner complete)
- Single source of truth for version: imports `__version__` from soorma-common
- Dynamic version usage in FastAPI metadata and health endpoint
- No functional changes to event service

### Changed
- Bumped version to 0.7.7 to align with unified platform release

## [0.7.6] - 2026-02-07

### Changed
- Bumped version to 0.7.6 to align with unified platform release

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
