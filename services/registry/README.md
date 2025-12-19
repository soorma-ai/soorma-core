# Registry Service

Event and Agent Registry Service for the Soorma platform. This service provides:

- **Event Registry**: Register and query event definitions with their schemas
- **Agent Registry**: Register and query agent definitions with their capabilities

## Development Setup

```bash
# Install soorma-common first (from core/libs/soorma-common)
cd ../../libs/soorma-common
pip install -e .

# Install registry-service
cd ../../services/registry
pip install -e ".[dev]"

# Run database migrations
alembic upgrade head
```

## Running the Service

```bash
# From core/services/registry/
uvicorn registry_service.main:app --reload --port 8000

# Or using Python directly
python -m registry_service.main
```

## API Endpoints

### Event Registry

- `POST /api/v1/events` - Register a new event
- `GET /api/v1/events` - Query events

### Agent Registry

- `POST /api/v1/agents` - Register a new agent
- `GET /api/v1/agents` - Query agents
- `PUT /api/v1/agents/{agent_id}/heartbeat` - Refresh agent heartbeat

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `IS_PROD` | `false` | Production mode (disables docs) |
| `IS_LOCAL_TESTING` | `true` | Use SQLite for local testing |
| `DATABASE_URL` | `sqlite+aiosqlite:///./registry.db` | Async database URL |
| `SYNC_DATABASE_URL` | (derived from DATABASE_URL) | Sync database URL for Alembic |
| `AGENT_TTL_SECONDS` | `300` | Agent registration TTL (5 min) |
| `AGENT_CLEANUP_INTERVAL_SECONDS` | `60` | Cleanup interval (1 min) |

## Docker

### Build

From the **soorma-core root** directory (i.e., `soorma-platform/core/` in the monorepo):

```bash
docker build -f services/registry/Dockerfile -t registry-service .
```

### Run (SQLite - local testing)

```bash
# Start the container
docker run -d --name registry-service -p 8000:8000 \
  -e DATABASE_URL="sqlite+aiosqlite:////tmp/registry.db" \
  -e SYNC_DATABASE_URL="sqlite:////tmp/registry.db" \
  registry-service

# Run database migrations
docker exec registry-service alembic upgrade head

# Verify it's running
curl http://localhost:8000/health
```

### Run (PostgreSQL - production)

```bash
# Start the container
docker run -d --name registry-service -p 8000:8000 \
  -e DATABASE_URL="postgresql+asyncpg://user:password@host:5432/registry" \
  -e SYNC_DATABASE_URL="postgresql+psycopg2://user:password@host:5432/registry" \
  registry-service

# Run database migrations
docker exec registry-service alembic upgrade head
```

### Test the API

```bash
# Health check
curl http://localhost:8000/health

# Register an agent
curl -X POST http://localhost:8000/api/v1/agents \
  -H "Content-Type: application/json" \
  -d '{
    "agent": {
      "agentId": "test-agent-v1",
      "name": "Test Agent",
      "description": "A test agent",
      "capabilities": [{
        "taskName": "process_data",
        "description": "Process incoming data",
        "consumedEvent": "data.received",
        "producedEvents": ["data.processed"]
      }]
    }
  }'

# Query agents
curl http://localhost:8000/api/v1/agents
```

### Stop and Remove

```bash
docker stop registry-service && docker rm registry-service
```
