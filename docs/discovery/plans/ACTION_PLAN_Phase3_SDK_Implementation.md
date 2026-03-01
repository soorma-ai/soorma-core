# Action Plan: Phase 3 - SDK Implementation & A2A Gateway (SOOR-DISC-P3)

**Status:** 📋 Planning  
**Parent Plan:** [MASTER_PLAN_Enhanced_Discovery.md](MASTER_PLAN_Enhanced_Discovery.md)  
**Phase:** 3 of 5  
**Refactoring Tasks:** RF-SDK-007, RF-SDK-008, RF-SDK-017  
**Estimated Duration:** 3-4 days (26 hours)  
**Target Release:** v0.8.1  
**Created:** March 1, 2026  
**Prerequisites:** Phase 1 ✅ Complete, Phase 2 ✅ Complete

---

## Architecture Compliance (Gate 0)

Per AGENT.md Section 2 (Step 0), the following ARCHITECTURE_PATTERNS.md sections have been read in full before planning:

| Section | Pattern | Application in Phase 3 |
|---------|---------|------------------------|
| §1 Auth | `X-Tenant-ID` custom header (v0.7.x) | `RegistryClient` already injects `X-Tenant-ID` from `SOORMA_DEVELOPER_TENANT_ID`. No changes needed. |
| §2 Two-Layer SDK | `RegistryClient` IS the wrapper; `context.registry` exposes it directly | New methods (`discover()`, `get_schema()`) added to `RegistryClient` are automatically available via `context.registry.*`. Agent code uses `context.registry.discover()` exclusively. |
| §3 Event Choreography | Explicit `response_event`, no inferred names | `EventSelector.publish_decision()` passes `response_event` explicitly. `A2AGatewayHelper.task_to_event()` carries `response_event` from A2A task ID. |
| §4 Multi-tenancy | PostgreSQL RLS enforced at service layer | Isolation is transparent to Phase 3 SDK — the Registry Service (Phase 2) handles this. SDK passes `X-Tenant-ID`; RLS filters automatically. |
| §5 State Management | N/A for discovery | Not applicable — `EventSelector` is stateless per invocation. |
| §6 Error Handling | Service client raises → wrapper propagates → handler converts | `RegistryClient.discover()` returns `None`/empty on 404; raises on unexpected errors. `EventSelector` raises `EventSelectionError` on LLM failure. |
| §7 Testing | Unit tests mock HTTP client; integration tests use live services | Phase 3 unit tests mock `httpx.AsyncClient`. Integration tests tagged `@pytest.mark.integration`. |

**Self-Check Answers:**
- **Why can't agent code import `RegistryServiceClient`?** There is no separate `RegistryServiceClient` — `RegistryClient` in `sdk/python/soorma/registry/client.py` is the single service client AND the agent-facing wrapper. It auto-injects `X-Tenant-ID`, abstracts HTTP, and is the only entry-point exposed via `context.registry`. Giving agents access to raw HTTP would bypass auth abstraction and expose internal infrastracture details.
- **Difference between service endpoint and wrapper method?** A service endpoint is an HTTP route on the backend (e.g., `GET /v1/agents/discover`). A wrapper method is the Python API in `RegistryClient` that calls it (e.g., `context.registry.discover(requirements=["web_search"])`). The wrapper hides auth headers, serialization, and error mapping.

---

## 1. Requirements & Core Objective

### Phase Objective

Implement SDK-level discovery methods, the `EventSelector` intelligent routing utility, and the `A2AGatewayHelper` for external interoperability. This phase makes the Phase 2 service endpoints usable from agent code and adds the full LLM-based routing capability from RF-SDK-017.

**From Master Plan Section 3 - Phase 3:**
- Update `RegistryClient.discover_agents()` to return `List[DiscoveredAgent]` and add `discover()` alias with capability filtering
- Implement `EventSelector` in `sdk/python/soorma/ai/selection.py` (RF-SDK-017)
- Implement `A2AGatewayHelper` in `sdk/python/soorma/gateway.py`
- Add `EventDecision` DTO to `soorma_common/decisions.py`
- Write 40+ SDK unit tests covering discovery, schema, selector, and gateway

### Acceptance Criteria

- [ ] `context.registry.discover(requirements=["web_search"])` returns `List[DiscoveredAgent]` with full capabilities
- [ ] `context.registry.discover(requirements=..., include_schemas=True)` includes schema references in results
- [ ] `context.registry.get_schema("search_request_v1")` retrieves a `PayloadSchema` from service
- [ ] `EventSelector.select_event()` returns an `EventDecision` with validated `event_type`, `payload`, `reasoning`
- [ ] `EventSelector` validates selected event exists in registry before returning decision
- [ ] `A2AGatewayHelper.agent_to_card()` converts `AgentDefinition` to a valid `A2AAgentCard`
- [ ] `A2AGatewayHelper.task_to_event()` converts `A2ATask` → `EventEnvelope` with correlation tracking
- [ ] `A2AGatewayHelper.event_to_response()` converts `EventEnvelope` → `A2ATaskResponse`
- [ ] All new methods have Google-style docstrings and full type hints
- [ ] 40+ unit tests passing (15 discovery, 10 schema client, 10 EventSelector, 10 A2AGateway)
- [ ] No agent/example code imports `RegistryClient` directly — all use `context.registry.*`

### Refactoring Tasks Addressed

| Task ID | Description | Status |
|---------|-------------|--------|
| RF-SDK-007 | Event registration tied to agent startup (schema references) | 🟡 Partial — `RegistryClient` already supports `EventDefinition.payload_schema_name`. Phase 3 verifies example agents use schema names, not embedded schemas. |
| RF-SDK-008 | Agent discovery by capability (`DiscoveredAgent` return type) | 🎯 This phase |
| RF-SDK-017 | EventSelector utility (deferred from Stage 4) | 🎯 This phase |

---

## 2. Technical Design

### Component Map

| Component | File | Change Type |
|-----------|------|-------------|
| `RegistryClient` | `sdk/python/soorma/registry/client.py` | Update — add `discover()`, update `discover_agents()` return type |
| `EventDecision` DTO | `libs/soorma-common/src/soorma_common/decisions.py` | New model |
| `EventSelector` | `sdk/python/soorma/ai/selection.py` | New file |
| `A2AGatewayHelper` | `sdk/python/soorma/gateway.py` | New file |
| `soorma_common.__init__` | `libs/soorma-common/src/soorma_common/__init__.py` | Export `EventDecision` |
| `soorma.__init__` | `sdk/python/soorma/__init__.py` | Export `A2AGatewayHelper`, `EventSelector` |
| Tests | `sdk/python/tests/test_registry_discover.py` | New file |
| Tests | `sdk/python/tests/test_registry_schema_client.py` | New file |
| Tests | `sdk/python/tests/test_event_selector.py` | New file |
| Tests | `sdk/python/tests/test_a2a_gateway_helper.py` | New file |

### Data Models

**New: `EventDecision`** (in `soorma_common/decisions.py`)

```python
class EventDecision(BaseModel):
    """LLM-selected event routing decision produced by EventSelector.
    
    Attributes:
        event_type: Validated event name that exists in the registry.
        topic: PubSub topic for the event.
        payload: LLM-generated payload conforming to event schema.
        reasoning: LLM's explanation for selecting this event.
        confidence: Optional confidence score (0.0–1.0).
    """
    event_type: str
    topic: str
    payload: Dict[str, Any]
    reasoning: str
    confidence: Optional[float] = None
```

**Updated: `RegistryClient.discover()`** (replaces `discover_agents()` scope for Phase 3)

```python
async def discover(
    self,
    requirements: List[str],
    include_schemas: bool = True,
) -> List[DiscoveredAgent]:
    """Discover agents by capability requirements."""

async def discover_agents(
    self,
    consumed_event: Optional[str] = None,
) -> List[DiscoveredAgent]:  # Return type updated from List[AgentDefinition]
    """Discover active agents by consumed event (backward-compat method)."""
```

**New: `EventSelector`**

```python
class EventSelector:
    """LLM-based event selector for intelligent routing.
    
    Args:
        context: PlatformContext (for registry access via context.registry)
        topic: EventTopic to discover events from
        prompt_template: Optional prompt template string (uses f-string substitution)
        model: LiteLLM model identifier (default: "gpt-4o-mini")
        api_key: Optional API key override
        api_base: Optional base URL for custom endpoints
    """
    
    async def select_event(
        self,
        state: Dict[str, Any],
    ) -> EventDecision: ...
    
    async def publish_decision(
        self,
        decision: EventDecision,
        correlation_id: str,
        response_event: Optional[str] = None,
        response_topic: Optional[str] = None,
    ) -> None: ...
```

**New: `A2AGatewayHelper`**

```python
class A2AGatewayHelper:
    """Static conversion helpers between Soorma and A2A protocol DTOs."""
    
    @staticmethod
    def agent_to_card(
        agent: AgentDefinition,
        gateway_url: str,
        auth_type: A2AAuthType = A2AAuthType.NONE,
    ) -> A2AAgentCard: ...
    
    @staticmethod
    def task_to_event(
        task: A2ATask,
        event_type: str,
        topic: str = "action-requests",
        tenant_id: str = "00000000-0000-0000-0000-000000000000",
        user_id: str = "00000000-0000-0000-0000-000000000000",
    ) -> EventEnvelope: ...
    
    @staticmethod
    def event_to_response(
        event: EventEnvelope,
        task_id: str,
    ) -> A2ATaskResponse: ...
```

### SDK Layer Verification

This section verifies compliance with ARCHITECTURE_PATTERNS.md Section 2 before implementation begins.

**`context.registry` Architecture:**

> Note: `RegistryClient` is NOT wrapped in a separate class inside `context.py`. It IS the agent-facing wrapper. `PlatformContext.__init__()` initializes it as `self.registry = RegistryClient(base_url=...)`. This is the approved pattern for the registry (developer-scoped, not session-scoped). See Phase 2 ARCHITECTURE_COMPLIANCE verification.

- [x] **`RegistryClient` (the wrapper):** All new methods added directly here. No separate service client needed.
  - File: `sdk/python/soorma/registry/client.py`
  - New method: `discover(requirements, include_schemas) -> List[DiscoveredAgent]`
  - Updated method: `discover_agents(consumed_event) -> List[DiscoveredAgent]` (return type change)
  - Existing (verified working): `register_schema()`, `get_schema()`, `list_schemas()`
  - Verified: All methods inject `X-Tenant-ID` via `self._auth_headers` ✅

- [x] **`PlatformContext` wrappers:** `context.registry.*` automatically exposes all `RegistryClient` methods.
  - File: `sdk/python/soorma/context.py`, line 1466: `self.registry = RegistryClient(...)`
  - Agent code calls: `await context.registry.discover(["web_search"])`
  - Zero config required — wrapper is `RegistryClient` itself ✅

- [x] **Examples compliance:** All examples that show agent code MUST use `context.registry.*`
  - New examples (11, 12, 13 — Phase 5) will be written against `context.registry.*` exclusively
  - No `from soorma.registry.client import RegistryClient` in example agent handlers ✅

- [x] **`EventSelector` architecture:** Receives `PlatformContext` and calls `context.toolkit` (which reuses `context.registry`) for event discovery. Does NOT instantiate `RegistryClient` independently.

- [x] **`A2AGatewayHelper` architecture:** Pure static helper — no runtime dependencies on services. Handles DTO conversion only. No auth context needed.

**Note if wrapper methods were missing:** All are present or being added. New `discover()` and `EventDecision` are the only net-new additions. No blocking gaps.

---

## 3. Task Tracking Matrix

### Task 3A: `RegistryClient.discover()` — Enhanced Discovery (RF-SDK-008)

**Scope:** Update `discover_agents()` return type and add `discover()` with requirements parameter.

**Why both methods?** `discover()` is the new high-level API (requirements-based). `discover_agents()` stays for backward compatibility with existing code in Phases 1–2 but now returns `DiscoveredAgent` instead of `AgentDefinition`.

**STUB → RED → GREEN → REFACTOR cycle:**

- [ ] **STUB (0.5h):** Add `discover()` stub to `RegistryClient` with `NotImplementedError`. Update `discover_agents()` return type annotation to `List[DiscoveredAgent]` (implementation raises `NotImplementedError`).
  ```python
  async def discover(
      self,
      requirements: List[str],
      include_schemas: bool = True,
  ) -> List[DiscoveredAgent]:
      """Discover agents by capability requirements (stub)."""
      raise NotImplementedError("Phase 3 discovery not yet implemented")
  ```

- [ ] **RED (1h):** Write tests in `tests/test_registry_discover.py`. Tests MUST fail with `NotImplementedError`:
  - `test_discover_returns_discovered_agent_list` — asserts return type is `List[DiscoveredAgent]`
  - `test_discover_with_requirements_sends_query_param` — verifies `requirements` becomes query param
  - `test_discover_include_schemas_true_passes_param` — verifies `include_schemas=True` in request
  - `test_discover_agents_returns_discovered_agent_list` — backward compat: `discover_agents()` returns `List[DiscoveredAgent]`
  - `test_discover_empty_result` — handles empty list response gracefully
  - `test_discover_maps_agent_definition_to_discovered_agent` — verifies field mapping
  - `test_discover_parses_version_from_name` — `"SearchWorker:1.0.0"` → `version="1.0.0"`
  - `test_discover_defaults_version_when_no_suffix` — `"SearchWorker"` → `version="1.0.0"`

- [ ] **GREEN (1.5h):** Implement real logic:
  - `discover()`: GET `/v1/agents/discover?requirements[]=web_search&include_schemas=true`
  - Map `AgentQueryResponse.agents` → `List[DiscoveredAgent]` (parse version from `name:version`)
  - `discover_agents()`: delegates to `discover()` or uses consumed_event param on `/v1/agents/discover`

- [ ] **REFACTOR (0.5h):** Extract `_map_agent_to_discovered(agent: AgentDefinition) -> DiscoveredAgent` helper. Ensure docstrings present. Update `discover_agents()` docstring to note backward-compat status.

**Files Modified:**
- `sdk/python/soorma/registry/client.py` — add `discover()`, update `discover_agents()`
- `sdk/python/tests/test_registry_discover.py` — new test file

---

### Task 3B: `EventDecision` DTO (RF-SDK-017 foundation)

**Scope:** Add `EventDecision` model to `soorma_common/decisions.py` and export from `__init__.py`.

- [ ] **STUB (0.25h):** Add `EventDecision` class with field stubs (no validation logic yet):
  ```python
  class EventDecision(BaseModel):
      event_type: str
      topic: str
      payload: Dict[str, Any]
      reasoning: str
      confidence: Optional[float] = None
  ```

- [ ] **RED (0.5h):** Write tests in `libs/soorma-common/tests/test_decisions.py` (extend existing file if present, else create):
  - `test_event_decision_requires_event_type` — missing field raises ValidationError
  - `test_event_decision_requires_topic` — missing field raises ValidationError
  - `test_event_decision_requires_payload_dict` — non-dict payload raises ValidationError
  - `test_event_decision_confidence_optional` — confidence defaults to None
  - `test_event_decision_exported_from_soorma_common` — `from soorma_common import EventDecision`

- [ ] **GREEN (0.25h):** Model is trivially correct — tests should pass immediately after STUB if fields are defined. Confirm export added to `soorma_common/__init__.py`.

- [ ] **REFACTOR (0.25h):** Add Google-style docstring. Add model_config for alias generation (inherit `BaseModel` or check if `BaseDTO` needed).

**Files Modified:**
- `libs/soorma-common/src/soorma_common/decisions.py`
- `libs/soorma-common/src/soorma_common/__init__.py`

---

### Task 3C: `EventSelector` (RF-SDK-017)

**Scope:** Implement LLM-based event routing in `sdk/python/soorma/ai/selection.py`.

**Design Notes:**
- Reuses `context.toolkit` (`EventToolkit`) for `discover_events()` and `format_for_llm()` — no direct `RegistryClient` access
- Uses LiteLLM (same pattern as `ChoreographyPlanner`) — BYO model, no hardcoded vendor
- Prompt template: f-string based (FDE decision — see Section 5). Template receives `state` dict and `events` list as formatted JSON.
- Validates selected event exists in discovered list before returning `EventDecision` — prevents LLM hallucination

**STUB → RED → GREEN → REFACTOR cycle:**

- [ ] **STUB (0.5h):** Create `sdk/python/soorma/ai/selection.py` with skeleton:
  ```python
  class EventSelector:
      def __init__(
          self,
          context: "PlatformContext",
          topic: EventTopic,
          prompt_template: Optional[str] = None,
          model: str = "gpt-4o-mini",
          api_key: Optional[str] = None,
          api_base: Optional[str] = None,
      ) -> None:
          raise NotImplementedError("EventSelector.__init__ not yet implemented")
      
      async def select_event(
          self,
          state: Dict[str, Any],
      ) -> EventDecision:
          raise NotImplementedError("EventSelector.select_event not yet implemented")
      
      async def publish_decision(
          self,
          decision: EventDecision,
          correlation_id: str,
          response_event: Optional[str] = None,
          response_topic: Optional[str] = None,
      ) -> None:
          raise NotImplementedError("EventSelector.publish_decision not yet implemented")
  ```

- [ ] **RED (1.5h):** Write tests in `sdk/python/tests/test_event_selector.py`. All MUST fail with `NotImplementedError`:
  - `test_select_event_returns_event_decision` — basic selection returns `EventDecision`
  - `test_select_event_validates_event_exists_in_registry` — selected event not in discovered list raises `ValueError`
  - `test_select_event_uses_default_prompt_when_none_given` — default template applied
  - `test_select_event_uses_custom_prompt_template` — custom template used
  - `test_select_event_llm_response_parsed_correctly` — mock LLM returns JSON, parsed to `EventDecision`
  - `test_select_event_llm_invalid_json_raises_error` — malformed LLM output raises `EventSelectionError`
  - `test_select_event_unknown_event_raises_error` — LLM picks unlisted event raises `EventSelectionError`
  - `test_publish_decision_calls_context_bus` — `publish_decision()` calls `context.bus.publish()` correctly
  - `test_publish_decision_passes_response_event` — `response_event` forwarded to bus publish
  - `test_selector_reuses_context_toolkit` — no new `RegistryClient` instantiated

- [ ] **GREEN (3h):** Implement real logic:
  1. `__init__`: Store `context`, `topic`, `prompt_template`, LiteLLM config
  2. `select_event()`:
     - `events = await context.toolkit.discover_events(topic=self.topic)`
     - `events_json = context.toolkit.format_for_llm(events)`
     - Build prompt: substitute `state` dict and `events_json` into template
     - Call LiteLLM: `response = await litellm.acompletion(model=..., messages=[...])`
     - Parse JSON from response into `EventDecision`
     - Validate `event_type` exists in discovered list — if not, raise `EventSelectionError`
     - Return `EventDecision`
  3. `publish_decision()`:
     - `await context.bus.publish(topic=decision.topic, event_type=decision.event_type, data=decision.payload, response_event=response_event, ...)`

- [ ] **REFACTOR (0.5h):** Extract `_build_prompt()` and `_parse_llm_response()` helpers. Add `EventSelectionError` exception class (in same file or `soorma.exceptions`). Export `EventSelector` from `sdk/python/soorma/__init__.py`.

**Files Created/Modified:**
- `sdk/python/soorma/ai/selection.py` — new file
- `sdk/python/tests/test_event_selector.py` — new test file
- `sdk/python/soorma/__init__.py` — add `EventSelector` export

---

### Task 3D: `A2AGatewayHelper` (RF-SDK-008 / A2A interoperability)

**Scope:** Implement static conversion helpers in `sdk/python/soorma/gateway.py`.

**Design Notes:**
- Pure static methods — no constructor, no service calls, no auth context
- `agent_to_card()`: `AgentDefinition.capabilities` → `List[A2ASkill]`. Parse version from `name:version` format (if present) else default `"1.0.0"`.
- `task_to_event()`: A2ATask → `EventEnvelope`. Extracts `task.message.parts[0].text` as `data["input"]`. Sets `correlation_id=task.id`.
- `event_to_response()`: `EventEnvelope` → `A2ATaskResponse`. Sets `status=A2ATaskStatus.COMPLETED` if event has data, else `FAILED`.

**STUB → RED → GREEN → REFACTOR cycle:**

- [ ] **STUB (0.25h):** Create `sdk/python/soorma/gateway.py`:
  ```python
  class A2AGatewayHelper:
      @staticmethod
      def agent_to_card(agent: AgentDefinition, gateway_url: str, ...) -> A2AAgentCard:
          raise NotImplementedError
      
      @staticmethod
      def task_to_event(task: A2ATask, event_type: str, ...) -> EventEnvelope:
          raise NotImplementedError
      
      @staticmethod
      def event_to_response(event: EventEnvelope, task_id: str) -> A2ATaskResponse:
          raise NotImplementedError
  ```

- [ ] **RED (0.75h):** Write tests in `sdk/python/tests/test_a2a_gateway_helper.py`:
  - `test_agent_to_card_name_and_description` — basic field mapping
  - `test_agent_to_card_sets_gateway_url` — `url` field populated from arg
  - `test_agent_to_card_capabilities_become_skills` — 2 capabilities → 2 skills
  - `test_agent_to_card_skill_maps_schema_name` — `capability.consumed_event.payload_schema_name` → `A2ASkill.inputSchema` reference
  - `test_agent_to_card_parses_version_from_name` — `"ResearchWorker:2.0.0"` → `version="2.0.0"`
  - `test_task_to_event_sets_event_type` — correct `event_type` in envelope
  - `test_task_to_event_uses_task_id_as_correlation` — `correlation_id == task.id`
  - `test_task_to_event_text_part_in_data` — `parts[0].text` → `data["input"]`
  - `test_event_to_response_completed_when_data_present` — `status == COMPLETED`
  - `test_event_to_response_failed_when_empty` — `status == FAILED`

- [ ] **GREEN (1.5h):** Implement all three static methods with correct field mapping.

- [ ] **REFACTOR (0.25h):** Add docstrings. Export `A2AGatewayHelper` from `sdk/python/soorma/__init__.py`. Add imports to `soorma_common/__init__.py` if any new models added (none expected).

**Files Created/Modified:**
- `sdk/python/soorma/gateway.py` — new file
- `sdk/python/tests/test_a2a_gateway_helper.py` — new test file
- `sdk/python/soorma/__init__.py` — add `A2AGatewayHelper` export

---

### Task 3E: Schema Client Tests (gap fill)

**Scope:** The `register_schema()`, `get_schema()`, `list_schemas()` methods in `RegistryClient` were implemented in Phase 2 but tested only at the service level. This task adds SDK-layer unit tests.

- [ ] **Write tests** in `sdk/python/tests/test_registry_schema_client.py`:
  - `test_register_schema_sends_correct_payload` — mock HTTP, verify camelCase aliasing
  - `test_register_schema_returns_payload_schema_response` — return type verified
  - `test_get_schema_latest_version` — calls `GET /v1/schemas/{name}`
  - `test_get_schema_specific_version` — calls `GET /v1/schemas/{name}/versions/{ver}`
  - `test_get_schema_returns_none_on_404` — 404 → `None` (not exception)
  - `test_list_schemas_no_filter` — calls `GET /v1/schemas` with no params
  - `test_list_schemas_with_owner_filter` — `owner_agent_id` becomes query param
  - `test_list_schemas_returns_list` — return type `List[PayloadSchema]`

These are **pure GREEN** tests (no STUB/RED cycle needed — code already implemented, tests filling coverage gap).

**Files Created:**
- `sdk/python/tests/test_registry_schema_client.py` — new test file

---

### Task Summary

| Task | Duration | Priority | Status |
|------|----------|----------|--------|
| **3A:** `discover()` + `discover_agents()` return type | 3.5h | 🔴 Critical | 📋 Not started |
| **3B:** `EventDecision` DTO | 1.25h | 🔴 Critical (blocks 3C) | 📋 Not started |
| **3C:** `EventSelector` | 5.5h | 🟡 High | 📋 Not started |
| **3D:** `A2AGatewayHelper` | 2.75h | 🟡 High | 📋 Not started |
| **3E:** Schema client tests | 2h | 🟢 Medium | 📋 Not started |
| **FDE check:** Verify `litellm` installed | 0.25h | 🟡 High | 📋 Not started |
| **Exports:** `__init__.py` updates | 0.5h | 🟢 Medium | 📋 Not started |

**Total estimated:** 15.75h (~2 days)

**Execution sequence:** 3B → 3A → 3C → 3D → 3E → Exports

---

## 4. TDD Strategy

### Unit Tests (SDK Layer)

All unit tests mock the HTTP client at `httpx.AsyncClient` level.

**Fixtures** (`sdk/python/tests/conftest.py` — extend existing or create):

```python
@pytest.fixture
def mock_registry_client() -> RegistryClient:
    """RegistryClient with mocked HTTP client."""
    client = RegistryClient(base_url="http://test-registry")
    client._client = AsyncMock()
    return client

@pytest.fixture
def sample_agent_definition() -> AgentDefinition:
    """Minimal valid AgentDefinition with structured capabilities."""
    return AgentDefinition(
        agent_id="test-worker",
        name="TestWorker",
        description="Test agent",
        capabilities=[
            AgentCapability(
                task_name="test_task",
                description="A test task",
                consumed_event=EventDefinition(
                    event_name="test.requested",
                    topic="action-requests",
                    description="Test request",
                    payload_schema_name="test_request_v1",
                ),
                produced_events=[
                    EventDefinition(
                        event_name="test.completed",
                        topic="action-results",
                        description="Test result",
                    )
                ],
            )
        ],
    )

@pytest.fixture
def sample_a2a_task() -> A2ATask:
    """Minimal A2ATask for gateway conversion tests."""
    return A2ATask(
        id="task-001",
        message=A2AMessage(
            role="user",
            parts=[A2APart(type="text", text="Research AI trends")],
        ),
    )
```

**Mock patterns:**

```python
# Pattern 1: Mock successful JSON response
mock_response = MagicMock()
mock_response.status_code = 200
mock_response.json.return_value = {...}  # camelCase response
mock_response.raise_for_status = MagicMock()  # no-op
mock_registry_client._client.get.return_value = mock_response

# Pattern 2: Mock 404 (get_schema returns None)
mock_response.status_code = 404
mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(...)

# Pattern 3: Mock LLM in EventSelector
with patch("soorma.ai.selection.litellm.acompletion") as mock_llm:
    mock_llm.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content=json.dumps({
            "event_type": "research.requested",
            "topic": "action-requests",
            "payload": {"query": "test"},
            "reasoning": "Best match",
        })))]
    )
```

### Integration Tests (Live Services)

Tagged `@pytest.mark.integration` — not run in CI by default.

```python
@pytest.mark.integration
async def test_discover_agents_live():
    """Verify discover() returns DiscoveredAgent list against live registry."""
    context = PlatformContext.from_env()
    agents = await context.registry.discover(requirements=["web_search"])
    assert isinstance(agents, list)
    # If list non-empty, verify type
    if agents:
        assert isinstance(agents[0], DiscoveredAgent)
        assert agents[0].capabilities
```

**Pre-condition:** Registry Service running on `localhost:8081`, test agents registered via `examples/11-discovery-llm/` (Phase 5).

---

## 5. Forward Deployed Logic Decision

### FDE-1: Prompt Templates — f-strings instead of Jinja2

**Decision:** ✅ Use Python f-strings for `EventSelector` prompt templates. Do NOT add Jinja2 as a dependency.

**Rationale:**
- Jinja2 adds a new package dependency for marginal benefit (templates are short, single-level substitutions)
- f-strings handle `{state}` and `{events}` substitution cleanly
- Jinja2 can be added later when template complexity warrants it (e.g., conditionals, loops in templates)

**Implementation:**
```python
DEFAULT_SELECTOR_PROMPT = """\
You are an event routing agent. Given the current state and available events, \
select the most appropriate event to publish.

Current State:
{state_json}

Available Events:
{events_json}

Respond with a JSON object:
{{
  "event_type": "<selected event name>",
  "topic": "<event topic>",
  "payload": {{<generated payload conforming to schema>}},
  "reasoning": "<why this event was selected>"
}}
"""
```

**Trade-off:** Custom templates are passed as plain strings with `{state_json}` / `{events_json}` placeholders — developers must use these exact keys in their custom templates.

---

### FDE-2: `DiscoveredAgent.version` parsing — `name:version` convention

**Decision:** ✅ Parse `version` from `AgentDefinition.name` using the `name:version` suffix convention established in `AgentDefinition.__init__()`.

**Rationale:**
- `AgentDefinition.__init__` appends `:version` to the name (e.g., `"ResearchWorker:1.0.0"`)
- The database does not store version as a separate column (Phase 1 migration adds `version` column — but let's check if the API returns it)

**Lookup:** From Phase 1 migration: `version VARCHAR DEFAULT '1.0.0'` added to `agents` table. The `AgentQueryResponse` currently returns `AgentDefinition` objects. The service may need to populate `version` from the DB column.

**Implementation in SDK:**
```python
def _map_agent_to_discovered(self, agent: AgentDefinition) -> DiscoveredAgent:
    """Map AgentDefinition to DiscoveredAgent, parsing version from name."""
    name_parts = agent.name.split(":")
    name = name_parts[0]
    version = name_parts[1] if len(name_parts) > 1 else "1.0.0"
    return DiscoveredAgent(
        agent_id=agent.agent_id,
        name=name,
        description=agent.description,
        version=version,
        capabilities=agent.capabilities,
    )
```

**Risk:** If service populates a separate `version` field in `AgentDefinition` response, this parsing is redundant. Implementation should check for explicit version field first, fall back to name parsing.

---

### FDE-3: `EventSelector` error handling — `EventSelectionError` in same file

**Decision:** ✅ Define `EventSelectionError` exception class in `sdk/python/soorma/ai/selection.py` (co-located with `EventSelector`).

**Rationale:**
- Creating a separate `soorma.exceptions` module is premature (Phase 3 is the first consumer)
- Co-location keeps the file self-contained
- Can be moved to `soorma.exceptions` in a future refactoring stage

---

## 6. Deployment & Verification

### Pre-Implementation Checklist

- [ ] Phase 2 Registry Service tests still passing (`cd services/registry && pytest`)
- [ ] `soorma_common` exports `DiscoveredAgent`, `PayloadSchema`, `PayloadSchemaResponse`, `A2AAgentCard`, `A2ATask`, `A2ATaskResponse`
- [ ] `litellm` is in `sdk/python/pyproject.toml` (same dep as `ChoreographyPlanner`)

### Post-Implementation Checklist

- [ ] `pytest sdk/python/tests/test_registry_discover.py` — all 8 tests green
- [ ] `pytest sdk/python/tests/test_registry_schema_client.py` — all 8 tests green
- [ ] `pytest sdk/python/tests/test_event_selector.py` — all 10 tests green
- [ ] `pytest sdk/python/tests/test_a2a_gateway_helper.py` — all 10 tests green
- [ ] `pytest libs/soorma-common/tests/ -k test_event_decision` — all 5 tests green
- [ ] No `from soorma.registry.client import RegistryClient` in any example agent handler
- [ ] `EventSelector` and `A2AGatewayHelper` exported from top-level `soorma`

### CHANGELOG Entry (to be added on completion)

```
## [0.8.1] - 2026-03-XX

### Added
- `RegistryClient.discover()` — capability-based agent discovery returning `List[DiscoveredAgent]`
- `RegistryClient.discover_agents()` — updated return type to `List[DiscoveredAgent]`
- `EventSelector` — LLM-based event routing utility (`soorma.ai.selection`)
- `A2AGatewayHelper` — A2A protocol conversion helpers (`soorma.gateway`)
- `EventDecision` DTO — LLM routing decision model (`soorma_common.decisions`)
```

---

## 7. Related Documents

- [MASTER_PLAN_Enhanced_Discovery.md](MASTER_PLAN_Enhanced_Discovery.md) — Parent plan (Phase 3 section)
- [ACTION_PLAN_Phase1_Foundation.md](ACTION_PLAN_Phase1_Foundation.md) — ✅ Complete
- [ACTION_PLAN_Phase2_Service_Implementation.md](ACTION_PLAN_Phase2_Service_Implementation.md) — ✅ Complete
- [docs/ARCHITECTURE_PATTERNS.md](../../ARCHITECTURE_PATTERNS.md) — Core patterns (§1, §2, §3, §6, §7)
- [sdk/python/soorma/registry/client.py](../../../sdk/python/soorma/registry/client.py) — Target file for Tasks 3A
- [sdk/python/soorma/ai/choreography.py](../../../sdk/python/soorma/ai/choreography.py) — Reference pattern for LLM integration
- [sdk/python/soorma/ai/event_toolkit.py](../../../sdk/python/soorma/ai/event_toolkit.py) — Reused by `EventSelector`
- [libs/soorma-common/src/soorma_common/decisions.py](../../../libs/soorma-common/src/soorma_common/decisions.py) — Target for `EventDecision`
- [libs/soorma-common/src/soorma_common/a2a.py](../../../libs/soorma-common/src/soorma_common/a2a.py) — A2A DTOs (read-only)

---

**Plan Author:** GitHub Copilot (Soorma Senior Architect)  
**Status:** 📋 Planning — Awaiting developer approval before implementation  
**Next Step:** Developer approval → start Task 3B (EventDecision DTO) → Task 3A → Task 3C → Task 3D → Task 3E
