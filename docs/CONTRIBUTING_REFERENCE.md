# Soorma Core: Technical Reference for AI Agents

This document provides deep technical context for implementing features in the `soorma-core` repository. Refer to this AFTER the Action Plan has been approved.

## 🛠️ Component Workflows

### Python SDK (`sdk/python`)

* **Setup:** `cd sdk/python && poetry install`
* **Testing:** `poetry run pytest tests/ -v`
* **Linting:** `poetry run ruff check .`
* **Exports:** Primitives (Agent, Planner, Worker, Tool) must be exported in `soorma/__init__.py`.

### Control Plane Services

* **Registry:** `services/registry` (FastAPI + SQLite/Postgres)
* **Event Service:** `services/event-service` (FastAPI + NATS JetStream)
* **Memory Service:** `services/memory` (FastAPI + pgvector)

### Shared Models (`libs/soorma-common`)

* Use Pydantic v2 for all models.
* **Import Pattern:** `from soorma_common.models import EventDefinition`

## 🧪 Testing Guidelines

### Async Tests

```python
@pytest.mark.asyncio
async def test_feature():
    result = await some_async_function()
    assert result == expected
