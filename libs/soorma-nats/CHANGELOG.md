# Changelog — soorma-nats

## v0.1.0 (2026-03)

- Initial release: `NATSClient` for Soorma infrastructure services
- Extracted from Event Service `NatsAdapter` pattern
- Used by Tracker Service (replaces SDK `EventClient` dependency)
- Features: connect, subscribe (with queue groups), unsubscribe, disconnect
- Auto-reconnection with configurable retry settings
- JSON message deserialization
- Subject namespace: `soorma.events.*`
