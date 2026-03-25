# Tech Stack Decisions — U7: services/event-service
## Initiative: Multi-Tenancy Model Implementation
**Date**: 2026-03-25

---

## Existing Stack (unchanged)

| Component | Technology | Version / Details | Decision |
|-----------|-----------|------------------|----------|
| API framework | FastAPI | existing | No change |
| ASGI / request context | Starlette / FastAPI dependency injection | existing | Keep and extend with shared identity dependency |
| Event transport | Event manager + configured adapter (NATS / memory adapter) | existing | No change |
| DTO validation | Pydantic via `soorma-common` | existing | Keep |
| Test framework | pytest + existing event-service test suite | existing | Extend |
| Logging | Python logging | existing | Keep, tighten metadata logging behavior |

---

## New Dependencies

| Dependency | Source | Purpose |
|-----------|--------|---------|
| `soorma-service-common` | `libs/soorma-service-common/` (workspace) | `TenancyMiddleware`, `get_platform_tenant_id` dependency, future auth abstraction boundary |

**Add to service dependency configuration**:
- workspace/path dependency on `soorma-service-common`

---

## Removed / Avoided Approaches

| Approach | Reason |
|---------|--------|
| Direct header parsing in `publish_event` | Rejected in favor of dependency injection for future auth evolution |
| Per-producer metadata trust for `platform_tenant_id` | Rejected due to spoofing risk |
| Truncation of oversized IDs | Rejected; fail-closed validation is safer |
| Optional `tenant_id` on some events | Rejected; all events must carry explicit service-tenant scope |
| Optional `user_id` on some events | Rejected; all events must remain attributable to a human or machine actor identity |

---

## Security Controls in Use

| Control | Implementation | Activation |
|---------|---------------|-----------|
| Platform identity injection | `Depends(get_platform_tenant_id)` + overwrite before publish | Per publish request |
| Metadata sanitization | trim + empty-to-None + len<=64 validation | Per publish request |
| Anti-spoofing | unconditional overwrite of payload `platform_tenant_id` | Per publish request |
| Fail-closed validation | reject invalid schema/metadata before `event_manager.publish` | Per publish request |
| Transitional default platform tenant | `DEFAULT_PLATFORM_TENANT_ID` fallback | Temporary, until identity service hardening |

---

## Testing Decisions

| Test Area | Decision |
|----------|----------|
| Publish route tests | Extend existing API tests for injected platform tenant and overwrite semantics |
| Validation tests | Add cases for oversized IDs, empty-string normalization, and missing required `tenant_id` / `user_id` |
| Compatibility tests | Preserve SDK compatibility for `tenant_id` / `user_id` semantics |
| Integration tests | Verify shared middleware/dependency resolves platform tenant and reaches bus payload |

---

## Future-Proofing Notes

- The DI boundary is intentional so the route does not care whether platform identity comes from `X-Tenant-ID`, API key, JWT claims, or another service-auth mechanism.
- Event Service remains transport/auth boundary only; no database or persistent identity cache is introduced.
- When Identity Service lands, fallback to `DEFAULT_PLATFORM_TENANT_ID` should be removed without changing endpoint behavior contract.
