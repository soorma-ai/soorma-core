# Memory Service

Persistent memory layer for autonomous agents in the Soorma platform. This service provides:

- **Semantic Memory**: Factual knowledge shared across tenant (RAG)
- **Episodic Memory**: User/Agent interaction history with temporal recall
- **Procedural Memory**: Dynamic prompts, rules, and skills
- **Working Memory**: Plan-scoped shared state for multi-agent collaboration

Implements the CoALA (Cognitive Architectures for Language Agents) framework with enterprise-grade multi-tenancy.

## Development Setup

### Prerequisites

⚠️ **PostgreSQL with pgvector extension is required** - Unlike other services that can use SQLite, the Memory Service requires PostgreSQL because:
- Vector embeddings for semantic search (core feature)
- Row Level Security (RLS) for multi-tenancy
- HNSW indexes for high-performance similarity search

```bash
# Quick start: PostgreSQL + pgvector via Docker
docker run -d --name postgres-pgvector \
  -e POSTGRES_USER=soorma \
  -e POSTGRES_PASSWORD=soorma \
  -e POSTGRES_DB=memory \
  -p 5432:5432 \
  pgvector/pgvector:pg16

# Install soorma-common first (from core/libs/soorma-common)
cd ../../libs/soorma-common
pip install -e .

# Install memory-service
cd ../../services/memory
pip install -e ".[dev]"

# Set up environment variables
export DATABASE_URL="postgresql+asyncpg://soorma:soorma@localhost:5432/memory"
export SYNC_DATABASE_URL="postgresql+psycopg2://soorma:soorma@localhost:5432/memory"
export OPENAI_API_KEY="sk-..."

# Run database migrations
alembic upgrade head
```

## Running the Service

```bash
# From core/services/memory/
uvicorn memory_service.main:app --reload --port 8002

# Or using Python directly
python -m memory_service.main
```

## API Endpoints

### Semantic Memory (Knowledge Base)

- `POST /api/v1/memory/semantic` - Ingest knowledge chunk
  - Body: `{ "content": "text", "metadata": {} }`
  - Automatically generates embeddings
- `GET /api/v1/memory/semantic/search?q=query&limit=5` - Search knowledge base
  - Returns: Top K relevant knowledge chunks

### Episodic Memory (Experience)

- `POST /api/v1/memory/episodic` - Log interaction
  - Body: `{ "agent_id": "researcher-1", "role": "assistant", "content": "...", "metadata": {} }`
- `GET /api/v1/memory/episodic/recent?agent_id=X&limit=10` - Recent history (context window)
- `GET /api/v1/memory/episodic/search?agent_id=X&q=query&limit=5` - Long-term recall

### Procedural Memory (Skills)

- `GET /api/v1/memory/procedural/context?agent_id=X&q=query&limit=3` - Fetch relevant skills
  - Returns: System prompts and few-shot examples matching the query

### Working Memory (Plan State)

- `PUT /api/v1/memory/working/{plan_id}/{key}` - Set state variable
  - Body: `{ "value": { "any": "json" } }`
- `GET /api/v1/memory/working/{plan_id}/{key}` - Get state variable

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `IS_PROD` | `false` | Production mode (disables docs) |
| `IS_LOCAL_TESTING` | `true` | Use default tenant for local dev |
| `DATABASE_URL` | (required) | Async PostgreSQL URL with asyncpg driver |
| `SYNC_DATABASE_URL` | (derived) | Sync PostgreSQL URL for Alembic |
| `OPENAI_API_KEY` | (required) | OpenAI API key for embeddings |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding model |
| `EMBEDDING_DIMENSIONS` | `1536` | Vector dimensions |
| `DEFAULT_TENANT_ID` | `00000000-0000-0000-0000-000000000000` | Local dev tenant |

## Docker

### Build

From the **soorma-core root** directory:

```bash
docker build -f services/memory/Dockerfile -t memory-service .
```

### Run (PostgreSQL)

```bash
# Start PostgreSQL with pgvector
docker run -d --name postgres-pgvector \
  -e POSTGRES_USER=soorma \
  -e POSTGRES_PASSWORD=soorma \
  -e POSTGRES_DB=memory \
  -p 5432:5432 \
  pgvector/pgvector:pg16

# Start the memory service
docker run -d --name memory-service -p 8002:8002 \
  -e DATABASE_URL="postgresql+asyncpg://soorma:soorma@host.docker.internal:5432/memory" \
  -e SYNC_DATABASE_URL="postgresql+psycopg2://soorma:soorma@host.docker.internal:5432/memory" \
  -e OPENAI_API_KEY="sk-..." \
  memory-service

# Run database migrations
docker exec memory-service alembic upgrade head

# Verify it's running
curl http://localhost:8002/health
```

## Multi-Tenancy & Security

### Local Development (Single Tenant)

For local development without an Identity Service:
- A default tenant (`00000000-0000-0000-0000-000000000000`) is automatically created
- All requests without authentication use this tenant
- Set `IS_LOCAL_TESTING=true` (default)

### Production (Multi-Tenant)

Authentication is enforced via JWT tokens:
1. Client includes JWT in `Authorization: Bearer <token>` header
2. Middleware extracts `tenant_id` and `user_id` from token claims
3. PostgreSQL session variables are set: `app.current_tenant`, `app.current_user`
4. Row Level Security (RLS) policies enforce isolation at database level

**Key Security Properties:**
- Application bugs cannot leak data between tenants
- Tenant isolation is enforced by PostgreSQL, not application code
- User-level personalization for episodic and procedural memories
- Tenant-wide semantic memory with optional user overrides

## Architecture

See [ARCHITECTURE.md](./ARCHITECTURE.md) for detailed design documentation, including:
- CoALA framework implementation
- Database schema and indexes
- RLS policy design
- Replica table strategy
- Embedding generation pipeline

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=memory_service --cov-report=html

# Run specific test file
pytest tests/test_semantic_memory.py -v
```

## Development

```bash
# Lint code
ruff check .

# Format code
ruff format .

# Type checking
mypy src/
```

## License

MIT - See [LICENSE](../../LICENSE) in the repository root.
