# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-12-20

### Added
- Added `agent_name` query parameter to SSE stream connection URL to support subscriber groups.
- Added `agent_name` parameter to `EventClient.subscribe` method (optional).

### Changed
- Updated `_stream_events` to include `agent_name` in the connection URL.
