# Changelog — soorma-nats

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.8.1] - 2026-03-02

### Added
- Initial release: `NATSClient` for Soorma infrastructure services
- Extracted from Event Service `NatsAdapter` pattern; replaces SDK `EventClient` dependency in Tracker Service (TECH-DEBT-001)
- Features: `connect()`, `subscribe()` (with queue groups), `unsubscribe()`, `disconnect()`
- Auto-reconnection with configurable retry settings (`max_reconnect_attempts`, `reconnect_time_wait`)
- JSON message deserialization with subject→topic mapping (`soorma.events.*` namespace)
- Graceful drain-and-disconnect on shutdown
- Custom exceptions: `NATSConnectionError`, `NATSSubscriptionError`
- 33 unit tests with 100% coverage of `client.py`
