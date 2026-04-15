# Infrastructure Design - uow-cutover-hardening

## Design Inputs
Approved infrastructure answers:
- Q1: D - Single-step in-place deployment for hard-cutover releases
- Q2: A - In-process bounded verifier cache per service instance
- Q3: A - Existing event bus invalidation plus periodic polling backstop
- Q4: A - Explicit issuer allowlist and egress restriction per environment
- Q5: A - Existing centralized logs/metrics/tracing stack with alert contracts
- Q6: B - Manual wiki rollback procedure outside deployment tooling
- Q7: A - Automated ephemeral local keypair and JWKS bootstrap artifacts

Supporting artifacts:
- aidlc-docs/platform/identity-service/construction/uow-cutover-hardening/functional-design/business-logic-model.md
- aidlc-docs/platform/identity-service/construction/uow-cutover-hardening/functional-design/business-rules.md
- aidlc-docs/platform/identity-service/construction/uow-cutover-hardening/nfr-design/nfr-design-patterns.md
- aidlc-docs/platform/identity-service/construction/uow-cutover-hardening/nfr-design/logical-components.md

## Infrastructure Mapping Decisions

### 1. Runtime Deployment Model
- identity-service uses the existing in-place deployment path for this unit's cutover release.
- No new blue/green or canary infrastructure is introduced in this unit.
- Cutover safety is achieved through verification checks and documented manual rollback procedure rather than new deployment tooling.

### 2. Verifier Cache Topology
- Last-known-good verifier material is stored in process memory on each service instance.
- Cache entries are TTL-bounded and expire deterministically.
- No shared Redis/database/filesystem cache is added for this unit.

Infrastructure consequence:
- Simpler runtime footprint and no new persistence dependency.
- Cache warm-up and expiry behavior must be tolerated per instance.

### 3. Rotation and Refresh Transport
- Key invalidation uses the existing event bus as the primary propagation mechanism.
- Periodic polling remains the bounded backstop when events are delayed or missed.
- No webhook-based invalidation service or manual-only refresh path is added.

Infrastructure consequence:
- This unit reuses existing messaging infrastructure rather than introducing a new control plane component.

### 4. Delegated Issuer Network Boundary
- Runtime outbound trust retrieval is permitted only to explicitly approved issuer/OIDC/JWKS endpoints.
- Environment-specific egress controls must restrict outbound access to the allowlisted destinations.
- Application-level issuer trust validation remains required, but is not the only control.

Infrastructure consequence:
- Outbound network policy, security groups/firewall rules, or equivalent environment controls must encode trusted issuer boundaries.
- Broad unrestricted outbound internet access is not the target design.

### 5. Telemetry and Alerting Sink
- Auth, override, key-resolution, and delegated trust telemetry flows into the existing centralized logging, metrics, and tracing stack.
- Alert contracts for denial spikes, unknown `kid`/signature failures, and override anomalies are defined against that shared stack.
- No new monitoring vendor is introduced by this unit.

### 6. Rollback Control Boundary
- Rollback execution remains a documented manual operational procedure external to deployment automation.
- The procedure must define entry criteria, execution steps, and post-rollback verification checks.
- No new rollback endpoint, admin control plane, or pipeline gating framework is added by this unit.

Infrastructure consequence:
- Lowest tooling overhead for this unit.
- Operational discipline is documentation-driven rather than automation-enforced.

### 7. Local Bootstrap Infrastructure Boundary
- `soorma dev` generates ephemeral asymmetric keypair and JWKS bootstrap artifacts per local environment instance.
- Generated local trust artifacts are not long-lived shared assets and are not committed to the repository.
- Local setup remains production-aligned without requiring centralized local secret distribution.

## Shared Infrastructure Reuse
- Existing service deployment environment: reused
- Existing event bus/topic mechanism: reused
- Existing centralized observability stack: reused
- Existing network policy framework: reused and tightened for delegated issuer allowlists

No new shared infrastructure artifact is required for this unit.

## Operational Constraints
- In-place deployment increases need for deterministic pre/post verification even though rollback remains manual.
- Per-instance in-memory caches require strong TTL discipline and consistent invalidation behavior.
- Manual rollback documentation must be concrete enough to support fail-closed recovery without feature flags.

## Security Baseline Alignment
- SECURITY-03: Compliant. Centralized structured logging/metrics/tracing sink is required for auth security events.
- SECURITY-07: Compliant. Delegated issuer trust retrieval uses explicit egress restriction and allowlisting.
- SECURITY-08: Compliant. Infrastructure design preserves deny-by-default authenticated runtime boundaries and trusted issuer restrictions.
- SECURITY-11: Compliant. Security controls are layered across network boundaries, runtime trust validation, and centralized telemetry.
- SECURITY-14: Compliant. Alert sinks and signal families are explicitly mapped to existing monitoring infrastructure.
- SECURITY-15: Compliant. Cache expiry, trust-source failure, and invalid key paths remain fail-closed.

Rules tracked as N/A in this artifact:
- SECURITY-01: N/A - no persistent storage resource added in this unit infrastructure design
- SECURITY-02: N/A - no new external load balancer/API gateway/CDN resource defined in this artifact
- SECURITY-04: N/A - no web HTML-serving boundary in this unit infrastructure design
- SECURITY-05: N/A - input validation is a code-level concern, not an infrastructure design deliverable here
- SECURITY-06: N/A - IAM permission policies are not specified in this artifact
- SECURITY-09: N/A - runtime hardening specifics belong to implementation/deployment config stage
- SECURITY-10: N/A - supply-chain controls belong to build/code generation and CI stages
- SECURITY-12: N/A - authentication credential/session implementation details are not specified here
- SECURITY-13: N/A - integrity verification controls are not explicitly modeled as infrastructure resources in this stage