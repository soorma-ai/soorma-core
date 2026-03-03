# soorma-nats

Shared NATS client library for Soorma infrastructure services.

## Overview

Provides a simple, opinionated NATS client suitable for infrastructure services that need to subscribe to events directly from the NATS broker. This is **not** an SDK-facing library — it is for internal service-to-service communication only.

## Usage

```python
from soorma_nats import NATSClient

client = NATSClient(url="nats://localhost:4222")
await client.connect()

async def on_message(subject: str, message: dict) -> None:
    print(f"Received on {subject}: {message}")

await client.subscribe(
    topics=["action-requests", "action-results"],
    callback=on_message,
    queue_group="my-service",
)

# On shutdown:
await client.disconnect()
```

## Subject Namespace

All topics are mapped to `soorma.events.<topic>`. For example:
- `action-requests` → `soorma.events.action-requests`
- `action-results` → `soorma.events.action-results`
- `system-events` → `soorma.events.system-events`

## Consumers

- **Tracker Service** — v0.8.1+ (replaces SDK `EventClient` dependency)
- **Event Service** — future migration (Stage 6)

## Changelog

See [CHANGELOG.md](CHANGELOG.md).
