# Event Service

The Event Service is a smart proxy/gateway that decouples Soorma agents from the underlying message bus (NATS, Google Pub/Sub, Kafka, etc.).

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Agent                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │           SDK EventClient                           │    │
│  │  • publish() → POST /v1/events/publish              │    │
│  │  • subscribe() → GET /v1/events/stream (SSE)        │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Event Service (Proxy)                    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  FastAPI Endpoints                                  │    │
│  │  • POST /v1/events/publish                          │    │
│  │  • GET /v1/events/stream?topics=research.*          │    │
│  └─────────────────────────────────────────────────────┘    │
│                              │                              │
│                              ▼                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Adapter Interface                                  │    │
│  │  • publish(topic, message)                          │    │
│  │  • subscribe(topic, callback)                       │    │
│  └─────────────────────────────────────────────────────┘    │
│           │                 │                 │             │
│           ▼                 ▼                 ▼             │
│  ┌────────────┐  ┌────────────────┐  ┌──────────────┐       │
│  │   NATS     │  │  Google PubSub │  │    Kafka     │       │
│  │  Adapter   │  │    Adapter     │  │   Adapter    │       │
│  └────────────┘  └────────────────┘  └──────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

## Why SSE (Server-Sent Events)?

We use SSE for downstream event delivery (Service → Agent) because:

1. **Simple for Local Dev**: No need for agents to run HTTP servers or configure webhooks
2. **Firewall Friendly**: Works through NAT and firewalls (standard HTTP)
3. **Auto-Reconnection**: Built-in retry semantics
4. **Lightweight**: No WebSocket complexity, just HTTP

## API Endpoints

### Publish Event
```
POST /v1/events/publish
Content-Type: application/json

{
  "event": {
    "source": "agent-123",
    "type": "research.requested",
    "topic": "action-requests",
    "data": {"query": "What is quantum computing?"},
    "correlation_id": "trace-abc"
  }
}
```

### Subscribe to Events (SSE Stream)
```
GET /v1/events/stream?topics=research.*,billing.alert&agent_id=agent-123
Accept: text/event-stream

# Response (SSE format):
event: message
data: {"id": "...", "type": "research.requested", "data": {...}}

event: message
data: {"id": "...", "type": "research.completed", "data": {...}}
```

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `EVENT_SERVICE_PORT` | `8082` | HTTP port for the service |
| `EVENT_ADAPTER` | `nats` | Adapter type: `nats`, `pubsub`, `kafka`, `memory` |
| `NATS_URL` | `nats://localhost:4222` | NATS server URL |
| `REDIS_URL` | `redis://localhost:6379` | Redis for subscription state (optional) |

## Local Development

```bash
# Start the service
cd core/services/event-service
poetry install
poetry run uvicorn src.main:app --reload --port 8082

# Or with Docker
docker compose up event-service
```

## Dependencies

- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `sse-starlette` - Server-Sent Events support
- `nats-py` - NATS client (for NATS adapter)
- `httpx` - HTTP client for webhooks (fallback)
