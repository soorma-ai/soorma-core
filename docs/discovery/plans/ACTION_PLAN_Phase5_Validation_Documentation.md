# Action Plan: Phase 5 — Validation & Documentation (SOOR-DISC-P5)

**Status:** � In Progress (T5 next — example 12)  
**Parent Plan:** [MASTER_PLAN_Enhanced_Discovery.md](MASTER_PLAN_Enhanced_Discovery.md)  
**Phase:** 5 of 5  
**Refactoring Tasks:** RF-SDK-007 (final verification), RF-SDK-017 (examples), End-to-End Validation  
**Estimated Duration:** 3–4 days (24–30 hours)  
**Target Release:** v0.8.1  
**Created:** March 2, 2026  
**Approved:** (awaiting developer approval)  
**Prerequisites:** Phase 1 ✅ Complete | Phase 2 ✅ Complete | Phase 3 ✅ Complete | Phase 4 ✅ Complete

---

## Architecture Pattern Compliance (Step 0 Gateway)

Per AGENT.md Section 2 (Step 0), the following ARCHITECTURE_PATTERNS.md sections have been verified before planning:

| Section | Pattern | Application in Phase 5 |
|---------|---------|------------------------|
| §1 Auth | `X-Tenant-ID` custom header (v0.7.x) | All example agents use `SOORMA_DEVELOPER_TENANT_ID` env var. No hardcoded credentials. |
| §2 Two-Layer SDK | `RegistryClient` is the agent-facing wrapper; `context.registry` exposes it | All examples use `context.registry.discover()`, `context.registry.get_schema()`, `context.registry.register_schema()`. Zero direct HTTP calls in example code. |
| §3 Event Choreography | Explicit `response_event`, no inferred names | Example 11 passes `response_event` explicitly in payload. Example 12 `EventSelector.publish_decision()` carries explicit `correlation_id`. Example 13 A2A gateway maps `task.id` to `response_event`. |
| §4 Multi-tenancy | PostgreSQL RLS enforces tenant isolation | Integration tests explicitly verify cross-tenant isolation. Examples use distinct `TENANT_A` / `TENANT_B` UUIDs in isolation test cases. |
| §5 State Management | N/A | Examples 11–13 are stateless or use existing plan-context patterns. |
| §6 Error Handling | SDK raises → wrapper propagates | Examples demonstrate graceful failure (empty `discover()` result, `EventSelectionError` retry). |
| §7 Testing | Unit: mocked HTTP; Integration: live services with docker-compose | End-to-end integration tests in `tests/integration/` use docker-compose stack (Registry + NATS + Tracker). |

**Self-Check Answers:**
- **Why can't example code import `RegistryClient` directly?** `RegistryClient` is exposed exclusively through `context.registry`. Direct import bypasses the authentication injection (`X-Tenant-ID`), bypasses the abstraction that hides the service URL, and teaches patterns that would break when the auth model migrates to JWT in v0.8.0+.
- **Difference between service endpoint and wrapper method?** A service endpoint is an HTTP route on the Registry Service backend (e.g., `GET /v1/agents/discover`). A wrapper method is the Python API in `RegistryClient` that calls it (e.g., `context.registry.discover(requirements=["web_search"])`). The wrapper injects tenant headers, handles HTTP errors, and returns typed Pydantic models.

---

## 1. Requirements & Core Objective

### Phase Objective

Validate the complete Stage 5 implementation through working examples, end-to-end integration tests, and comprehensive documentation updates. This phase makes the discovery system developer-ready by demonstrating three distinct use-cases:

1. **LLM-Based Dynamic Discovery** — ChoreographyPlanner finds agents dynamically using `discover()`
2. **EventSelector Intelligent Routing** — Natural language routing with `EventSelector` 
3. **A2A Gateway Interoperability** — External HTTP clients invoke Soorma agents via A2A protocol

### Acceptance Criteria

**Examples:**
- [ ] `examples/11-discovery-llm/` runs end-to-end: planner discovers worker, generates payload from schema, publishes event
- [ ] `examples/12-event-selector/` runs end-to-end: ticket router selects correct worker via LLM
- [ ] `examples/13-a2a-gateway/` runs end-to-end: external HTTP request → A2A Agent Card → internal event → A2A response
- [ ] All examples use `context.registry.*` exclusively (zero direct `RegistryClient` imports)
- [ ] All examples have `README.md` with quickstart, expected output, and pattern description
- [ ] All examples have `.env.example` with required environment variables

**Integration Tests:**
- [ ] End-to-end discovery flow: register → discover → invoke → response (25+ tests)
- [ ] Multi-tenant isolation verified: cross-tenant queries return empty results
- [ ] Schema versioning: `v1.0.0` and `v2.0.0` coexist without conflict
- [ ] A2A gateway round-trip: HTTP POST → internal event → HTTP response

**Documentation:**
- [ ] `docs/discovery/README.md` updated with Phase 5 status, new patterns, examples 11–13
- [ ] `docs/discovery/ARCHITECTURE.md` updated with complete component map (all 5 phases)
- [ ] `docs/ARCHITECTURE_PATTERNS.md` Section 9 checklist updated for discovery pattern
- [ ] `CHANGELOG.md` (root, SDK, soorma-common, Registry) updated with v0.8.1 entries
- [ ] `examples/README.md` updated with examples 11–13 in learning path table

### Refactoring Tasks Addressed

| Task ID | Description | Status in Phase 5 |
|---------|-------------|-------------------|
| RF-SDK-007 | Event registration tied to startup (schema references) | Final verification — all examples register schemas at startup before agent loop |
| RF-SDK-017 | EventSelector examples (deferred documentation from Phase 3) | ✅ New: Example 12 demonstrates full EventSelector routing pattern |
| (none) | End-to-end validation | New integration test suite covering all Phase 1–4 features together |

---

## 2. Technical Design

### Component Map

| Component | File | Change Type |
|-----------|------|-------------|
| Example 11 | `examples/11-discovery-llm/` | New example (planner + worker + schema_registration + start.sh) |
| Example 12 | `examples/12-event-selector/` | New example (router + 3 workers + start.sh) |
| Example 13 | `examples/13-a2a-gateway/` | New example (gateway service + internal agent + start.sh) |
| Integration Tests | `sdk/python/tests/integration/test_e2e_discovery.py` | New test file (lives in SDK test suite) |
| Integration Tests | `sdk/python/tests/integration/test_multi_tenant_isolation.py` | New test file (lives in SDK test suite) |
| Integration Tests | `sdk/python/tests/integration/test_a2a_gateway_roundtrip.py` | New test file (lives in SDK test suite) |
| Feature README | `docs/discovery/README.md` | Update (Phase 5 status, new patterns, examples) |
| Feature ARCHITECTURE | `docs/discovery/ARCHITECTURE.md` | Update (complete component map, all phases done) |
| Global patterns | `docs/ARCHITECTURE_PATTERNS.md` | Update (Section 9: discovery checklist) |
| Root CHANGELOG | `CHANGELOG.md` | Update (v0.8.1 entry) |
| Examples README | `examples/README.md` | Update (examples 11–13 in learning path) |

### SDK Layer Verification

> Phase 5 adds no new service methods. All wrappers are verified complete from Phase 3.
> **One SDK gap identified below (T0) must be closed before examples can be written correctly.**

- [x] **`context.registry.discover(requirements, include_schemas)` → `List[DiscoveredAgent]`** — Implemented in Phase 3 ✅
- [x] **`context.registry.get_schema(schema_name, version)` → `Optional[PayloadSchema]`** — Implemented in Phase 3 ✅
- [x] **`context.registry.register_schema(schema)` → `PayloadSchemaResponse`** — Implemented in Phase 2 ✅
- [x] **`context.registry.deregister(agent_id)` → `None`** — Implemented in Phase 3 ✅
- [x] **`EventSelector.select_event(state)` → `EventDecision`** — Implemented in Phase 3 ✅
- [x] **`A2AGatewayHelper.agent_to_card(agent, gateway_url)` → `A2AAgentCard`** — Implemented in Phase 3 ✅
- [x] **`A2AGatewayHelper.task_to_event(task, event_type)` → `ActionRequestEvent`** — Implemented in Phase 3 ✅
- [x] **`A2AGatewayHelper.event_to_response(event, task_id)` → `A2ATaskResponse`** — Implemented in Phase 3 ✅

**SDK Gap (T0):** `_register_with_registry()` in `agents/base.py` auto-registers `event_definitions` and the `AgentDefinition` but never calls `register_schema`. An agent that declares a `payload_schema_name` on its `AgentCapability` cannot make that schema discoverable today without calling `ctx.registry.register_schema()` manually — which violates the two-layer principle (agents should not do plumbing). Fix: extend `_register_with_registry()` to auto-register any inline `json_schema` bodies attached to capabilities. After T0, workers simply declare their schema inline; the SDK handles registration.

**Conclusion:** T0 closes the gap. After that, examples need no explicit schema-registration calls.

**Examples compliance check:**
- [ ] Example 11: Uses `context.registry.discover()` — NOT `RegistryClient` directly
- [ ] Example 12: Uses `EventSelector(context=ctx, ...)` — NOT raw LiteLLM calls, NOT Jinja2 prompt templates
- [ ] Example 13: Uses `A2AGatewayHelper` for conversions — NOT raw dict manipulation
- [ ] No example imports `from soorma.registry.client import RegistryClient`
- [ ] Integration tests reside in `sdk/python/tests/integration/` — NOT a top-level `tests/` dir

---

## 3. Task Tracking Matrix

### Task Sequence

```
[T0: SDK — auto-register schemas in _register_with_registry()]
        ↓
[T1: Example 11 Structure + start.sh]
        ↓
[T2: Example 11 Worker]
        ↓
[T3: Example 11 Planner]
        ↓
[T4: Example 11 README + end-to-end ./start.sh run]
        ↓
[T5: Example 12 Structure + start.sh]
        ↓
[T6: Example 12 Workers]
        ↓
[T7: Example 12 Router]
        ↓
[T8: Example 12 README + end-to-end ./start.sh run]
        ↓
[T9: Example 13 Structure + start.sh]
        ↓
[T10: Example 13 Gateway Service]
        ↓
[T11: Example 13 Internal Agent]
        ↓
[T12: Example 13 README + end-to-end ./start.sh run]
        ↓
[T13: Integration Tests — E2E Discovery (sdk/python/tests/integration/)]
        ↓
[T14: Integration Tests — Multi-Tenant (sdk/python/tests/integration/)]
        ↓
[T15: Integration Tests — A2A Round-Trip (sdk/python/tests/integration/)]
        ↓
[T16: Documentation Updates]
        ↓
[T17: CHANGELOG Entries]
        ↓
[T18: Examples README Update]
```

### Task Tracking Matrix

| Task | Description | Files Affected | Estimate | TDD Phase | Status |
|------|-------------|----------------|----------|-----------|--------|
| **T0** | Extend `_register_with_registry()` to auto-register inline `json_schema` bodies from `AgentCapability.consumed_event` — agent declares schema inline, SDK calls `register_schema`; delete `schema_registration.py` standalone script concept | `sdk/python/soorma/agents/base.py`, `sdk/python/tests/test_agents.py` | 1.5h | RED → GREEN | ✅ |
| **T1** | Scaffold `examples/11-discovery-llm/` — `.env.example`, `requirements.txt`, stub `*.py`, `start.sh`, `README.md` stub | `examples/11-discovery-llm/` | 30m | N/A | ✅ |
| **T2** | Implement `worker.py` — declares inline `json_schema` on `AgentCapability.consumed_event`; SDK auto-registers schema + agent via `_register_with_registry()`. No explicit `ctx.registry.register_schema()` call. | `examples/11-discovery-llm/worker.py` | 1h | STUB → GREEN | ✅ |
| **T3** | Implement `planner.py` — `ctx.registry.discover()`, `ctx.registry.get_schema()`, `ctx.ai.generate_payload()` (NO manual prompt), `goal.dispatch()` with explicit `response_event`; fixed `plan_id=correlation_id` for goal metadata scope | `examples/11-discovery-llm/planner.py` | 2h | STUB → GREEN | ✅ |
| **T4** | Complete `README.md` with expected output; verify `./start.sh` runs end-to-end | `examples/11-discovery-llm/README.md`, `start.sh` | 45m | N/A | ✅ |
| **T5** | Scaffold `examples/12-event-selector/` — stub `*.py`, `start.sh`, `.env.example`, `README.md` stub. No `prompts/` dir. | `examples/12-event-selector/` | 30m | N/A | 📋 |
| **T6** | Implement three workers using `ctx.registry.register_agent()` at startup; each handles its event type | `examples/12-event-selector/technical_worker.py`, `billing_worker.py`, `escalation_worker.py` | 1.5h | STUB → GREEN | 📋 |
| **T7** | Implement `router.py` — `EventSelector(context=ctx, topic=..., model=...)`, `selector.select_event(state={...})`, `selector.publish_decision(...)`. Zero Jinja2, zero raw LiteLLM. | `examples/12-event-selector/router.py` | 1h | STUB → GREEN | 📋 |
| **T8** | Complete `README.md` with expected output; verify `./start.sh` routes tickets correctly | `examples/12-event-selector/README.md`, `start.sh` | 45m | N/A | 📋 |
| **T9** | Scaffold `examples/13-a2a-gateway/` — stub `*.py`, `start.sh`, `.env.example`, `README.md` stub | `examples/13-a2a-gateway/` | 30m | N/A | 📋 |
| **T10** | Implement `gateway_service.py` — FastAPI, `A2AGatewayHelper.agent_to_card()`, `A2AGatewayHelper.task_to_event()`, `ctx.bus.request()`, `A2AGatewayHelper.event_to_response()` | `examples/13-a2a-gateway/gateway_service.py` | 2h | STUB → GREEN | 📋 |
| **T11** | Implement `internal_agent.py` — standard `ctx.registry.register_agent()` at startup, handles event, publishes response | `examples/13-a2a-gateway/internal_agent.py` | 1h | STUB → GREEN | 📋 |
| **T12** | Complete `README.md` with expected output; verify `./start.sh` completes A2A round-trip | `examples/13-a2a-gateway/README.md`, `start.sh` | 45m | N/A | 📋 |
| **T13** | Write integration tests: end-to-end discovery flow (register → discover → invoke → response) | `sdk/python/tests/integration/test_e2e_discovery.py` | 2h | RED → GREEN | 📋 |
| **T14** | Write integration tests: multi-tenant isolation (cross-tenant queries return empty) | `sdk/python/tests/integration/test_multi_tenant_isolation.py` | 1h | RED → GREEN | 📋 |
| **T15** | Write integration tests: A2A gateway round-trip (HTTP → event → HTTP) | `sdk/python/tests/integration/test_a2a_gateway_roundtrip.py` | 1h | RED → GREEN | 📋 |
| **T16** | Update `docs/discovery/README.md`, `docs/discovery/ARCHITECTURE.md`, `docs/ARCHITECTURE_PATTERNS.md` | Docs files | 2h | N/A | 📋 |
| **T17** | Write `CHANGELOG.md` entries (root, SDK, soorma-common, Registry) | 4x `CHANGELOG.md` | 1h | N/A | 📋 |
| **T18** | Update `examples/README.md` with examples 11–13 in learning path table | `examples/README.md` | 30m | N/A | 📋 |

**48-Hour Filter:** Total estimated: 23.5h (< 48h threshold). No FDE simplification required. Full scope proceeds.

---

## 4. Technical Design: Examples

### Example 11: LLM-Based Dynamic Discovery

**File structure:**
```
examples/11-discovery-llm/
├── README.md
├── .env.example
├── requirements.txt
├── start.sh                   # Starts all agents (workers first, then planner) — same pattern as examples 09/10
├── worker.py                  # Research worker: declares inline json_schema on capability, SDK handles registration
└── planner.py                 # ChoreographyPlanner: discovers, fetches schema, LLM → payload
```

> **No per-example unit test directory.** Examples are runnable demonstrations, not test suites. Integration tests for discovery behaviour live in `sdk/python/tests/integration/` (see §5).

**Key patterns demonstrated:**
```python
# worker.py — schema declared inline on the capability; SDK auto-registers it at startup
from soorma import Worker
from soorma_common import AgentCapability, EventDefinition

worker = Worker(
    name="research-worker",
    capabilities=[
        AgentCapability(
            task_name="web_research",
            description="Performs structured web research",
            consumed_event=EventDefinition(
                event_name="research.requested",
                topic="action-requests",
                payload_schema_name="research_request_v1",
                # Inline schema body — SDK calls register_schema() automatically
                payload_schema={
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string", "description": "Research topic"},
                        "max_results": {"type": "integer", "default": 5},
                    },
                    "required": ["topic"],
                },
            ),
            produced_events=[...],
        )
    ],
)

@worker.on_task("research.requested")
async def handle_research(task, ctx):
    # handler logic — no schema or registry calls here
    ...

# planner.py — discovers worker, retrieves schema, uses LLM to generate payload
@planner.on_goal("research.goal")
async def plan_research(goal, ctx: PlatformContext):
    # Dynamic discovery — no hardcoded event names
    agents = await ctx.registry.discover(
        requirements=["web_research"],
        include_schemas=True,
    )
    if not agents:
        raise RuntimeError("No research agents available")

    # Fetch the consumed schema — SDK returns typed PayloadSchema with json_schema field
    schema_name = agents[0].get_consumed_schemas()[0]
    schema = await ctx.registry.get_schema(schema_name)

    # LLM generates a conforming payload — SDK's PayloadSchema.to_llm_prompt() builds the
    # prompt automatically; planner does NOT hand-craft prompt strings
    payload = await ctx.ai.generate_payload(schema=schema, context=goal.description)

    # Publish with explicit response_event (§3 Event Choreography)
    await ctx.bus.request(
        event_type=agents[0].capabilities[0].consumed_event.event_name,
        payload=payload,
        response_event=f"research.completed.{goal.correlation_id}",
    )
```

**`start.sh` pattern (mirrors examples 09 & 10):**
```bash
#!/bin/bash
set -e
trap 'kill $(jobs -p) 2>/dev/null' EXIT INT TERM

python worker.py &
sleep 2  # allow worker to register with Registry + NATS before planner runs
python planner.py
wait
```

> **No `schema_registration.py` script.** Schema registration is part of agent startup via the SDK. When the worker instantiates its `AgentCapability` with an inline `json_schema`, `_register_with_registry()` calls `register_schema` automatically — the agent never does it explicitly.

---

### Example 12: EventSelector Intelligent Routing

**File structure:**
```
examples/12-event-selector/
├── README.md
├── .env.example
├── requirements.txt
├── start.sh                   # Starts all workers then publishes a test ticket
├── router.py                  # Customer support router using EventSelector
├── technical_worker.py        # Handles technical issues
├── billing_worker.py          # Handles billing issues
└── escalation_worker.py       # Handles escalations (high-priority)
```

> **No `prompts/` directory.** `EventSelector` is an SDK abstraction — it owns prompt engineering internally. The agent passes *state* (key/value context), not raw prompt strings. Exposing a Jinja2 template in the example would teach the wrong pattern and leak SDK internals.

> **No per-example unit test directory.** Integration tests for `EventSelector` routing live in `sdk/python/tests/integration/` (see §5).

**Key patterns demonstrated:**
```python
# router.py — uses EventSelector for intelligent routing
# No prompt templates, no LiteLLM imports, no Jinja2 — all handled by SDK
from soorma.ai.selection import EventSelector

@worker.on_task("support.ticket.received")
async def route_ticket(task, ctx: PlatformContext):
    # SDK auto-discovers available events and builds its own routing prompt
    selector = EventSelector(
        context=ctx,
        topic="action-requests",
        model="gpt-4o-mini",  # optional override; SDK default applies if omitted
    )

    decision = await selector.select_event(state={
        "ticket_subject": task.payload["subject"],
        "ticket_body": task.payload["body"],
        "priority": task.payload.get("priority", "normal"),
    })

    # decision.event_type validated against registry inside SDK before return
    # decision.reasoning logged for audit — agent does not inspect prompt internals
    await selector.publish_decision(
        decision=decision,
        correlation_id=task.correlation_id,
    )
```

**`start.sh` pattern:**
```bash
#!/bin/bash
set -e
trap 'kill $(jobs -p) 2>/dev/null' EXIT INT TERM

python technical_worker.py &
python billing_worker.py &
python escalation_worker.py &
sleep 2  # allow workers to register before router runs
python router.py
wait
```

---

### Example 13: A2A Gateway

**File structure:**
```
examples/13-a2a-gateway/
├── README.md
├── .env.example
├── requirements.txt
├── start.sh                   # Starts internal_agent, then gateway_service
├── gateway_service.py         # FastAPI service with A2A endpoints
└── internal_agent.py          # Soorma worker handling routed requests
```

> **No per-example unit test directory.** A2A gateway round-trip tests live in `sdk/python/tests/integration/` (see §5).

**Key patterns demonstrated:**
```python
# gateway_service.py — A2A-compatible FastAPI gateway
from fastapi import FastAPI
from soorma.gateway import A2AGatewayHelper
from soorma import PlatformContext
from soorma_common import AgentDefinition, A2ATask

app = FastAPI()
GATEWAY_URL = os.environ["GATEWAY_URL"]  # e.g., https://api.example.com/a2a

@app.get("/.well-known/agent.json")
async def get_agent_card():
    """Publish A2A Agent Card for external discovery."""
    async with PlatformContext() as ctx:
        agent = await ctx.registry.get_agent("research-worker-001")
        card = A2AGatewayHelper.agent_to_card(agent, GATEWAY_URL)
    return card.model_dump()

@app.post("/a2a/tasks/send")
async def send_task(task: A2ATask):
    """Accept A2A task, convert to internal event, wait for response."""
    async with PlatformContext() as ctx:
        # Convert A2A task → internal event (response_event derived from task.id)
        event = A2AGatewayHelper.task_to_event(task, event_type="research.requested")
        response_event = await ctx.bus.request(
            event_type=event.event_type,
            payload=event.payload,
            response_event=f"a2a.response.{task.id}",
            timeout=30.0,
        )
        # Convert internal event → A2A response
        return A2AGatewayHelper.event_to_response(response_event, task_id=task.id)
```

---

## 5. TDD Strategy

### TDD Cycle for Examples

> **Examples are runnable demonstrations, not test suites.** They do NOT contain `tests/` subdirectories. Each example is validated by running it end-to-end via its `start.sh` script.

**STUB Phase:**
1. Create all `.py` files with function signatures and `pass` bodies
2. Verify the example can be imported without errors: `python -c "import worker"`
3. Verify `.env.example` is complete and documented
4. Verify `start.sh` runs without syntax errors (`bash -n start.sh`)

**GREEN Phase:**
1. Implement real logic — each example must run end-to-end via `./start.sh`
2. Verify expected console output matches the `README.md` "Expected Output" section
3. Confirm zero direct `RegistryClient` / service client imports in any example file

### Integration Test Strategy

Integration tests live in **`sdk/python/tests/integration/`** — the same test suite that already holds `test_registry_service_client.py`, `test_event_selector.py`, etc. There is no top-level `tests/` directory in this repo; tests always reside under their owning component (service, lib, or SDK).

**File:** `sdk/python/tests/integration/test_e2e_discovery.py`  
**Marker:** `@pytest.mark.integration` (requires `soorma dev` stack running)

```python
# Test fixtures — share a live docker-compose stack
@pytest.fixture(scope="session")
async def registry_ctx():
    """Live PlatformContext connected to running soorma dev stack (Registry + NATS)."""
    async with PlatformContext() as ctx:
        yield ctx

@pytest.mark.integration
class TestEndToEndDiscovery:
    async def test_register_and_discover(self, registry_ctx):
        """Worker registers → planner discovers → planner gets schema."""
        # Register schema
        await registry_ctx.registry.register_schema(
            schema_name="test_schema_e2e_v1",
            version="1.0.0",
            json_schema={"type": "object", "properties": {"query": {"type": "string"}}},
        )
        # Register agent
        await registry_ctx.registry.register_agent(...)
        # Discover
        agents = await registry_ctx.registry.discover(requirements=["e2e_test_task"])
        assert len(agents) == 1
        assert agents[0].capabilities[0].consumed_event.payload_schema_name == "test_schema_e2e_v1"

    async def test_schema_versioning_coexistence(self, registry_ctx):
        """v1.0.0 and v2.0.0 schemas coexist without conflict."""
        await registry_ctx.registry.register_schema("versioned_schema", "1.0.0", {...})
        await registry_ctx.registry.register_schema("versioned_schema", "2.0.0", {...})
        v1 = await registry_ctx.registry.get_schema("versioned_schema", version="1.0.0")
        v2 = await registry_ctx.registry.get_schema("versioned_schema", version="2.0.0")
        assert v1.version == "1.0.0"
        assert v2.version == "2.0.0"
        assert v1.json_schema != v2.json_schema

    async def test_deregister_cleanup(self, registry_ctx):
        """Deregistered agent no longer appears in discover results."""
        ...
```

**File:** `sdk/python/tests/integration/test_multi_tenant_isolation.py`

```python
@pytest.mark.integration
class TestMultiTenantIsolation:
    async def test_cross_tenant_agents_invisible(self):
        """Agent registered in tenant_a is invisible to tenant_b queries."""
        async with PlatformContext(tenant_id=TENANT_A_ID) as ctx_a:
            await ctx_a.registry.register_agent(agent_a)

        async with PlatformContext(tenant_id=TENANT_B_ID) as ctx_b:
            agents = await ctx_b.registry.discover(requirements=["tenant_a_capability"])
            assert len(agents) == 0  # TENANT_B cannot see TENANT_A agents

    async def test_cross_tenant_schemas_invisible(self):
        """Schema registered in tenant_a is invisible to tenant_b lookup."""
        ...
```

**File:** `sdk/python/tests/integration/test_a2a_gateway_roundtrip.py`

```python
@pytest.mark.integration
class TestA2AGatewayRoundTrip:
    async def test_full_roundtrip_http_to_event_to_http(self, test_client):
        """External HTTP → A2A task → internal event → A2A response."""
        response = test_client.post("/a2a/tasks/send", json={
            "id": "task-001",
            "message": {"parts": [{"text": "Research quantum computing"}]},
        })
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "task-001"
        assert data["status"]["state"] == "completed"

    async def test_agent_card_structure(self, test_client):
        """Agent Card matches A2A specification structure."""
        response = test_client.get("/.well-known/agent.json")
        card = response.json()
        assert "name" in card
        assert "capabilities" in card
        assert "url" in card
```

---

## 6. Forward Deployed Logic Decision

**FDE Analysis:** All components in Phase 5 are examples and documentation — no new infrastructure services.

| Component | Full Implementation | FDE Option | Decision |
|-----------|--------------------|-----------|----|
| **Example 11** (LLM) | Uses real LiteLLM call to generate payload | Use static hardcoded payload if no LLM key | ✅ Full — but guard with `if os.getenv("OPENAI_API_KEY")` check |
| **Example 12** (EventSelector) | LLM-based routing | Same guard | ✅ Full — same guard |
| **Example 13** (A2A) | FastAPI service with full round-trip | N/A — no LLM needed | ✅ Full |
| **Integration Tests** | Requires live docker-compose stack | `@pytest.mark.integration` skip flag | ✅ Full — integration tests gated by marker |

**Conditional LLM Guard Pattern:**
```python
# All LLM-dependent examples follow this pattern
if not os.getenv("OPENAI_API_KEY"):
    print("[SKIP] OPENAI_API_KEY not set — set it to run this example")
    print("       Without it, using a mock static payload instead")
    payload = DEMO_STATIC_PAYLOAD
else:
    payload = await generate_payload_with_llm(goal, schema)
```

This allows developers to run examples without an LLM key and observe the discovery/schema flow, while full LLM functionality activates with an API key.

---

## 7. Day-by-Day Implementation Schedule

### Day 1 — Examples 11 & 12 (8h)

| Hours | Task | Deliverable |
|-------|------|-------------|
| 0:00–1:30 | T0: SDK auto-schema-registration in `_register_with_registry()` | `base.py` updated, tests passing |
| 1:30–2:00 | T1: Scaffold Example 11 | Directories, `.env.example`, stub files, `start.sh` |
| 0:30–2:00 | T2: Worker in Example 11 | `worker.py` — `ctx.registry.*` at startup, event handler |
| 2:00–4:30 | T3: Planner in Example 11 | `planner.py` — `ctx.registry.discover()`, `ctx.ai.generate_payload()`, `ctx.bus.request()` |
| 4:30–5:15 | T4: Example 11 `README.md` + `./start.sh` end-to-end run | Expected output documented, `start.sh` verified |
| 5:15–5:45 | T5: Scaffold Example 12 | Directories, stub files, `start.sh`. No `prompts/` dir. |
| 5:45–7:15 | T6: Three workers in Example 12 | Each worker registers at startup via `ctx.registry.*` |
| 7:15–8:00 | T7 (partial): Router stub | `router.py` skeleton with `EventSelector` wiring |

### Day 2 — Examples 12 (cont.) & 13 (8h)

| Hours | Task | Deliverable |
|-------|------|-------------|
| 0:00–1:00 | T7 (cont.): Complete `router.py` | `EventSelector.select_event()` + `publish_decision()` working |
| 1:00–1:45 | T8: Example 12 `README.md` + `./start.sh` run | Routing to correct workers verified |
| 1:45–2:15 | T9: Scaffold Example 13 | Directories, stub files, `start.sh` |
| 2:15–4:45 | T10: Gateway Service | `gateway_service.py` with A2A endpoints via `A2AGatewayHelper` |
| 4:45–6:15 | T11: Internal Agent | `internal_agent.py` — registers + handles events |
| 6:15–7:00 | T12: Example 13 `README.md` + `./start.sh` run | A2A round-trip verified in output |
| 7:00–8:00 | SDK compliance sweep | `grep -rn 'RegistryClient\|MemoryServiceClient' examples/` returns zero results |

### Day 3 — Integration Tests (6h)

| Hours | Task | Deliverable |
|-------|------|-------------|
| 0:00–2:00 | T13: E2E discovery integration tests | 10+ tests, `sdk/python/tests/integration/test_e2e_discovery.py` |
| 2:00–3:00 | T14: Multi-tenant isolation tests | 5+ tests, `sdk/python/tests/integration/test_multi_tenant_isolation.py` |
| 3:00–4:00 | T15: A2A round-trip tests | 5+ tests, `sdk/python/tests/integration/test_a2a_gateway_roundtrip.py` |
| 4:00–6:00 | Run full SDK test suite, fix failures | `pytest sdk/python/tests/` all passing |

### Day 4 — Documentation & CHANGELOG (4h)

| Hours | Task | Deliverable |
|-------|------|-------------|
| 0:00–2:00 | T16: Documentation updates | `README.md`, `ARCHITECTURE.md`, `ARCHITECTURE_PATTERNS.md` |
| 2:00–3:00 | T17: CHANGELOG entries | v0.8.1 entries in all 4 changelogs |
| 3:00–3:30 | T18: `examples/README.md` update | Examples 11–13 in learning path |
| 3:30–4:00 | Final review pass | Master Plan status updated to ✅ Complete |

---

## 8. Definition of Done

Phase 5 is **complete** when ALL of the following are true:

- [ ] T0 complete: `_register_with_registry()` auto-registers inline schemas; no example calls `ctx.registry.register_schema()` explicitly
- [ ] `examples/11-discovery-llm/` runs end-to-end via `./start.sh` and produces expected output
- [ ] `examples/12-event-selector/` runs end-to-end via `./start.sh` and routes tickets to correct workers
- [ ] `examples/13-a2a-gateway/` runs end-to-end via `./start.sh` and completes an A2A HTTP round-trip
- [ ] Zero `tests/` subdirectories inside any example directory
- [ ] Zero direct service client imports in examples: `grep -rn 'RegistryClient\|MemoryServiceClient\|BusClient' examples/` returns no results
- [ ] Zero Jinja2 / prompt template files in examples: prompt engineering is internal to the SDK
- [ ] Integration tests live in `sdk/python/tests/integration/`: `pytest sdk/python/tests/integration/ -m integration` (requires `soorma dev` stack)
- [ ] 25+ integration tests across 3 test files, all passing
- [ ] Zero direct `RegistryClient` imports in any example (grep verified)
- [ ] `docs/discovery/README.md` status updated to `✅ Implementation Complete`
- [ ] `docs/discovery/ARCHITECTURE.md` status updated to `✅ All 5 Phases Complete`  
- [ ] `MASTER_PLAN_Enhanced_Discovery.md` Phase 5 status updated to `✅ Complete`
- [ ] `CHANGELOG.md` v0.8.1 entries written in root, SDK, soorma-common, and Registry changelogs
- [ ] `examples/README.md` includes examples 11–13 in the learning path table

---

## 9. Related Documents

- [MASTER_PLAN_Enhanced_Discovery.md](MASTER_PLAN_Enhanced_Discovery.md) — Parent plan (Phase 5 row)
- [ACTION_PLAN_Phase3_SDK_Implementation.md](ACTION_PLAN_Phase3_SDK_Implementation.md) — Completed Phase 3 (wrappers implemented)
- [ACTION_PLAN_Phase4_Tracker_NATS_Integration.md](ACTION_PLAN_Phase4_Tracker_NATS_Integration.md) — Completed Phase 4 (infrastructure)
- [docs/ARCHITECTURE_PATTERNS.md](../../ARCHITECTURE_PATTERNS.md) — §2 (wrapper pattern), §3 (event choreography), §4 (multi-tenancy)
- [docs/discovery/README.md](../README.md) — Feature user guide (updated in T16)
- [docs/discovery/ARCHITECTURE.md](../ARCHITECTURE.md) — Feature technical architecture (updated in T16)
- [examples/README.md](../../../examples/README.md) — Examples learning path (updated in T18)
