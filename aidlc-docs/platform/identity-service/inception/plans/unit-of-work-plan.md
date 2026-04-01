# Unit of Work Plan

## Objective
Decompose the identity-service initiative into implementation-ready units of work that support incremental PR merges while preserving FR-11 compatibility constraints and security quality gates.

## Planning Checklist
- [x] Step 1 - Confirm decomposition approach and sequencing principles
- [x] Step 2 - Define unit boundaries and responsibilities
- [x] Step 3 - Define inter-unit dependencies and critical path
- [x] Step 4 - Map stories to units
- [x] Step 5 - Generate unit-of-work.md
- [x] Step 6 - Generate unit-of-work-dependency.md
- [x] Step 7 - Generate unit-of-work-story-map.md
- [x] Step 8 - Validate coverage and dependency consistency

## Mandatory Artifacts
- [x] Generate `aidlc-docs/platform/identity-service/inception/application-design/unit-of-work.md`
- [x] Generate `aidlc-docs/platform/identity-service/inception/application-design/unit-of-work-dependency.md`
- [x] Generate `aidlc-docs/platform/identity-service/inception/application-design/unit-of-work-story-map.md`
- [x] Validate that all stories are assigned to one or more units
- [x] Validate unit boundaries and dependency order

## Context-Specific Questions

## Question 1
What should be the primary decomposition strategy for units?

A) By capability epic (onboarding, trust, token, rollout)

B) By architectural layer (shared lib, service, SDK, cutover)

C) Hybrid capability-first with explicit layer subphases (recommended)

X) Other (please describe after [Answer]: tag below)

[Answer]: c)

## Question 2
How many units should we target for implementation and review efficiency?

A) 3 units (larger scope per unit)

B) 4 units (balanced)

C) 5-6 units (finer-grained, more checkpoints)

D) Let AI choose based on dependency and risk minimization

X) Other (please describe after [Answer]: tag below)

[Answer]: d)

## Question 3
Which unit should be forced as the first unit on the critical path?

A) Shared auth dependency evolution in `soorma-service-common`

B) New identity service core domain APIs

C) SDK wrapper/client JWT updates

D) No forced first unit; AI decides by dependency graph

X) Other (please describe after [Answer]: tag below)

[Answer]: d) however make sure that each unit can be merged to main as the work completes, so scope / changes for each unit and it's predecessar (dependencies) are planned accordingly.

## Question 4
How should FR-11 compatibility work be represented?

A) Dedicated compatibility unit

B) Embedded acceptance criteria in all affected units

C) Both: dedicated unit + embedded criteria (recommended)

X) Other (please describe after [Answer]: tag below)

[Answer]: c)

## Question 5
How should security and QA extension outputs align with units?

A) Generate one QA/security-focused unit only at the end

B) Attach QA/security acceptance checks to each functional unit (recommended)

C) Separate security hardening unit + QA checks per unit

X) Other (please describe after [Answer]: tag below)

[Answer]: b)

## Question 6
How should PR checkpoint cadence balance throughput vs review depth?

A) Minimal units with fewer checkpoints

B) Moderate units with balanced checkpoints (recommended)

C) Fine-grained units with many checkpoints

X) Other (please describe after [Answer]: tag below)

[Answer]: b)

## Approval
After filling all answers, confirm in chat:
"unit of work plan approved"

Then Units Generation Part 2 will generate:
- `aidlc-docs/platform/identity-service/inception/application-design/unit-of-work.md`
- `aidlc-docs/platform/identity-service/inception/application-design/unit-of-work-dependency.md`
- `aidlc-docs/platform/identity-service/inception/application-design/unit-of-work-story-map.md`