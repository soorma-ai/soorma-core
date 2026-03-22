# Domain Entities — services/registry (U3)
## Initiative: Multi-Tenancy Model Implementation
**Date**: 2026-03-22

---

## ORM Model Changes

### AgentTable (`registry_service/models/agent.py`)

**Changed column** (all other columns unchanged):

| Attribute | Before | After |
|---|---|---|
| Column name | `tenant_id` | `platform_tenant_id` |
| SQLAlchemy type | `Uuid(as_uuid=True, native_uuid=True)` | `String(64)` |
| Python annotation | `Mapped[UUID]` | `Mapped[str]` |
| Import | `from uuid import UUID` (needed) | Remove if UUID unused elsewhere in file |

```python
# Before
tenant_id: Mapped[UUID] = mapped_column(
    Uuid(as_uuid=True, native_uuid=True),
    nullable=False,
    index=True,
    comment="Developer tenant identifier ..."
)

# After
platform_tenant_id: Mapped[str] = mapped_column(
    String(64),
    nullable=False,
    index=True,
    comment="Platform tenant identifier — opaque string, no UUID format enforced"
)
```

---

### EventTable (`registry_service/models/event.py`)

**Changed column** (all other columns unchanged):

| Attribute | Before | After |
|---|---|---|
| Column name | `tenant_id` | `platform_tenant_id` |
| SQLAlchemy type | `Uuid(as_uuid=True, native_uuid=True)` | `String(64)` |
| Python annotation | `Mapped[UUID]` | `Mapped[str]` |

**Changed `__table_args__`** — the `UniqueConstraint` implicit in the DB (from migration 003) referenced `tenant_id`; migration 004 recreates it as `(event_name, platform_tenant_id)`. No explicit `__table_args__` change needed in the ORM model (constraint is already `()` in the current code) — the DB-level constraint is managed by Alembic.

---

### PayloadSchemaTable (`registry_service/models/schema.py`)

**Changed column** (all other columns unchanged):

| Attribute | Before | After |
|---|---|---|
| Column name | `tenant_id` | `platform_tenant_id` |
| SQLAlchemy type | `Uuid(as_uuid=True, native_uuid=True)` | `String(64)` |
| Python annotation | `Mapped[UUID]` | `Mapped[str]` |

---

## CRUD Method Signatures

### AgentCRUD (`registry_service/crud/agents.py`)

All methods that previously accepted `developer_tenant_id: UUID` now accept `platform_tenant_id: str`:

```python
# Before
async def create_agent(self, db, agent, developer_tenant_id: UUID) -> AgentTable
async def update_agent(self, db, agent_id, developer_tenant_id: UUID, ...) -> Optional[AgentTable]
async def get_agent(self, db, agent_id, developer_tenant_id: UUID) -> Optional[AgentTable]
async def get_agents_by_tenant(self, db, developer_tenant_id: UUID) -> List[AgentTable]
async def delete_agent(self, db, agent_id, developer_tenant_id: UUID) -> bool
# (and any other methods with tenant_id: UUID parameter)

# After — same signatures with str instead of UUID
async def create_agent(self, db, agent, platform_tenant_id: str) -> AgentTable
async def update_agent(self, db, agent_id, platform_tenant_id: str, ...) -> Optional[AgentTable]
async def get_agent(self, db, agent_id, platform_tenant_id: str) -> Optional[AgentTable]
async def get_agents_by_tenant(self, db, platform_tenant_id: str) -> List[AgentTable]
async def delete_agent(self, db, agent_id, platform_tenant_id: str) -> bool
```

### EventCRUD (`registry_service/crud/events.py`)

```python
# Before
async def create_event(self, db, event, developer_tenant_id: UUID) -> EventTable
async def upsert_event(self, db, event, developer_tenant_id: UUID) -> tuple[EventTable, bool]
async def get_event_by_name(self, db, event_name, developer_tenant_id: UUID) -> Optional[EventTable]
# etc.

# After
async def create_event(self, db, event, platform_tenant_id: str) -> EventTable
async def upsert_event(self, db, event, platform_tenant_id: str) -> tuple[EventTable, bool]
async def get_event_by_name(self, db, event_name, platform_tenant_id: str) -> Optional[EventTable]
```

### SchemaCRUD (`registry_service/crud/schemas.py`)

```python
# Before
async def create_schema(self, db, schema, tenant_id: UUID) -> PayloadSchemaTable
async def get_schema_by_name_version(self, db, schema_name, version, tenant_id: UUID) -> ...
# etc.

# After
async def create_schema(self, db, schema, platform_tenant_id: str) -> PayloadSchemaTable
async def get_schema_by_name_version(self, db, schema_name, version, platform_tenant_id: str) -> ...
```

---

## Route Handler DB Dependency

### All `registry_service/api/v1/*.py` route handlers

Every route handler that touches the DB MUST switch from `Depends(get_db)` to `Depends(get_tenanted_db)`:

```python
# Before
from ...core.database import get_db
...
async def register_agent(
    request: AgentRegistrationRequest,
    db: AsyncSession = Depends(get_db),
    platform_tenant_id: str = Depends(get_platform_tenant_id)
):

# After
from soorma_service_common.dependencies import get_tenanted_db
...
async def register_agent(
    request: AgentRegistrationRequest,
    db: AsyncSession = Depends(get_tenanted_db),
    platform_tenant_id: str = Depends(get_platform_tenant_id)
):
```

This applies to all endpoints in `agents.py`, `events.py`, and `schemas.py`.

---

## API Dependency Entity

### `registry_service/api/dependencies.py`

```python
# Before — entire file
from uuid import UUID
from fastapi import Header, HTTPException, status

async def get_developer_tenant_id(x_tenant_id: str = Header(...)) -> UUID:
    try:
        return UUID(x_tenant_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=...)

# After — entire file replaced
from soorma_service_common.dependencies import get_platform_tenant_id

# get_platform_tenant_id is re-exported here so existing import paths
# inside Registry route files continue to work unchanged:
#   from ..dependencies import get_platform_tenant_id
__all__ = ["get_platform_tenant_id"]
```

Re-exporting via `dependencies.py` preserves existing import paths in `api/v1/agents.py`, `api/v1/events.py`, `api/v1/schemas.py` — no changes needed in those files beyond the parameter type annotation.

---

## Configuration Entity

### `registry_service/core/config.py` — Settings class

**Removed fields**:
```python
IS_LOCAL_TESTING: bool         # removed
SYNC_DATABASE_URL: str         # removed
DB_INSTANCE_CONNECTION_NAME    # removed
DB_USER                        # removed
DB_NAME                        # removed
DB_PASS_PATH                   # removed
```

**Updated field default**:
```python
# Before
DATABASE_URL: str = "sqlite+aiosqlite:///./registry.db"

# After
DATABASE_URL: str = "postgresql+asyncpg://soorma:soorma@localhost:5432/registry"
```

---

## Database Engine Entity

### `registry_service/core/database.py` — `create_db_engine()`

**Before**: multi-branch function with SQLite / Cloud SQL URL assembly (~30 lines)

**After**:
```python
def create_db_engine():
    """Creates SQLAlchemy async engine from DATABASE_URL setting. PostgreSQL only."""
    return create_async_engine(
        settings.DATABASE_URL,
        poolclass=NullPool,
        future=True,
        echo=False,
    )
```

`create_db_url()` helper function is removed entirely.

---

## Alembic Migration Entity

### `alembic/versions/004_tenant_id_uuid_to_varchar.py`

**Revision chain**: follows migration 003 (schema_registry)

**Tables affected**: `agents`, `events`, `payload_schemas`

**Operations per table** (agents shown; identical pattern for events and payload_schemas):
```python
# 1. Drop unique constraint referencing old column name
op.drop_constraint("uq_agents_agent_id_tenant_id", "agents", type_="unique")

# 2. Rename column
op.alter_column("agents", "tenant_id", new_column_name="platform_tenant_id")

# 3. Change type
op.alter_column(
    "agents",
    "platform_tenant_id",
    existing_type=sa.dialects.postgresql.UUID(as_uuid=True),
    type_=sa.String(64),
    postgresql_using="platform_tenant_id::text",
)

# 4. Recreate unique constraint with new column name
op.create_unique_constraint(
    "uq_agents_agent_id_platform_tenant_id",
    "agents",
    ["agent_id", "platform_tenant_id"],
)
```

**Downgrade**: `pass` (no-op — pre-release, no production data)

---

## Test Fixture Entity

### `tests/conftest.py` — sentinel and fixture changes

```python
# Before
TEST_TENANT_ID = UUID("00000000-0000-0000-0000-000000000000")
os.environ["IS_LOCAL_TESTING"] = "true"

# After
TEST_TENANT_ID = "spt_00000000-0000-0000-0000-000000000000"
# IS_LOCAL_TESTING line removed

# client fixture — no change needed (TEST_TENANT_ID is already used as str in headers)
with TestClient(app, headers={"X-Tenant-ID": TEST_TENANT_ID}) as test_client:
    yield test_client
```
