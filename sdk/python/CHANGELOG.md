# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

