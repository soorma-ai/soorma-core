# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
