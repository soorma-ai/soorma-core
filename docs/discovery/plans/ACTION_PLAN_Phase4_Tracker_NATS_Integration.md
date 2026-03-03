# Action Plan: Phase 4 — Tracker Service NATS Integration (SOOR-DISC-004)

**Status:** 📋 Planning  
**Parent Plan:** [MASTER_PLAN_Enhanced_Discovery.md](MASTER_PLAN_Enhanced_Discovery.md)  
**Feature Area:** Discovery / Infrastructure  
**Refactoring Task:** TECH-DEBT-001  
**Created:** March 1, 2026  
**Estimated Duration:** 1–2 days (12–16 hours)  
**Target Release:** v0.8.1  

---

## Architecture Pattern Compliance (Step 0 Gateway)

**ARCHITECTURE_PATTERNS.md sections verified before planning:**

- ✅ **Section 1 (Authentication):** Tracker is a Tier 2 service — uses `X-Tenant-ID` + `X-User-ID` headers for task/plan data isolation. After this refactor, no headers are passed *from* Tracker outward; it reads tenant context from inbound event envelopes.
- ✅ **Section 2 (Two-Layer SDK):** This refactor is infrastructure-only. The goal is to *remove* the SDK (`soorma-core`) dependency from Tracker Service. No agent-facing PlatformContext wrappers are modified.
- ✅ **Section 3 (Event Choreography):** Tracker is a passive subscriber; it does not publish events. Subscription topics (`action-requests`, `action-results`, `system-events`) are stable — no inferred event names.
- ✅ **Section 4 (Multi-tenancy):** Tracker extracts tenant/user from inbound `EventEnvelope`. This pattern is unchanged; tenant context flows from the event payload, not from HTTP headers on the NATS consumer path.
- ✅ **Section 6 (Error Handling):** NATS reconnection errors are handled in `NATSClient`. Handler-level exceptions roll back the DB session (existing pattern retained).
- ✅ **Section 7 (Testing):** Unit tests mock the NATS client; integration tests verify end-to-end subscription with a real NATS server (Docker / pytest-docker).

---

## 1. Requirements & Core Objective

### Problem Statement (TECH-DEBT-001)

The Tracker Service currently depends on `soorma-core` (the SDK) to subscribe to events:

```
Current (WRONG):
  Tracker Service → EventClient (SDK) → HTTP/SSE → Event Service → NATS
```

This violates the architectural principle that **infrastructure services must not depend on the SDK**. The SDK is a developer-facing layer for building agent applications. Backend services should connect to the message bus directly.

```
Target (CORRECT):
  Tracker Service → NATSClient (soorma-nats lib) → NATS directly
```

### Acceptance Criteria

1. Tracker Service subscribes to NATS topics directly, with no dependency on `soorma-core` SDK.
2. A shared `soorma-nats` library (`libs/soorma-nats/`) provides the NATS client, usable by Tracker Service, Event Service (future migration), and any other infrastructure service.
3. Tracker Service receives and processes `action-requests`, `action-results`, and `system-events` correctly after the refactor.
4. All existing Tracker Service tests pass (event handler logic is unchanged).
5. New tests validate NATS subscription lifecycle (connect, receive, reconnect, disconnect).
6. `soorma-core` removed from `services/tracker/pyproject.toml` dependencies.
7. `NATS_URL` environment variable added; `EVENT_SERVICE_URL` removed from Tracker config (dead config — no other callers).
8. Event Service `NatsAdapter` extraction deferred to Stage 6 (see [DEFERRED_WORK.md](../../refactoring/DEFERRED_WORK.md#event-service-nats-adapter-extraction)).

---

## 2. Technical Design

**Components affected:**
- **New:** `libs/soorma-nats/` — shared NATS client library
- **Modified:** `services/tracker/` — remove SDK dependency, replace `EventClient` with `NATSClient`
- **No change:** Registry Service, SDK
- **Deferred to Stage 6:** Event Service `NatsAdapter` extraction to `soorma-nats` — cosmetic cleanup only, not a correctness fix; tracked in [DEFERRED_WORK.md](../../refactoring/DEFERRED_WORK.md#event-service-nats-adapter-extraction)

### Current Architecture (Before)

```
Tracker Service
├── pyproject.toml
│     └── soorma-core  ← SDK dependency (VIOLATION)
└── src/tracker_service/
    └── subscribers/
        └── event_handlers.py
              ├── from soorma.events import EventClient  ← SDK import (VIOLATION)
              └── EventClient.connect([ACTION_REQUESTS, ACTION_RESULTS, SYSTEM_EVENTS])
                      ↓ HTTP/SSE
              Event Service (:8082)
                      ↓
              NATS (:4222)
```

### Target Architecture (After)

```
libs/soorma-nats/                  ← NEW shared library
└── src/soorma_nats/
    ├── __init__.py
    ├── client.py                  NATSClient (connect, subscribe, disconnect)
    └── exceptions.py              NATSConnectionError, NATSSubscriptionError

services/tracker/
├── pyproject.toml
│     └── soorma-nats  ← replaces soorma-core  (NO SDK dependency)
└── src/tracker_service/
    └── subscribers/
        └── event_handlers.py
              ├── from soorma_nats import NATSClient  ← infrastructure import ✅
              └── NATSClient.subscribe(subjects, callback)
                      ↓ NATS protocol
              NATS (:4222)
```

### SDK Layer Verification

> ⚠️ This refactor does NOT touch any agent-facing SDK layer. Verification is provided to confirm no SDK API changes are introduced.

- **Service Client (Low-Level):** No `MemoryServiceClient`, `EventClient`, or `RegistryServiceClient` changes.
- **PlatformContext Wrapper (High-Level):** No changes to `context.memory`, `context.bus`, or `context.registry`.
- **Examples:** No examples reference Tracker Service internals — unaffected.
- **SDK Dependency Status:** `soorma-core` is being **removed** from `services/tracker/pyproject.toml`. This is the desired outcome.

**Conclusion:** No PlatformContext wrappers required. Zero impact on agent-developer APIs.

### Data Models

No new Pydantic models. Existing `EventEnvelope` from `soorma-common` is retained — the envelope is deserialized from the raw NATS message payload.

### NATS Subject Mapping

The Event Service uses a consistent subject namespace. Tracker will subscribe to the same subjects:

| Tracker Topic Constant | NATS Subject |
|---|---|
| `EventTopic.ACTION_REQUESTS` | `soorma.events.action-requests` |
| `EventTopic.ACTION_RESULTS` | `soorma.events.action-results` |
| `EventTopic.SYSTEM_EVENTS` | `soorma.events.system-events` |

**Subject prefix:** `soorma.events.` (matches `NatsAdapter._topic_to_subject()` in Event Service).

### `soorma-nats` Library Design

The library wraps `nats-py` and exposes a simple interface suitable for all infrastructure services.

```python
# libs/soorma-nats/src/soorma_nats/client.py

from typing import Callable, List, Awaitable
import nats

MessageCallback = Callable[[str, dict], Awaitable[None]]
"""Async callback: (subject: str, message: dict) -> None"""


class NATSClient:
    """
    Lightweight NATS client for Soorma infrastructure services.
    
    Wraps nats-py with:
    - Auto-reconnection (infinite retries by default)
    - JSON message deserialization
    - Subject namespace (soorma.events.*)
    - Graceful drain-and-disconnect on shutdown
    """
    
    def __init__(
        self,
        url: str = "nats://localhost:4222",
        reconnect_time_wait: int = 2,
        max_reconnect_attempts: int = -1,
    ) -> None: ...
    
    async def connect(self) -> None:
        """Connect to NATS server."""
        ...
    
    async def subscribe(
        self,
        topics: List[str],
        callback: MessageCallback,
        queue_group: str | None = None,
    ) -> str:
        """Subscribe to topics, returns subscription ID."""
        ...
    
    async def unsubscribe(self, subscription_id: str) -> None:
        """Unsubscribe from a subscription."""
        ...
    
    async def disconnect(self) -> None:
        """Drain and disconnect from NATS."""
        ...
    
    @property
    def is_connected(self) -> bool: ...
```

### `event_handlers.py` Refactor Design

The handler logic (database writes) is **unchanged** — only the subscription mechanism changes.

```python
# services/tracker/src/tracker_service/subscribers/event_handlers.py  (AFTER)

from soorma_nats import NATSClient                   # ← replaces EventClient
from soorma_common.events import EventEnvelope, EventTopic
import json

_nats_client: NATSClient | None = None


async def start_event_subscribers(nats_url: str) -> None:
    """Start NATS subscription for Tracker Service."""
    global _nats_client
    _nats_client = NATSClient(url=nats_url)
    await _nats_client.connect()
    
    async def _dispatch(subject: str, message: dict) -> None:
        """Route raw NATS messages to event handlers."""
        event = EventEnvelope.model_validate(message)
        topic = subject.removeprefix("soorma.events.")
        
        if topic == EventTopic.ACTION_REQUESTS.value:
            handler = handle_action_request
        elif topic == EventTopic.ACTION_RESULTS.value:
            handler = handle_action_result
        elif topic == EventTopic.SYSTEM_EVENTS.value:
            handler = handle_plan_event
        else:
            return
        
        await _create_db_handler(handler)(event)
    
    await _nats_client.subscribe(
        topics=[
            EventTopic.ACTION_REQUESTS.value,
            EventTopic.ACTION_RESULTS.value,
            EventTopic.SYSTEM_EVENTS.value,
        ],
        callback=_dispatch,
        queue_group="tracker-service",   # load-balance across tracker instances
    )


async def stop_event_subscribers() -> None:
    """Disconnect NATS client."""
    global _nats_client
    if _nats_client:
        await _nats_client.disconnect()
        _nats_client = None
```

### Configuration Change

`config.py` gains `nats_url` and retains `event_service_url` (for future if needed, or remove):

```python
# services/tracker/src/tracker_service/core/config.py  (change)
nats_url: str = os.environ.get("NATS_URL", "nats://localhost:4222")
```

`main.py` passes `settings.nats_url` to `start_event_subscribers()` instead of `settings.event_service_url`.

---

## 3. Task Tracking Matrix

### Task Sequence

| # | Task | Component | Estimated | Status |
|---|------|-----------|-----------|--------|
| T1 | Create `libs/soorma-nats/` library scaffold | libs | 2h | ⬜ Not started |
| T2 | Implement `NATSClient` in `soorma-nats` | libs | 3h | ⬜ Not started |
| T3 | Write unit tests for `NATSClient` (RED phase) | libs | 1h | ⬜ Not started |
| T4 | Write integration tests for `NATSClient` (RED phase) | libs | 1h | ⬜ Not started |
| T5 | Verify `NATSClient` tests pass (GREEN phase) | libs | 1h | ⬜ Not started |
| T6 | Stub `event_handlers.py` with `NATSClient` API (STUB phase) | tracker | 1h | ⬜ Not started |
| T7 | Write Tracker subscriber tests against real behavior (RED phase) | tracker | 2h | ⬜ Not started |
| T8 | Implement Tracker `start_event_subscribers` with NATS (GREEN phase) | tracker | 2h | ⬜ Not started |
| T9 | Update `config.py`, `main.py`, `pyproject.toml` | tracker | 0.5h | ⬜ Not started |
| T10 | Run full Tracker test suite, confirm all pass | tracker | 0.5h | ⬜ Not started |
| T11 | Update `CHANGELOG.md` for tracker and libs | docs | 0.5h | ⬜ Not started |

**Total:** ~14.5 hours (fits within 1.5-day estimate)

### Task 48H: FDE Decision

**FDE Option:** Skip `libs/soorma-nats/` extraction — embed NATS client code directly in Tracker Service.

- **Time Saved:** 2 hours (no library scaffold, no separate `pyproject.toml`)
- **Impact:** Low — creates duplication when Event Service also migrates (Phase 5/future work)
- **FDE Recommendation:** ✅ **ACCEPTABLE with approval** — Tracker and Event Service are the only consumers; inlining is pragmatic for a 15-day sprint. If deferred, add a TODO comment and Stage 6 task.
- **Default Plan:** Extract to `libs/soorma-nats/` (full scope, per Master Plan approval)

> ⚠️ Developer must approve FDE before inlining. Default implementation uses the shared library.

---

## 4. TDD Strategy

### TDD Cycle: `soorma-nats` Library

**STUB Phase:**
```python
# libs/soorma-nats/src/soorma_nats/client.py
class NATSClient:
    async def connect(self) -> None:
        raise NotImplementedError("NATSClient.connect not implemented")
    
    async def subscribe(self, topics, callback, queue_group=None) -> str:
        raise NotImplementedError("NATSClient.subscribe not implemented")
    
    async def disconnect(self) -> None:
        raise NotImplementedError("NATSClient.disconnect not implemented")
```

**RED Phase — Unit Tests** (`libs/soorma-nats/tests/test_nats_client.py`):
```python
@pytest.mark.asyncio
async def test_connect_raises_on_invalid_url():
    """NATSClient raises ConnectionError for unreachable server."""
    client = NATSClient(url="nats://nonexistent:4222", max_reconnect_attempts=1)
    with pytest.raises((ConnectionError, OSError)):
        await client.connect()

@pytest.mark.asyncio
async def test_subscribe_before_connect_raises():
    """subscribe() raises if not connected."""
    client = NATSClient()
    with pytest.raises(ConnectionError, match="Not connected"):
        await client.subscribe(["action-requests"], callback=AsyncMock())

@pytest.mark.asyncio
async def test_is_connected_false_before_connect():
    client = NATSClient()
    assert client.is_connected is False
```

**RED Phase — Integration Tests** (`libs/soorma-nats/tests/test_nats_integration.py`):

> Requires `NATS_URL` env var pointing to a live NATS server (Docker Compose in CI).

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_subscribe_and_receive_message(nats_url):
    """Subscribe to a topic and receive a published message."""
    received = []
    client = NATSClient(url=nats_url)
    await client.connect()
    
    async def on_message(subject: str, message: dict):
        received.append((subject, message))
    
    await client.subscribe(["action-requests"], on_message)
    
    # Publish test message using raw nats-py
    import nats, json
    pub = await nats.connect(nats_url)
    await pub.publish("soorma.events.action-requests", json.dumps({"test": True}).encode())
    await asyncio.sleep(0.1)
    await pub.close()
    
    assert len(received) == 1
    assert received[0][0] == "soorma.events.action-requests"
    assert received[0][1]["test"] is True
    
    await client.disconnect()
```

**GREEN Phase:** Replace `NotImplementedError` stubs with real implementation (adapted from `services/event-service/src/adapters/nats_adapter.py`).

---

### TDD Cycle: Tracker Service Refactor

**STUB Phase (`event_handlers.py`):**

Add `_nats_client` global and stub `start_event_subscribers` with NATS signature:
```python
async def start_event_subscribers(nats_url: str) -> None:
    """Start NATS subscription (stub)."""
    raise NotImplementedError("NATS integration not yet implemented")
```

**RED Phase** (`services/tracker/tests/test_nats_subscribers.py`):
```python
@pytest.mark.asyncio
async def test_start_subscribers_uses_nats_client(monkeypatch):
    """start_event_subscribers creates NATSClient and subscribes."""
    mock_nats = AsyncMock(spec=NATSClient)
    mock_nats.is_connected = True
    
    with patch("tracker_service.subscribers.event_handlers.NATSClient", return_value=mock_nats):
        await start_event_subscribers("nats://localhost:4222")
    
    mock_nats.connect.assert_awaited_once()
    mock_nats.subscribe.assert_awaited_once()
    
    # Verify subscribes to all three topics
    topics_arg = mock_nats.subscribe.call_args.kwargs.get("topics") or \
                 mock_nats.subscribe.call_args.args[0]
    assert "action-requests" in topics_arg
    assert "action-results" in topics_arg
    assert "system-events" in topics_arg

@pytest.mark.asyncio
async def test_stop_subscribers_disconnects_nats(monkeypatch):
    """stop_event_subscribers calls NATSClient.disconnect()."""
    mock_nats = AsyncMock(spec=NATSClient)
    
    # Inject mock into module global
    import tracker_service.subscribers.event_handlers as eh
    eh._nats_client = mock_nats
    
    await stop_event_subscribers()
    
    mock_nats.disconnect.assert_awaited_once()
    assert eh._nats_client is None

@pytest.mark.asyncio
async def test_dispatch_routes_action_request(monkeypatch):
    """Dispatcher routes action-requests topic to handle_action_request."""
    # Build a minimal ActionRequest event envelope
    event = EventEnvelope(
        id="test-id",
        type="test.action",
        topic=EventTopic.ACTION_REQUESTS,
        data={"action_id": "a1", "action_name": "test"},
        tenant_id="tenant-001",
        user_id="user-001",
    )
    
    with patch("tracker_service.subscribers.event_handlers.handle_action_request") as mock_handler, \
         patch("tracker_service.subscribers.event_handlers._create_db_handler") as mock_db:
        mock_db.return_value = AsyncMock()
        # Simulate dispatch call
        ...  # trigger _dispatch with action-requests subject
```

**Existing tests to verify remain GREEN:**
- `tests/test_subscribers.py` — update mocks to use `NATSClient` instead of `EventClient`
- `tests/test_query_api.py` — no NATS dependency; unchanged
- `tests/test_main.py` — update lifespan mock to pass `nats_url`

**Target test count:** 10+ new NATS tests + all existing 15+ tests passing.

---

## 5. Task Details

### T1: Create `libs/soorma-nats/` Scaffold

**Files to create:**
```
libs/soorma-nats/
├── README.md
├── pyproject.toml              # package: soorma-nats
└── src/
    └── soorma_nats/
        ├── __init__.py         # exports: NATSClient, NATSConnectionError, NATSSubscriptionError
        ├── client.py           # NATSClient class
        └── exceptions.py       # custom exceptions
tests/
├── __init__.py
├── conftest.py                 # nats_url fixture (from env or default)
├── test_nats_client.py         # unit tests (mock nats-py)
└── test_nats_integration.py    # integration tests (live NATS)
```

**`pyproject.toml` dependencies:**
```toml
[project]
name = "soorma-nats"
version = "0.1.0"
description = "Shared NATS client for Soorma infrastructure services"
requires-python = ">=3.11"
dependencies = [
    "nats-py>=2.6.0",
    "soorma-common",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.1.0",
    "ruff>=0.1.0",
]
```

---

### T2: Implement `NATSClient`

**Source:** Adapted from `services/event-service/src/adapters/nats_adapter.py`.

**Differences from `NatsAdapter`:**
- Simpler API: `subscribe(topics, callback, queue_group)` vs `subscribe(topics, handler, subscription_id, queue_group)`
- No `publish()` method (Tracker is subscribe-only)
- No abstract base class dependency (standalone library)
- `MessageCallback` type: `async (subject: str, message: dict) -> None`
- Subject prefix: `soorma.events.` (same as Event Service)

**`exceptions.py`:**
```python
class NATSConnectionError(Exception):
    """Raised when NATS connection fails or is lost."""
    pass

class NATSSubscriptionError(Exception):
    """Raised when NATS subscription fails."""
    pass
```

**`__init__.py` exports:**
```python
from .client import NATSClient
from .exceptions import NATSConnectionError, NATSSubscriptionError

__all__ = ["NATSClient", "NATSConnectionError", "NATSSubscriptionError"]
```

---

### T6–T8: Tracker Service Refactor

**`event_handlers.py` changes:**
1. Remove: `from soorma.events import EventClient`
2. Add: `from soorma_nats import NATSClient`
3. Replace `_event_client: Optional[Any]` with `_nats_client: NATSClient | None = None`
4. Replace `start_event_subscribers(event_service_url: str)` signature with `start_event_subscribers(nats_url: str)`
5. Replace `EventClient` instantiation and `.connect()` / `.on_all_events` / `.disconnect()` pattern with `NATSClient` pattern
6. Retain `_create_db_handler`, `_extract_tenant_user`, and all three handler functions **unchanged**

**`config.py` changes:**
```python
# ADD
nats_url: str = os.environ.get("NATS_URL", "nats://localhost:4222")

# REMOVE — dead config after refactor, no other callers in Tracker
# event_service_url: str = os.environ.get("EVENT_SERVICE_URL", "http://localhost:8082")
```

**`main.py` changes:**
```python
# BEFORE
await start_event_subscribers(settings.event_service_url)

# AFTER
await start_event_subscribers(settings.nats_url)
```

**`pyproject.toml` changes:**
```toml
# REMOVE
"soorma-core",        # SDK for event bus subscription

# ADD  
"soorma-nats",        # Shared NATS client for infrastructure services
```

---

### T11: Changelog Updates

**`libs/soorma-nats/CHANGELOG.md`** (new file):
```markdown
# Changelog — soorma-nats

## v0.1.0 (2026-03)
- Initial release: NATSClient for Soorma infrastructure services
- Extracted from Event Service NatsAdapter pattern
- Used by Tracker Service (replaces SDK EventClient dependency)
```

**`services/tracker/CHANGELOG.md`** (add entry):
```markdown
## v0.8.1 (Unreleased)
### Changed
- **TECH-DEBT-001:** Replace `soorma-core` (SDK) dependency with `soorma-nats` (infrastructure library)
- Tracker Service now subscribes to NATS directly instead of via Event Service HTTP/SSE
- Add `NATS_URL` environment variable (default: `nats://localhost:4222`)

### Removed
- `EVENT_SERVICE_URL` no longer used for event subscriptions (may be removed in future)
- `soorma-core` removed from runtime dependencies
```

---

## 6. Forward Deployed Logic Decision

**FDE Option:** Inline NATS client code into Tracker Service (skip `libs/soorma-nats/`).

| Criterion | Full Scope (libs/soorma-nats/) | FDE (inline) |
|---|---|---|
| Time | 14.5h | 12h |
| Reusability | Event Service can adopt same lib | Duplication risk |
| Maintenance | Single place for NATS config | Two files to update |
| Risk | Low — lib scaffold is straightforward | Low — simpler scope |

**Decision:** Full scope (create `soorma-nats` library) — approved in Master Plan Option C. 

> ⚠️ If developer wishes to change to FDE/inline, explicit approval required before implementation starts. FDE approach requires adding a `# TODO(Stage 6): Extract to soorma-nats library` comment.

---

## 7. Wrapper Completeness Checklist

> This phase makes NO changes to agent-facing SDK methods.

- [x] `context.registry` — unchanged (Phases 1–3)
- [x] `context.memory` — unchanged (Stage 2)
- [x] `context.bus` — unchanged (Stage 1)
- [x] No new service endpoints in Registry, Memory, or Event Service
- [x] Tracker Service has no SDK-facing API; it is a pure infrastructure service
- [x] `soorma-nats` library is **not** imported by agent code — internal service use only
- [x] Examples affected: **none** — examples never reference Tracker Service internals

---

## 8. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| NATS subject mismatch between Event Service and Tracker | Low | High | Verify `soorma.events.*` prefix in both; add integration test publishing from Event Service side |
| Queue group causes message loss during cutover | Low | Medium | Use `queue_group="tracker-service"` only when multiple Tracker instances run; single-instance dev mode can omit |
| Existing event handler tests break due to mock change | Medium | Low | Update mocks from `EventClient` to `NATSClient` (same interface in tests) |
| NATS reconnection loop during Tracker startup if NATS not ready | Low | Low | `max_reconnect_attempts=-1` (infinite); service starts and retries continuously |
| Missing `NATS_URL` env var in existing Docker Compose | Medium | Low | Provide default `nats://nats:4222` matching Docker Compose service name |

---

## 9. Docker Compose / Deployment Notes

**Environment variable change:**

| Service | Old Var | New Var | Notes |
|---|---|---|---|
| `tracker` | `EVENT_SERVICE_URL=http://event-service:8082` | `NATS_URL=nats://nats:4222` | Replace in `docker-compose.yml` |

**`docker-compose.yml` tracker entry (after):**
```yaml
tracker:
  environment:
    - NATS_URL=nats://nats:4222
    - DATABASE_URL=postgresql+asyncpg://soorma:soorma@postgres:5432/tracker
```

> Event Service continues to use NATS internally — no change to Event Service deployment.

---

## 10. Success Criteria

- [ ] `soorma-nats` library installable via `pip install -e libs/soorma-nats`
- [ ] `NATSClient.connect()` / `subscribe()` / `disconnect()` work with real NATS server
- [ ] `libs/soorma-nats/tests/` achieves 100% coverage of `client.py`
- [ ] `services/tracker/pyproject.toml` no longer lists `soorma-core` as a dependency
- [ ] `from soorma.events import EventClient` does **not** appear in Tracker Service source
- [ ] All existing Tracker Service tests pass
- [ ] 10+ new NATS subscriber tests pass (unit + integration)
- [ ] Tracker Service starts successfully in Docker Compose with NATS
- [ ] `CHANGELOG.md` updated for both `soorma-nats` (new) and `tracker-service` (modified)
- [ ] `EVENT_SERVICE_URL` does not appear in `services/tracker/src/` after refactor

---

## 11. Related Documents

- [MASTER_PLAN_Enhanced_Discovery.md](MASTER_PLAN_Enhanced_Discovery.md) — Phase 4 section
- [docs/ARCHITECTURE_PATTERNS.md](../../ARCHITECTURE_PATTERNS.md) — Sections 1, 2, 6, 7
- [services/event-service/src/adapters/nats_adapter.py](../../../services/event-service/src/adapters/nats_adapter.py) — Source pattern for NATSClient implementation
- [services/tracker/src/tracker_service/subscribers/event_handlers.py](../../../services/tracker/src/tracker_service/subscribers/event_handlers.py) — File being refactored
- [services/tracker/pyproject.toml](../../../services/tracker/pyproject.toml) — Dependency being removed

---

**Plan Author:** GitHub Copilot  
**Awaiting Developer Approval:** ⏳ Yes — do NOT begin implementation until this plan is committed.
