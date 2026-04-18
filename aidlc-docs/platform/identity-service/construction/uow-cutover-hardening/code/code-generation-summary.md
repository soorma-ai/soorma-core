# Code Generation Summary - uow-cutover-hardening

## Scope Completed
- Hardened shared tenancy middleware so secured non-public routes require bearer JWTs, preserve the trusted admin-key exception for identity control-plane paths, and prefer canonical `tenant_id` claims over compatibility aliases.
- Updated low-level SDK Memory and Tracker clients so the active bearer-auth path sends `Authorization` without legacy `X-*` identity headers.
- Extended SDK auth, event, registry, platform-context, and base-agent wiring so infrastructure traffic can carry bearer JWTs through the same wrapper/client surfaces used by agents and examples, including async token-provider/factory support for requesting, caching, and refreshing JWTs.
- Added canonical `tenant_id` issuance in identity-service tokens while preserving compatibility claims for bounded migration.
- Switched `soorma dev` local bootstrap from HS256-secret defaults to persisted `.soorma/identity/` RSA key material with inline JWKS/public-key verifier material derived from those files.
- Added a shared example auth helper and persisted local JWT bootstrap flow so `examples/01-hello-world` can onboard once, reuse stored principal metadata, expose a reusable trusted-proxy style token provider, surface the bootstrapped platform tenant and admin principal identifiers, and inject bearer tokens into infrastructure-facing clients without per-example bootstrap shims or hard-coded tenant IDs.
- Applied the same shared example auth-provider pattern to `examples/01-hello-tool`, including startup bootstrap priming, client-side bearer-token injection, and tool initialization with the shared provider.
- Applied the shared example auth-provider pattern across the remaining example suite so each example `start.sh` primes bootstrap state, each internal event-bus client publishes with bootstrap-derived tenant and principal identifiers, and each worker/planner/tool or direct service client uses the shared provider instead of static platform-tenant assumptions.
- Updated identity-service low-level client binding so platform tenant context is supplied only after onboarding/discovery instead of being assumed at construction time.
- Removed low-level identity-client symmetric caller-JWT generation so identity-admin requests now use only the admin API key plus optional bound `X-Tenant-ID` until a future explicit caller-principal injection path is designed.
- Refined the identity-service admin contract so onboarding is superuser-key only, tenant-admin endpoints require tenant-bound admin keys plus `X-Tenant-ID`, onboarding returns the generated tenant admin key, and SDK/example call sites no longer pass service tenant or service user IDs into identity operations.
- Replaced the deterministic derived tenant admin key scheme with persisted, rotatable tenant admin credentials backed by a new identity-service table, hashed secret-at-rest validation, and a tenant-admin rotation endpoint exposed through the SDK wrapper/client.

## Brownfield Files Changed
- `libs/soorma-service-common/src/soorma_service_common/middleware.py`
- `sdk/python/soorma/memory/client.py`
- `sdk/python/soorma/tracker/client.py`
- `sdk/python/soorma/events.py`
- `sdk/python/soorma/registry/client.py`
- `sdk/python/soorma/auth.py`
- `sdk/python/soorma/context.py`
- `sdk/python/soorma/agents/base.py`
- `sdk/python/soorma/cli/commands/dev.py`
- `services/identity-service/src/identity_service/services/token_service.py`
- `examples/01-hello-world/client.py`
- `examples/01-hello-world/worker.py`
- `examples/01-hello-world/start.sh`
- `examples/01-hello-world/README.md`
- `examples/01-hello-tool/client.py`
- `examples/01-hello-tool/calculator_tool.py`
- `examples/01-hello-tool/start.sh`
- `examples/01-hello-tool/README.md`
- `examples/02-events-simple/*`
- `examples/03-events-structured/*`
- `examples/04-memory-working/*`
- `examples/05-memory-semantic/*`
- `examples/06-memory-episodic/*`
- `examples/08-worker-basic/*`
- `examples/09-planner-basic/*`
- `examples/10-choreography-basic/*`
- `examples/11-discovery-llm/*`
- `examples/12-event-selector/*`
- `examples/13-a2a-gateway/*`
- `examples/research-advisor/*`
- `examples/shared/__init__.py`
- `examples/shared/auth.py`
- Focused tests under `libs/soorma-service-common/tests/`, `sdk/python/tests/`, and `services/identity-service/tests/`
- Documentation and changelogs under `services/identity-service/`, `sdk/python/`, and `docs/identity_service/`

## Architecture Alignment
- Section 1 Authentication and tenancy: secured ingress now denies header-only requests after cutover, while the explicit trusted admin-key exception remains bounded to identity control-plane routes.
- Section 2 Two-layer SDK: handler-facing wrapper surfaces were unchanged; bearer-auth transport changes remain inside low-level clients, context wiring, and CLI/example bootstrap helpers rather than leaking service-client details into handlers.
- Section 3 Event choreography: event publish and stream registration semantics remain explicit while authorization moves into transport headers for event-service access.
- Section 4 Multi-tenancy: active runtime extraction now prefers canonical `tenant_id` while keeping compatibility claims bounded to migration seams.
- Section 6 Error handling: deny behavior remains fail closed for missing bearer tokens, invalid signatures, and unknown-key conditions.

## Verification Executed
- `sdk/python/tests/cli/test_dev.py`
- `sdk/python/tests/test_memory_client.py`
- `sdk/python/tests/test_tracker_service_client.py`
- `sdk/python/tests/test_context_wrappers.py`
- `sdk/python/tests/test_context_identity_wrapper.py`
- `sdk/python/tests/test_bus_client.py`
- `sdk/python/tests/test_event_client_registration.py`
- `sdk/python/tests/test_registry_service_client.py`
- `sdk/python/tests/test_identity_service_client.py`
- `sdk/python/tests/test_example_auth_bootstrap.py`
- `sdk/python/tests/test_agents.py`
- `libs/soorma-service-common/tests/test_middleware.py`
- `services/identity-service/tests/test_token_api.py`
- `services/identity-service/tests/test_provider_facade.py`
- `services/identity-service/tests/test_delegated_issuer_api.py`
- `services/identity-service/tests/test_discovery_api.py`
- `python -m py_compile` on the newly migrated `research-advisor` and `13-a2a-gateway` Python files

## Results
- SDK CLI + client suites: 58 passed
- Shared middleware suite: 29 passed
- Identity token API suite: 7 passed
- Provider facade suite: 6 passed
- Delegated issuer + discovery suites: 5 passed
- Onboarding API suite: 4 passed
- Wrapper suites: 25 passed
- CLI correction pass after review feedback: 29 passed
- Example/JWT propagation correction pass: 40 passed
- Bearer-token provider correction pass: 83 SDK/example tests passed and 30 shared middleware tests passed
- Shared-helper shim-removal cleanup: 51 focused SDK/example tests passed
- Bootstrap-derived platform-tenant correction pass: 28 focused SDK/example tests passed
- Identity-client transport cleanup after review feedback: 27 focused SDK/example tests passed
- Scoped admin-key review correction: 20 focused identity-service tests, 8 focused SDK identity tests, and 31 shared middleware tests passed
- Persisted tenant-admin credential redesign: 23 focused identity-service tests and 14 focused SDK/example tests passed
- Final example migration syntax validation: `py_compile` passed for the remaining migrated `research-advisor` and `13-a2a-gateway` Python files

## Residual Notes
- Identity-service persistence still retains compatibility-era naming in storage tables; this unit keeps that behind a bounded migration seam while moving active issuance/verification behavior toward canonical `tenant_id`.
- Monorepo pytest invocations still need package-local grouping because multiple `tests/conftest.py` files collide when mixed in one command.
- Local key rotation now follows the documented delete-and-regenerate path: remove `.soorma/identity/` files and rerun `soorma dev`.
- The hello-world example now depends on locally bootstrapped identity-service availability so it can reuse persisted onboarding metadata and let the shared token provider mint and cache JWTs before connecting to event or registry infrastructure.
- The hello-tool example now follows the same bootstrap-and-provider path as hello-world, instead of relying on hard-coded tenant/user constants for Event Service access.
- The full example suite now follows the same shared bootstrap/token-provider pattern for internal Soorma infrastructure access; the only intentional exception is the external plain-HTTP client in `examples/13-a2a-gateway/client.py`, which remains outside the internal event-bus auth flow.
- Hello-world now imports the shared helper directly and no longer carries a local `auth_bootstrap.py` adapter; the shared module also exposes the CLI priming path used by `start.sh`.
- Hello-world now derives both tenant and bootstrap-admin identifiers from the persisted bootstrap payload instead of embedding platform tenant constants in the example client.
- Low-level identity client requests no longer assume a platform tenant exists before onboarding; callers may bind it after bootstrap or pass it explicitly per request.
- Low-level identity client no longer self-mints caller JWTs from local symmetric secrets; current transport is superuser admin API key only for onboarding and tenant-admin API key plus bound `X-Tenant-ID` for tenant-scoped identity administration.
- Shared middleware now derives service identity from canonical JWT claims (`tenant_id`, `principal_id`, `sub`) when explicit service-claim aliases are absent, preserving bearer-only Tier-2 access after cutover.
- Existing tenants carrying the older deterministic tenant admin key format must re-onboard or rotate to obtain a persisted credential record; old derived keys are no longer accepted by the stricter validation path.