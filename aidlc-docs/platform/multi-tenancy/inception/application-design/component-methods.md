# Component Methods
## Initiative: Multi-Tenancy Model Implementation
**Date**: 2026-03-22

> Method signatures and high-level purpose. Detailed business logic and implementation rules are defined per-unit in Functional Design (Construction Phase).

---

## C1 — `libs/soorma-common`

### `soorma_common/tenancy.py` (new module)

```python
# Runtime-overridable default platform tenant constant
DEFAULT_PLATFORM_TENANT_ID: str  # = "spt_00000000-0000-0000-0000-000000000000"
# Read from SOORMA_PLATFORM_TENANT_ID env var if set; otherwise uses the literal default
# WARNING: For development/testing only. MUST NOT be used after Identity Service is implemented.
```

*(No callable methods — constant and env-var resolution only)*

---

## C2 — `libs/soorma-service-common`

### `soorma_service_common/middleware.py`

```python
class TenancyMiddleware(BaseHTTPMiddleware):
    """
    Starlette middleware that extracts identity dimensions from HTTP headers
    and stores them on request.state per request.
    Does NOT call set_config (DB not available in middleware scope — see get_tenanted_db).
    """
    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """
        Extract X-Tenant-ID → request.state.platform_tenant_id (default: DEFAULT_PLATFORM_TENANT_ID)
        Extract X-Service-Tenant-ID → request.state.service_tenant_id (default: None)
        Extract X-User-ID → request.state.service_user_id (default: None)
        Then call call_next(request).
        """
        ...
```

### `soorma_service_common/dependencies.py`

```python
def get_platform_tenant_id(request: Request) -> str:
    """Read platform_tenant_id from request.state (set by TenancyMiddleware). Returns str."""
    ...

def get_service_tenant_id(request: Request) -> Optional[str]:
    """Read service_tenant_id from request.state. Returns None if not set."""
    ...

def get_service_user_id(request: Request) -> Optional[str]:
    """Read service_user_id from request.state. Returns None if not set."""
    ...

async def get_tenanted_db(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency: wraps get_db and calls set_config for all three session
    variables before yielding, activating RLS policies for the request's DB transaction.

    Calls (within the same transaction):
        set_config('app.platform_tenant_id', platform_tenant_id, true)
        set_config('app.service_tenant_id',  service_tenant_id or '',  true)
        set_config('app.service_user_id',    service_user_id or '',    true)

    Services use this dependency instead of bare get_db wherever RLS must be enforced.
    Input: request.state values set by TenancyMiddleware.
    Yields: AsyncSession with session variables active.
    """
    ...
```

### `soorma_service_common/deletion.py`

```python
class PlatformTenantDataDeletion(ABC):
    """
    Abstract base for GDPR-compliant data deletion scoped to the platform tenant namespace.
    Concrete implementations: MemoryDataDeletion (memory service), TrackerDataDeletion (tracker service).
    All methods execute within a single DB transaction; return count of deleted rows.
    """

    @abstractmethod
    async def delete_by_platform_tenant(
        self,
        db: AsyncSession,
        platform_tenant_id: str,
    ) -> int:
        """Delete ALL rows across ALL covered tables for a platform tenant. Returns total row count deleted."""
        ...

    @abstractmethod
    async def delete_by_service_tenant(
        self,
        db: AsyncSession,
        platform_tenant_id: str,
        service_tenant_id: str,
    ) -> int:
        """Delete all rows for a service tenant within a platform tenant's namespace. Returns row count."""
        ...

    @abstractmethod
    async def delete_by_service_user(
        self,
        db: AsyncSession,
        platform_tenant_id: str,
        service_tenant_id: str,
        service_user_id: str,
    ) -> int:
        """Delete all rows for a specific service user. Returns row count."""
        ...
```

---

## C3 — `services/registry`

### `registry_service/api/dependencies.py` (updated)

```python
# get_developer_tenant_id() is REMOVED — replaced by get_platform_tenant_id from soorma-service-common
# All Registry endpoints now use:
#   platform_tenant_id: str = Depends(get_platform_tenant_id)
# from soorma_service_common.dependencies
```

### `registry_service/core/database.py` (updated)

```python
def create_db_engine() -> AsyncEngine:
    """
    Creates SQLAlchemy async engine.
    PostgreSQL only — IS_LOCAL_TESTING/SQLite path removed.
    Uses DATABASE_URL env var (postgresql+asyncpg://...).
    """
    ...
```

*(All CRUD and service layer methods retain their existing signatures; only `tenant_id` type changes from `UUID` → `str` in call sites and ORM columns)*

---

## C4 — `services/memory`

### `memory_service/services/data_deletion.py` (new)

```python
class MemoryDataDeletion(PlatformTenantDataDeletion):
    """
    Concrete GDPR deletion implementation for Memory Service.
    Covers: semantic_memory, episodic_memory, procedural_memory,
            working_memory, task_context, plan_context.
    """

    async def delete_by_platform_tenant(
        self,
        db: AsyncSession,
        platform_tenant_id: str,
    ) -> int:
        """Delete all memory rows for a platform tenant across all 6 tables."""
        ...

    async def delete_by_service_tenant(
        self,
        db: AsyncSession,
        platform_tenant_id: str,
        service_tenant_id: str,
    ) -> int:
        """Delete all memory rows for a service tenant within a platform tenant namespace."""
        ...

    async def delete_by_service_user(
        self,
        db: AsyncSession,
        platform_tenant_id: str,
        service_tenant_id: str,
        service_user_id: str,
    ) -> int:
        """Delete all memory rows for a specific service user."""
        ...
```

### `memory_service/core/dependencies.py` (updated)

```python
class TenantContext:
    """Encapsulates full three-dimension identity with DB session."""
    platform_tenant_id: str
    service_tenant_id: Optional[str]
    service_user_id: Optional[str]
    db: AsyncSession

async def get_tenant_context(
    request: Request,
    db: AsyncSession = Depends(get_tenanted_db),  # get_tenanted_db from soorma-service-common
) -> TenantContext:
    """
    Dependency combining identity extraction with DB session that has set_config active.
    Replaces current UUID-parsing TenantContext.
    Raises HTTP 422 if service_user_id is required but absent (per endpoint).
    """
    ...
```

*(Existing CRUD method signatures retain their shape; `tenant_id: UUID` and `user_id: UUID` parameters change to `platform_tenant_id: str`, `service_tenant_id: str`, `service_user_id: str` — detail in Functional Design per unit)*

---

## C5 — `services/tracker`

### `tracker_service/services/data_deletion.py` (new)

```python
class TrackerDataDeletion(PlatformTenantDataDeletion):
    """
    Concrete GDPR deletion implementation for Tracker Service.
    Covers: plan_progress, action_progress.
    """

    async def delete_by_platform_tenant(
        self,
        db: AsyncSession,
        platform_tenant_id: str,
    ) -> int:
        """Delete all tracker rows for a platform tenant across both tables."""
        ...

    async def delete_by_service_tenant(
        self,
        db: AsyncSession,
        platform_tenant_id: str,
        service_tenant_id: str,
    ) -> int:
        """Delete all tracker rows for a service tenant within a platform tenant namespace."""
        ...

    async def delete_by_service_user(
        self,
        db: AsyncSession,
        platform_tenant_id: str,
        service_tenant_id: str,
        service_user_id: str,
    ) -> int:
        """Delete all tracker rows for a specific service user."""
        ...
```

### `tracker_service/subscribers/event_handlers.py` (updated)

```python
async def handle_action_request(event: EventEnvelope, db: AsyncSession) -> None:
    """
    Upsert ActionProgress row for an incoming action-request event.
    platform_tenant_id: from DEFAULT_PLATFORM_TENANT_ID (NATS path — no auth context yet)
    service_tenant_id: from event.tenant_id
    service_user_id: from event.user_id
    """
    ...

async def handle_action_result(event: EventEnvelope, db: AsyncSession) -> None:
    """
    Update ActionProgress status on action-result event.
    Same tenant extraction as handle_action_request.
    """
    ...

async def handle_plan_event(event: EventEnvelope, db: AsyncSession) -> None:
    """
    Upsert/update PlanProgress on system-event (plan lifecycle).
    Same tenant extraction as handle_action_request.
    """
    ...
```

---

## C6 — `sdk/python` — `MemoryServiceClient` (low-level, updated)

```python
class MemoryClient:  # (the low-level client, not the PlatformContext wrapper)
    def __init__(
        self,
        base_url: str = "http://localhost:8083",
        timeout: float = 30.0,
        platform_tenant_id: Optional[str] = None,  # NEW: init-time; defaults to DEFAULT_PLATFORM_TENANT_ID / env var
    ):
        """
        platform_tenant_id is set once at init — sent as X-Tenant-ID on every request.
        Per-request methods accept service_tenant_id / service_user_id (renamed from tenant_id / user_id).
        """
        ...

    # Representative per-call signature (all methods follow same pattern):
    async def store_knowledge(
        self,
        content: str,
        service_user_id: str,           # renamed from user_id
        service_tenant_id: str,         # renamed from tenant_id (new explicit param)
        external_id: Optional[str] = None,
        is_public: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        source: Optional[str] = None,
    ) -> SemanticMemoryResponse:
        """X-Tenant-ID sent automatically from self.platform_tenant_id."""
        ...
```

## C6 — `sdk/python` — `TrackerServiceClient` (low-level, updated)

```python
class TrackerServiceClient:
    def __init__(
        self,
        base_url: str = "http://localhost:8084",
        timeout: float = 30.0,
        platform_tenant_id: Optional[str] = None,  # NEW: init-time
    ):
        ...

    async def get_plan_progress(
        self,
        plan_id: str,
        service_tenant_id: str,     # renamed from tenant_id
        service_user_id: str,       # renamed from user_id
    ) -> Optional[PlanProgress]:
        """X-Tenant-ID sent automatically from self.platform_tenant_id."""
        ...
```

---

## C7 — `sdk/python` — PlatformContext `MemoryClient` wrapper (updated)

```python
@dataclass
class MemoryClient:  # (the PlatformContext wrapper in context.py)

    async def retrieve(
        self,
        key: str,
        plan_id: Optional[str] = None,
        service_tenant_id: str = None,      # renamed from tenant_id
        service_user_id: str = None,        # renamed from user_id
    ) -> Optional[Any]:
        """
        platform_tenant_id is never a parameter here — it's set on the underlying
        MemoryServiceClient at init time. Agent handlers pass service_tenant_id /
        service_user_id from the event envelope.
        """
        ...

    async def store(
        self,
        key: str,
        value: Any,
        plan_id: Optional[str] = None,
        service_tenant_id: str = None,
        service_user_id: str = None,
    ) -> None:
        ...

    # All other wrapper methods follow the same (service_tenant_id, service_user_id) pattern.
    # store_task_context, get_task_context, update_task_context, delete_task_context,
    # store_knowledge, search_knowledge, log_interaction, get_recent_history, etc.
```
