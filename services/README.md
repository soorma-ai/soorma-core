# Soorma Core Services

This directory contains the microservices that power the Soorma platform.

## Services

### Registry Service
**Port:** 8000  
**Purpose:** Event and Agent Registry - service discovery and capability registration  
**Tech:** FastAPI + SQLite (dev) / PostgreSQL (prod)

Key features:
- Agent registration with TTL-based lifecycle tracking
- Event definition registry with schemas
- Discovery API for autonomous choreography
- Health monitoring and cleanup

[Documentation →](./registry/README.md)

### Event Service
**Port:** 8001  
**Purpose:** Event bus proxy/adapter - decouples agents from message infrastructure  
**Tech:** FastAPI + NATS JetStream

Key features:
- Pub/Sub event distribution
- SSE streaming for real-time consumption
- Queue groups for load balancing
- Multiple backend support (NATS, Google Pub/Sub, Kafka)

[Documentation →](./event-service/README.md)

### Memory Service
**Port:** 8002  
**Purpose:** Persistent memory layer for autonomous agents (CoALA framework)  
**Tech:** FastAPI + PostgreSQL + pgvector

Key features:
- Semantic Memory: Knowledge base with vector search (RAG)
- Episodic Memory: User/Agent interaction history with temporal recall
- Procedural Memory: Dynamic prompts, rules, and skills
- Working Memory: Plan-scoped shared state for multi-agent collaboration
- Native multi-tenancy with Row Level Security
- Automatic embedding generation

[Documentation →](./memory/README.md)

### Gateway (Planned)
**Port:** TBD  
**Purpose:** API Gateway for unified external access

## Development

All services follow a consistent structure:

```
service-name/
├── src/
│   └── service_name/        # Python package
│       ├── api/v1/          # API routes
│       ├── core/            # Config, database
│       ├── models/          # Data models
│       ├── crud/            # Database operations
│       └── services/        # Business logic
├── tests/                   # Test suite
├── alembic/                 # Database migrations
├── pyproject.toml           # Dependencies
├── Dockerfile               # Container build
├── README.md                # Service documentation
└── CHANGELOG.md             # Version history

```

## Running Services Locally

### Individual Service

```bash
cd services/<service-name>
pip install -e ".[dev]"
alembic upgrade head  # Run migrations
uvicorn <service_name>.main:app --reload --port <PORT>
```

### All Services (Docker Compose)

From the `soorma-core` root:

```bash
soorma dev --build  # Builds services from source for bleeding edge
```

## Service Communication

Services communicate through well-defined APIs:

- **Registry ← Agents**: Agents register capabilities on startup
- **Event Service ← Agents**: Agents publish/subscribe to events
- **Memory Service ← Agents**: Agents store/retrieve memories
- **Registry → Agents**: Dynamic capability discovery

## Versioning

All services follow [Semantic Versioning](https://semver.org/) and are kept in sync with the SDK:

- Current version: **0.5.0**
- See individual CHANGELOG.md files for release notes

## License

MIT - See [LICENSE](../LICENSE) in the repository root.
