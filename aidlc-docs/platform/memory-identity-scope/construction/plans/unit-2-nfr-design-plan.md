# Unit-2 NFR Design Plan

## Unit Context
- Unit: U2 - Memory Runtime Alignment (API + Services + CRUD)
- Inputs:
  - construction/unit-2/nfr-requirements/nfr-requirements.md
  - construction/unit-2/nfr-requirements/tech-stack-decisions.md
- Focus: convert approved NFR requirements into concrete design patterns and logical component boundaries for implementation.

## NFR Design Checklist
- [x] Analyze Unit-2 NFR requirements artifacts
- [x] Identify relevant NFR design-pattern decisions for Unit-2 scope
- [x] Prepare clarification questions with [Answer] tags
- [x] Resolve all answers and ambiguities
- [x] Generate nfr-design-patterns.md
- [x] Generate logical-components.md
- [x] Perform security-baseline compliance review
- [x] Present NFR Design completion for approval

## Clarifying Questions
Please answer each question by filling the letter after [Answer]:.

## Question 1
For fail-closed enforcement, where should identity guard checks be modeled to prevent bypass while avoiding duplication?

A) API route boundary only

B) Service boundary only

C) Dual-layer guard (route + service), with service as mandatory backstop

X) Other (please describe after [Answer]: tag below)

[Answer]: c)

## Question 2
For admin endpoint authorization design in Unit-2, what pattern should be documented as the implementation baseline?

A) Shared admin guard dependency applied per admin endpoint

B) Inline authorization logic in each endpoint handler

C) Middleware-level global admin authorization only

X) Other (please describe after [Answer]: tag below)

[Answer]: a)

## Question 3
For validation-failure logging, what structured event pattern should be used for consistency and privacy?

A) Structured warning event with fixed fields including platform_tenant_id only

B) Free-form warning strings without a fixed schema

C) No warning log event for expected validation failures

X) Other (please describe after [Answer]: tag below)

[Answer]: a)

## Question 4
For predicate consistency assurance across plans/sessions/task_context/plan_context, what design mechanism should be documented?

A) Shared predicate-builder/helper abstraction for full identity tuple

B) Per-module manual predicate composition with review checklist only

C) Service-layer wrapper methods only, leaving CRUD predicate style unchanged

X) Other (please describe after [Answer]: tag below)

[Answer]: A) Use a shared predicate-builder/helper abstraction for full identity tuple. Rationale: this adds modest upfront abstraction complexity but reduces long-term drift and duplicated query logic across plans/sessions/task_context/plan_context modules. Practical recommendation: keep helper API small and identity-agnostic (for example, full identity tuple predicate builder + optional resource-key predicate combiner), and avoid over-abstracting business-specific clauses so the pattern remains reusable by other service CRUD layers.

## Question 5
For testability-oriented NFR design output, how explicit should logical components and pattern-to-test traceability be?

A) High-level pattern list only

B) Pattern list plus component boundaries and scenario-to-test-module trace map

C) Detailed test case authoring in this stage

X) Other (please describe after [Answer]: tag below)

[Answer]: b)

## Notes
- Questions are scoped to Unit-2 NFR design decisions only.
- Code generation remains blocked until NFR Design stage is completed and approved.
