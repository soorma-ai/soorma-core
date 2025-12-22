# AI Assistant Instructions (Copilot/Cursor/Claude)

This document provides essential context for AI assistants working on the `soorma-core` repository. Read this first before making any changes.

---

## 🎯 Quick Start Checklist

Before starting any task:
1. ✅ Read `README.md` for project overview and getting started guide
2. ✅ Check the relevant CHANGELOG.md for recent changes
3. ✅ Understand the DisCo architecture (see below)
4. ✅ Follow TDD - write tests for every feature change
5. ✅ This is an OPEN SOURCE project - everything here is MIT licensed

---

## 📁 Repository Structure

```
soorma-core/              ← Public open-source repository (MIT License)
├── sdk/python/           ← The 'soorma-core' PyPI package
│   ├── soorma/           ← Main SDK code
│   ├── tests/            ← SDK test suite
│   └── CHANGELOG.md      ← SDK version history
├── libs/                 ← Shared libraries
│   └── soorma-common/    ← Common Pydantic models & DTOs
├── services/             ← Open source microservices
│   ├── registry/         ← Agent & Event registry service
│   ├── event-service/    ← Event bus proxy/adapter
│   └── gateway/          ← API gateway (planned)
├── examples/             ← Example AI agent implementations
│   ├── hello-world/      ← Basic agent example
│   └── research-advisor/ ← Advanced autonomous choreography example
└── iac/                  ← Infrastructure as Code (Terraform/Helm)
```

---

## ⚠️ Critical Rules

### 1. This Repository is PUBLIC

**All code here is visible to everyone under MIT License.**

- 🚫 **NEVER** commit secrets, API keys, or credentials
- 🚫 **NEVER** commit proprietary or closed-source code
- 🚫 **NEVER** include non-MIT compatible dependencies
- ✅ All code must be open source and MIT compatible
- ✅ Assume everything will be reviewed by the public community

### 2. License Consistency

| Component | License | File |
|-----------|---------|------|
| Everything | MIT | `LICENSE` |

All code, dependencies, and files must be MIT-compatible.

### 3. Test-Driven Development (TDD)

**Every feature change MUST include tests.**

```bash
# Python SDK tests
cd sdk/python
pytest tests/ -v

# Registry service tests  
cd services/registry
pytest test/ -v

# Event service tests
cd services/event-service
pytest test/ -v
```

Test coverage expectations:
- Unit tests for all public functions/methods
- Integration tests for API endpoints
- Example code must be working and tested

---

## 🏗️ Architecture Principles

### DisCo (Distributed Cognition) Pattern

Soorma implements event-driven agent choreography:

1. **Planner** - Strategic reasoning agent, orchestrates via LLM reasoning
2. **Worker** - Domain-specific agents that react to events
3. **Tool** - Atomic, stateless capabilities

**Key Innovation:** Autonomous choreography without hardcoded workflow rules.
- Agents discover available events from the Registry at runtime
- LLM reasons about event metadata to decide next actions
- Workflows emerge from agent decisions, not predefined sequences

### The Control Plane Services

| Service | Tech | Role |
|---------|------|------|
| Event Service | FastAPI + NATS | Event bus proxy/adapter |
| Registry | FastAPI + SQLite/Postgres | Agent/Event discovery & registration |

### Development Pattern

The SDK includes the `soorma` CLI for local development:
```bash
soorma dev          # Start local dev stack (Registry + Event Service + NATS)
soorma init <name>  # Scaffold new agent project
```

Services run in Docker while agent code runs natively on the host for fast iteration.

---

## 🛠️ Development Workflows

### Python SDK (`sdk/python`)

```bash
# Setup
cd sdk/python
poetry install

# Run tests
poetry run pytest tests/ -v

# Lint
poetry run ruff check .

# Build
poetry build

# Install locally for testing
pip install -e .
```

The SDK provides:
- Agent primitives: `Agent`, `Planner`, `Worker`, `Tool`
- Registry client: `RegistryClient`
- Event toolkit: `EventToolkit` (AI-powered event discovery)
- CLI: `soorma` command-line interface

### Registry Service (`services/registry`)

```bash
# Setup
cd services/registry
pip install -e .

# Run tests
pytest test/ -v

# Run locally
uvicorn src.app.main:app --reload --port 8000

# Database migrations
alembic upgrade head
```

### Event Service (`services/event-service`)

```bash
# Setup
cd services/event-service
pip install -e .

# Run tests
pytest test/ -v

# Run locally (requires NATS)
uvicorn src.app.main:app --reload --port 8001
```

---

## 📦 Dependencies & Imports

### Shared Libraries

Use `soorma-common` for shared Pydantic models:
```python
from soorma_common.models import EventDefinition, AgentProfile
```

### Internal Imports (within SDK)

```python
# From SDK to common
from soorma_common.models import SomeModel

# Within SDK
from soorma.registry.client import RegistryClient
from soorma.ai.event_toolkit import EventToolkit
from soorma.context import PlatformContext
```

### Example Imports

```python
# In examples
from soorma import Worker, Planner
from soorma.context import PlatformContext
from litellm import completion  # For LLM integration
```

---

## 🧪 Testing Guidelines

### Unit Tests

```python
import pytest

def test_feature():
    """Test description."""
    result = some_function()
    assert result == expected
```

### Async Tests

```python
import pytest

@pytest.mark.asyncio
async def test_async_feature():
    """Test async functionality."""
    result = await some_async_function()
    assert result == expected
```

### Integration Tests

Test services with real dependencies:
```python
@pytest.fixture
async def registry_client():
    """Fixture for registry client with test database."""
    client = RegistryClient(base_url="http://localhost:8000")
    yield client
    # cleanup

async def test_register_agent(registry_client):
    """Test agent registration."""
    response = await registry_client.register_agent(...)
    assert response.status == "registered"
```

### Example Tests

All examples in `examples/` should be functional and documented:
- Include README.md with setup and run instructions
- Use mock responses when API keys are not available
- Test basic functionality without requiring external services

---

## 🔄 Version Management

### Semantic Versioning

We follow [Semver](https://semver.org/): `MAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes to public API
- **MINOR**: New features, backward compatible
- **PATCH**: Bug fixes, backward compatible

### Release Process

1. Update version in respective `pyproject.toml`
2. Update CHANGELOG.md with release notes
3. Commit changes: `git commit -m "chore: bump version to X.Y.Z"`
4. Create tag: `git tag vX.Y.Z && git push --tags`
5. GitHub Actions will publish to PyPI

### Version Alignment

All components should be kept in sync:
- `sdk/python` - Main SDK version
- `libs/soorma-common` - Usually matches SDK
- `services/registry` - Matches SDK major.minor
- `services/event-service` - Matches SDK major.minor

---

## 📝 Code Style

### Python

- Python 3.11+ compatibility
- Use type hints everywhere
- Async/await for all I/O operations
- Pydantic v2 for data models
- Follow PEP 8 style guide

### Documentation

- Docstrings for all public functions/classes
- Type hints in function signatures
- Examples in docstrings where helpful
- README.md in all major directories

### Commit Messages

Follow conventional commits:
```
feat(sdk): add autonomous choreography to planner
fix(registry): handle concurrent registration race condition
docs: update architecture documentation
test(event-service): add SSE streaming tests
chore: bump version to 0.4.0
```

Types: `feat`, `fix`, `docs`, `test`, `chore`, `refactor`, `perf`

---

## 🎨 Example Development

### Research Advisor Example

The `examples/research-advisor/` demonstrates advanced patterns:

**Key Files:**
- `planner.py` - LLM-powered orchestrator with autonomous choreography
- `researcher.py` - Web research worker (DuckDuckGo + LLM)
- `advisor.py` - Content drafting worker
- `validator.py` - Fact-checking worker
- `llm_utils.py` - Multi-provider LLM support

**Design Principles:**
1. **No Hardcoded Workflows** - LLM reasons from event metadata
2. **Dynamic Discovery** - Events discovered from Registry at runtime
3. **Circuit Breakers** - Prevent infinite loops and stuck states
4. **Multi-Provider LLM** - Works with OpenAI, Anthropic, Gemini, etc.

When updating examples:
- Keep them working and well-documented
- Use environment variables for configuration
- Provide fallback/mock behavior when APIs not available
- Update README.md with any new dependencies or setup steps

---

## 🔗 Component Relationships

### SDK → Services

The SDK talks to services via HTTP APIs:
```python
# SDK uses Registry
registry_client = RegistryClient(base_url="http://localhost:8000")
await registry_client.register_agent(...)

# SDK uses Event Service
context.bus.publish(event_type="...", topic="...", data={})
```

### Services → Libraries

Services use `soorma-common` for shared models:
```python
# In registry service
from soorma_common.models import AgentRegistrationRequest
from soorma_common.enums import EventTopic
```

### Examples → SDK

Examples use the SDK:
```python
# In example code
from soorma import Worker, Planner
from soorma.context import PlatformContext

worker = Worker(name="my-worker", ...)
```

---

## 💡 Common Tasks

### Adding a New Agent Primitive

1. Define in `sdk/python/soorma/base.py` or new module
2. Add tests in `sdk/python/tests/`
3. Update `sdk/python/soorma/__init__.py` exports
4. Document in SDK README
5. Create example in `examples/`

### Adding a New Registry Endpoint

1. Define route in `services/registry/src/app/api/v1/`
2. Add data model in `libs/soorma-common/src/soorma_common/models/`
3. Update client in `sdk/python/soorma/registry/client.py`
4. Add tests for all three layers
5. Update API documentation

### Adding Multi-Provider Support

When adding LLM/API support:
1. Use environment variables for API keys
2. Provide fallback behavior when keys are missing
3. Document all supported providers in README
4. Test with at least 2 providers
5. Consider creating a utility module (like `llm_utils.py`)

### Creating a New Example

1. Create directory in `examples/<name>/`
2. Add `README.md` with:
   - What the example demonstrates
   - Prerequisites and setup
   - How to run
   - Expected output
3. Include working code with clear comments
4. Add `requirements.txt` or list dependencies
5. Test that it works from a fresh environment

---

## 🐛 Debugging Tips

### Local Development

```bash
# Start services with docker
soorma dev

# Check service health
curl http://localhost:8000/health  # Registry
curl http://localhost:8001/health  # Event Service

# View logs
docker logs soorma-registry
docker logs soorma-event-service
docker logs soorma-nats
```

### Common Issues

**Registry Connection Failed:**
- Check if `soorma dev` is running
- Verify port 8000 is available
- Check Docker container status

**Event Not Received:**
- Verify topic matches between publisher and subscriber
- Check agent is registered before publishing
- Look for NATS connection errors

**Import Errors:**
- Ensure packages are installed: `pip install -e .`
- Check Python path includes the package
- Verify dependencies are up to date

---

## 📚 Documentation Standards

### README Files

Every major component needs a README with:
1. **Purpose** - What this component does
2. **Installation** - How to install/setup
3. **Usage** - Basic usage examples
4. **API Reference** - Key functions/classes
5. **Development** - How to contribute

### CHANGELOG Files

Track changes in CHANGELOG.md:
- Follow [Keep a Changelog](https://keepachangelog.com/) format
- Use Semantic Versioning
- Include date for each release
- Categories: Added, Changed, Deprecated, Removed, Fixed, Security

### Code Comments

```python
# Good comments explain WHY, not WHAT
# ✅ Circuit breaker: prevent infinite loops in autonomous agents
if action_count > MAX_ACTIONS:
    return complete_workflow()

# ❌ Don't just describe the code
# Increment counter
action_count += 1
```

---

## 🤝 Contributing Guidelines

### Before Submitting PR

1. ✅ All tests pass: `pytest tests/ -v`
2. ✅ Code is formatted: `ruff check .`
3. ✅ CHANGELOG updated with your changes
4. ✅ Documentation updated if needed
5. ✅ Commit messages follow conventional commits

### PR Description Template

```markdown
## Changes
- Brief description of changes

## Type
- [ ] Feature
- [ ] Bug fix
- [ ] Documentation
- [ ] Refactor

## Testing
- How was this tested?
- Any manual testing steps?

## Breaking Changes
- Any breaking changes?
```

---

## 🎯 Current Focus Areas (Q1 2025)

Based on recent commits and development:

1. **Autonomous Choreography** - LLM-driven agent coordination without hardcoded workflows
2. **Multi-Provider LLM Support** - OpenAI, Anthropic, Gemini, Azure, Together AI, Groq
3. **Event Discovery** - Dynamic event discovery from Registry for flexible workflows
4. **Circuit Breakers** - Safeguards against infinite loops and stuck states
5. **Examples & Documentation** - Rich examples demonstrating DisCo patterns

---

**Remember:** 
- This is an open-source project - write code you'd be proud to show the world
- Favor simplicity over complexity
- Document thoroughly - future contributors will thank you
- Test extensively - bugs in examples hurt adoption
- Think about developer experience - make it easy and delightful to use

For questions, check existing documentation or examples first. The `research-advisor` example demonstrates most advanced patterns.
