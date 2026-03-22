# Tech Stack Decisions — soorma-service-common (U2)
## Initiative: Multi-Tenancy Model Implementation
**Date**: 2026-03-22

---

## Overview

`libs/soorma-service-common` is a pure infrastructure library. No new technology choices required — it builds on the same stack already in use across all soorma-core backend services.

---

## TS-U2-01: Web Framework — FastAPI / Starlette

**Decision**: Use FastAPI (`fastapi>=0.104.0`) and Starlette (`starlette`) for middleware and dependency interfaces.
**Rationale**: All consuming services (Memory, Tracker, Registry, Event Service) use FastAPI. `TenancyMiddleware` inherits from `starlette.middleware.base.BaseHTTPMiddleware` — the same base used by the existing per-service middleware implementations it replaces.
**Alternative considered**: Plain ASGI middleware (no Starlette base class). Rejected — would require reimplementing request/response handling that `BaseHTTPMiddleware` provides for free.

---

## TS-U2-02: ORM / Database — SQLAlchemy Async

**Decision**: Use `sqlalchemy[asyncio]>=2.0.0` with `asyncpg` driver for all DB interactions.
**Rationale**: All services already use SQLAlchemy 2.x async. `get_tenanted_db` works with `AsyncSession` from SQLAlchemy's async session factory. No per-service database abstraction — the `AsyncSession` type is the contract.
**Note**: `soorma-service-common` does NOT define an engine, session factory, or `get_db` — those remain in each consuming service's `core/database.py`. `soorma-service-common` only depends on the `AsyncSession` type.

---

## TS-U2-03: Library Build Tool — Hatchling / Poetry

**Decision**: Use `hatchling` as the build backend (consistent with `libs/soorma-common`).
**Rationale**: `libs/soorma-common` uses hatchling with the `pyproject.toml` / `src/` layout. `soorma-service-common` follows the same structure for consistency and to enable the same `pip install -e .` workflow used by services.

---

## TS-U2-04: Python Version

**Decision**: `requires-python = ">=3.11"` (same as all other libraries and services)
**Rationale**: No deviation; all soorma-core code targets Python 3.11+.

---

## TS-U2-05: No New Dependencies Beyond FastAPI + SQLAlchemy

**Decision**: `pyproject.toml` dependencies are limited to: `fastapi`, `sqlalchemy[asyncio]`, `soorma-common`.
**Rationale**: The library does header reads, async SQL calls, and ABC definition — all covered by these three packages. No additional packages needed.
**Note**: `asyncpg` is NOT a direct dependency of `soorma-service-common` — it is the driver used by consuming services. The library interacts with `AsyncSession` only.

---

## Dependency Matrix

| Package | Purpose | Already in services? |
|---------|---------|---------------------|
| `fastapi>=0.104.0` | `Request`, `Depends`, `BaseHTTPMiddleware` | Yes (all services) |
| `sqlalchemy[asyncio]>=2.0.0` | `AsyncSession`, `text()` for `set_config` | Yes (memory, tracker) |
| `soorma-common` | `DEFAULT_PLATFORM_TENANT_ID` | Yes (all services) |

---

## Testing Stack

| Package | Purpose |
|---------|---------|
| `pytest>=7.0.0` | Test runner |
| `pytest-asyncio>=0.21.0` | Async test support |
| `httpx>=0.25.0` | Test client (for integration tests via FastAPI TestClient) |
| `pytest-cov>=4.1.0` | Coverage reporting |
