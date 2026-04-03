# NFR Requirements Clarification - uow-shared-auth-foundation

A contradiction was detected during NFR answer validation:
- Q8 currently says "No compatibility constraints"
- Existing approved requirements include FR-11 compatibility constraints requiring non-breaking DI/router call-site behavior during coexistence.

Please resolve with one selection below.

## Question 1
Which compatibility requirement should govern this unit?

A) Enforce FR-11 compatibility strictly: zero route signature/DI call-site changes during coexistence

B) Allow additive optional parameters only, with no breaking changes to existing callers

C) Allow broader refactors if backward-compatible wrappers/adapters are provided and existing behavior is preserved

D) Override FR-11 for this unit and allow no compatibility constraints (explicit requirement change)

X) Other (please describe after [Answer]: tag below)

[Answer]: D) Override FR-11 for this unit and allow no compatibility constraints.

Rationale and details:
- This initiative is pre-release, and all impacted services in soorma-core are in scope for coordinated refactor.
- There are no known external adopters relying on a stable compatibility contract for these internal service call paths.
- Introducing wrappers/adapters purely for temporary compatibility would add avoidable complexity and maintenance burden.
- Decision is intentional and traceable: this unit will prioritize direct refactor correctness, with strong cross-service regression coverage as risk control.

## Note
If you choose D or X with an FR-11 override, I will update requirements traceability in the NFR artifact notes to reflect the deliberate scope change.
