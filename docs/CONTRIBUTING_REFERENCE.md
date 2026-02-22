# Soorma Core: Technical Reference for Contributors

**Purpose:** Technical cookbook for implementation—CLI commands, testing syntax, import patterns, and component-specific workflows.

**When to use:** During **Phase 3 (Implementation)** when you need actual commands/syntax to execute the approved Action Plan.

**Documentation Hierarchy:**
```
AGENT.md (Constitution) → Read first for requirements
  ↓
SESSION_INITIALIZATION.md (Workflow Process) → Use for planning & TDD workflow
  ↓ Phase 3: Implementation starts
  ↓
CONTRIBUTING_REFERENCE.md (YOU ARE HERE) → Technical syntax & commands
```

**Related Guides:**
- **Process & Workflow:** [SESSION_INITIALIZATION.md](SESSION_INITIALIZATION.md) - Master/Action Plans, TDD workflow, checklists
- **Architecture Patterns:** [ARCHITECTURE_PATTERNS.md](ARCHITECTURE_PATTERNS.md) - SDK design patterns (read in Phase 0)
- **Constitution:** [../AGENT.md](../AGENT.md) - Core developer requirements

---

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
