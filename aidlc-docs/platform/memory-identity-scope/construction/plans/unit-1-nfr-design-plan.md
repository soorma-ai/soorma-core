# Unit-1 NFR Design Plan

## Unit Context
- Unit: U1 - Shared Identity Dependency (soorma-service-common)
- Inputs:
  - construction/unit-1/nfr-requirements/nfr-requirements.md
  - construction/unit-1/nfr-requirements/tech-stack-decisions.md
- Focus: encode NFR requirements into concrete design patterns and logical components for implementation.

## NFR Design Checklist
- [x] Analyze NFR requirements artifacts for Unit-1
- [x] Identify relevant design-pattern decisions for Unit-1 scope
- [x] Prepare clarification questions with [Answer] tags
- [x] Resolve all answers and ambiguities
- [x] Generate nfr-design-patterns.md
- [x] Generate logical-components.md
- [x] Perform security-baseline compliance review
- [x] Present NFR Design completion for approval

## Clarifying Questions
Please answer each question by filling the letter after [Answer]:.

## Question 1
For fail-safe behavior in dependency validation, which pattern should be explicitly documented for Unit-1 implementation?

A) Immediate fail-closed (`HTTP 400`) on first invalid identity dimension detected

B) Aggregate all validation issues, then return one combined `HTTP 400`

C) Soft-fail with warning log and continue handler execution

X) Other (please describe after [Answer]: tag below)

[Answer]: B)

## Question 2
How should logging design be modeled for missing identity validation events in Unit-1?

A) Structured warning event with fixed fields and platform_tenant_id only

B) Unstructured text warning with minimal context

C) No logging pattern; rely only on HTTP response

X) Other (please describe after [Answer]: tag below)

[Answer]: A)

## Question 3
For message consistency design, which pattern should govern shared dependency error output?

A) Centralized message catalog/constants in shared library with immutable defaults

B) Shared defaults plus optional service override hook (not used immediately)

C) Per-service message ownership pattern

X) Other (please describe after [Answer]: tag below)

[Answer]: A)

## Question 4
Which logical component boundary should be explicit in Unit-1 NFR design docs?

Clarification: this asks how many named design building blocks we should document for Unit-1 (just validator, validator+logging seam, or validator+separate policy providers).

A) Keep two logical components only: identity-validation dependency and logging adapter interface seam

B) Single component only (dependency), no explicit logging boundary

C) Three components: dependency, message policy provider, and logging policy provider

X) Other (please describe after [Answer]: tag below)

[Answer]: A)

## Question 5
For deferred tenant-facing troubleshooting architecture, how should Unit-1 design capture this non-scope item?

A) Add explicit "Deferred Architecture Decision" section with future design trigger criteria

B) Mention briefly in one note line only

C) Omit from NFR design artifacts and keep only in NFR requirements

X) Other (please describe after [Answer]: tag below)

[Answer]: a) generate content that can be used to create a github issue to track later.

## Notes
- Questions are intentionally scoped to Unit-1 NFR design decisions only.
- Code generation remains blocked until NFR Design stage is completed and approved.
