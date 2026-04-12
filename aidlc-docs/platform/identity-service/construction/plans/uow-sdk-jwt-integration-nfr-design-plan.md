# NFR Design Plan - uow-sdk-jwt-integration

## Unit Context
- Unit: uow-sdk-jwt-integration
- Inputs reviewed:
  - aidlc-docs/platform/identity-service/construction/uow-sdk-jwt-integration/nfr-requirements/nfr-requirements.md
  - aidlc-docs/platform/identity-service/construction/uow-sdk-jwt-integration/nfr-requirements/tech-stack-decisions.md

## Execution Checklist
- [x] Step 1 - Analyze NFR requirements
- [x] Step 2 - Draft NFR design plan and question set
- [x] Step 3 - Store this NFR design plan file
- [ ] Step 4 - Collect and validate all answers
- [ ] Step 5 - Generate NFR design artifacts
- [ ] Step 6 - Present NFR Design completion gate

## NFR Design Clarifying Questions
Please answer each question by filling the [Answer]: field.

## Question 1
For verifier source precedence and resilience behavior, what explicit design pattern should be modeled?

A) Strict precedence chain: JWKS -> bounded static fallback -> fail closed

B) Runtime scorer chooses best available source dynamically

C) Static key primary with opportunistic JWKS refresh

D) Environment-specific behavior with no fixed precedence

X) Other (please describe after [Answer]: tag below)

[Answer]: A)

Rationale:
- Aligns directly with approved Unit 3 NFR decisions: JWKS primary, deterministic bounded fallback, and fail-closed terminal behavior.
- Preserves deterministic and auditable server-side verifier behavior across identity-service and other soorma-core service APIs.
- Avoids dynamic source-selection ambiguity and environment-specific drift that could weaken compatibility-phase security guarantees.

## Question 2
For JWKS/discovery cache policy, what default TTL/refresh strategy should NFR design encode for this unit?

A) Single TTL only with refresh on expiry

B) TTL + jittered proactive background refresh + hard-expiry fail-closed

C) No cache; always fetch live

D) Long-lived cache with manual rotation only

X) Other (please describe after [Answer]: tag below)

[Answer]: B)

Rationale:
- Aligns with approved Unit 3 resilience posture by combining bounded cache behavior with deterministic hard-expiry fail-closed enforcement.
- Proactive jittered refresh reduces synchronized expiry spikes and lowers risk of verification latency regressions near TTL boundaries.
- Preserves security guarantees while improving operational stability during transient JWKS/discovery interruptions.

## Question 3
For key rotation propagation objective (<=5 minutes), what distribution model should be modeled in design?
A) Poll-only refresh at fixed interval

B) Event-triggered invalidation + bounded polling backstop

C) Manual reload gates in each service

D) Opportunistic refresh only on verification miss

X) Other (please describe after [Answer]: tag below)

[Answer]: B)

Rationale:
- Best fits the <=5-minute key propagation objective by combining low-latency invalidation signals with deterministic bounded backstop refresh.
- Preserves resilience during transient event-delivery disruption without requiring unsafe manual operations.
- Aligns with approved Unit 3 fail-closed and deterministic verifier behavior while keeping propagation performance measurable.

## Question 4
For deterministic bootstrap outcomes (`CREATED`, `REUSED`, `FAILED_DRIFT`), what component pattern should be explicit?

A) Inline checks in CLI command only

B) Dedicated bootstrap state evaluator with typed result contract

C) B + protected-config drift classifier and explicit fail-closed guard

D) B + interactive remediation flow before return

X) Other (please describe after [Answer]: tag below)

[Answer]: C)

Rationale:
- Directly enforces the approved deterministic bootstrap outcome contract (`CREATED`, `REUSED`, `FAILED_DRIFT`) through explicit component boundaries rather than ad-hoc command logic.
- Adds protected-config drift classification with fail-closed guardrails, matching the established Unit 3 security and reliability posture.
- Improves testability and reuse across bootstrap execution contexts by centralizing evaluation and safety policy in a dedicated typed component.

## Question 5
For observability depth (logs + metrics + tracing), what minimum trace boundary should be enforced?

A) Wrapper entry/exit spans only

B) A + verification source selection and fallback-decision sub-spans

C) B + issuance override decision and audit-write sub-spans

D) C + per-claim validation sub-spans

X) Other (please describe after [Answer]: tag below)

[Answer]: C)

Rationale:
- Provides the minimum trace boundary that remains actionable for security and operations by capturing verifier source/fallback decisions plus issuance override and audit-write outcomes.
- Aligns with approved Unit 3 observability depth and durable override-audit requirements without requiring excessive per-claim trace volume.
- Preserves deterministic post-incident reconstruction for fail-closed and exception paths across identity-service and shared auth verification surfaces.

## Question 6
For security hardening with durable override auditability, what persistence design split should be modeled?

A) Single sync audit writer for all events

B) Critical override events sync + non-critical events async

C) All events async with retry guarantees

D) Fire-and-forget logs only

X) Other (please describe after [Answer]: tag below)

[Answer]: B)

Rationale:
- Aligns with the approved durable override-audit requirement by enforcing synchronous persistence for critical override/security decisions.
- Preserves performance and throughput for routine telemetry by allowing non-critical audit events to use asynchronous persistence.
- Maintains deterministic security posture while avoiding unnecessary end-to-end latency inflation from making all event writes synchronous.

## Question 7
For rollout gate enforcement before broad compatibility enablement, what design-level gate should be mandatory?

A) Unit tests only

B) Unit + integration happy paths only

C) B + required negative security matrix as blocking contract

D) C + load-profile pass required at selected throughput tier

X) Other (please describe after [Answer]: tag below)

[Answer]: C)

## Approval
After filling all answers, reply in chat:
"nfr design plan answers provided"
