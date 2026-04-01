# Technology Stack

## Programming Languages
- Python 3.11+ - SDK and backend services.
- TypeScript/JavaScript (limited utility and support scripts) - ancillary tooling.

## Frameworks and Libraries
- FastAPI - HTTP API services.
- Pydantic v2 - contract validation.
- SQLAlchemy async - database interactions.
- httpx - async SDK HTTP client.

## Data and Transport
- PostgreSQL - primary data store and tenancy-aware RLS enforcement.
- pgvector - semantic-memory indexing/search support.
- NATS/Kafka adapters - event transport pathways.

## Build and Development
- Python package tooling per package domain.
- Local service startup orchestration via repository dev tooling.

## Testing
- pytest (service and SDK tests).
- integration examples and choreography validation flows under `examples/`.