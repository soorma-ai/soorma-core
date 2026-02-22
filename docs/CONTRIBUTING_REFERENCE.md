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
```

---

## 📝 Git Workflow

### Commit Message Format

**CRITICAL:** Keep commit messages ≤15 lines total to prevent terminal execution issues.

**Format:** `type(scope): subject`

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `refactor`: Code restructuring
- `test`: Add/update tests
- `docs`: Documentation only
- `chore`: Build/tooling changes

**Scopes:**
- `sdk`: SDK changes
- `common`: soorma-common library
- `memory`: Memory Service
- `registry`: Registry Service
- `event`: Event Service
- `tracker`: Tracker Service
- `examples`: Example code

### Examples

**✅ GOOD - Succinct single-line commits:**
```bash
git commit -m "feat(sdk): add TrackerClient wrapper to PlatformContext"
git commit -m "test(common): add 11 tests for Tracker response DTOs"
git commit -m "fix(memory): handle 404 errors in semantic search"
```

**✅ GOOD - Multi-line with `-m` flags (≤15 lines total):**
```bash
git commit \
  -m "feat(sdk): add Tracker Service client integration" \
  -m "Layer 1: TrackerServiceClient with 10 tests" \
  -m "Layer 2: TrackerClient wrapper with 6 tests" \
  -m "Two-layer architecture compliance enforced"
```

**❌ BAD - Long message in single string (causes terminal issues):**
```bash
# This wraps in terminal and causes execution errors
git commit -m "feat(sdk): add Tracker Service client integration

Layer 1 - TrackerServiceClient (low-level HTTP client):
- Implement 7 query methods with headers
- Add 10 unit tests...
[20+ lines of text]"
```

**Subject Line Rules:**
- ≤72 characters
- Imperative mood ("add" not "added")
- No period at end
- Lowercase after colon

**Body Guidelines:**
- Use bullet points
- Each point on separate `-m` flag
- Focus on "what" and "why", not "how"
- Reference issue/plan if applicable
