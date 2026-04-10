# Business Logic Model - uow-sdk-jwt-integration

## Purpose
Define functional behavior for SDK JWT integration while preserving wrapper compatibility, enforcing secure issuance-call controls, and keeping migration risk bounded.

## Scope
- JWT-only canonical outbound identity context for SDK calls.
- Wrapper signature preservation (no handler call-site changes).
- Defensive alias mismatch denial when compatibility alias data appears.
- Compatibility-phase token issuance caller-auth using temporary admin key path.
- Scoped issuance authorization (self-issue default + audited admin override).
- Idempotent local tenant bootstrap command behavior.
- Typed SDK exception contracts for auth failures.

## Transaction and Decision Boundaries
1. SDK outbound call boundary:
   - Wrapper composes auth context and delegates to service client.
   - JWT claims are canonical identity source.
2. Defensive compatibility boundary:
   - If legacy alias fields are present, validate against JWT canonical tenant.
   - Any mismatch is denied fail-closed.
3. Issuance request boundary:
   - Admin key authenticates issuance caller in compatibility phase.
   - Identity service signs issued JWTs with asymmetric service-owned keys.
4. CLI bootstrap boundary:
   - Idempotent create-or-verify execution with explicit outcomes.

## Core Workflows

### BLM-1 Wrapper Compatibility Execution
1. Agent handler uses existing `context.*` wrapper API unchanged.
2. Wrapper resolves JWT auth material from configured runtime context.
3. Wrapper sends request through existing client contract without signature changes.
4. Client forwards typed results/errors back to caller.

### BLM-2 JWT Outbound Canonicalization
1. Build outbound authorization using JWT claims only.
2. Include tenant/user/principal context from validated JWT claims.
3. Do not require legacy headers on canonical path.
4. Preserve envelope/event choreography behavior unchanged.

### BLM-3 Defensive Alias Mismatch Guard
1. Detect whether any compatibility alias field is present.
2. If no alias fields: continue canonical JWT path.
3. If alias fields exist: compare alias tenant with JWT tenant.
4. On mismatch: deny request fail-closed and emit typed auth error.
5. Emit structured audit/telemetry signal for mismatch denial.

### BLM-4 Token Issuance Request via Admin Key (Compatibility)
1. Caller invokes issuance endpoint using admin key credential.
2. Service validates key status, scope, tenant binding, and policy constraints.
3. Apply issuance authorization policy:
   - Self-issue allowed by default.
   - Admin override allowed only for scoped authorized callers.
4. If authorized, issue JWT signed by identity-service asymmetric private key.
5. Record audit event with actor, target principal, reason, and correlation context.

### BLM-5 CLI Tenant Bootstrap (Idempotent)
1. `soorma dev` bootstrap checks whether tenant bootstrap state exists.
2. If absent: create baseline resources.
3. If present: verify immutable/protected fields.
4. On protected drift: fail-closed and return explicit drift result.
5. Return explicit outcome code (`CREATED`, `REUSED`, `FAILED_DRIFT`).

### BLM-6 SDK Error Mapping
1. Map auth failures to typed SDK exceptions.
2. Preserve stable error categories and safe messages.
3. Avoid leaking raw token, signing, or internal verification details.
4. Preserve correlation/request identifiers in exception metadata.

## Output Contracts
- Wrapper interfaces remain unchanged.
- Issuance API caller-auth contract supports temporary admin-key compatibility path.
- Verifier model supports static key fallback and JWKS path with deterministic precedence.
- CLI bootstrap returns deterministic machine-readable result codes.

## Security and Reliability Controls
- Fail-closed on JWT validation errors and tenant mismatch.
- Tenant-bound authorization checks for all issuance paths.
- Structured audit events for override and mismatch decisions.
- Stable exception taxonomy for observability and client handling.
