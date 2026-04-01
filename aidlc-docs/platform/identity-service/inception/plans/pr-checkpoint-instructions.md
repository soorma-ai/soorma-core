# PR Checkpoint Instructions

## Context
- Initiative: platform / identity-service
- Checkpoint Type: Inception PR Gate
- Branch: dev
- Generated: 2026-04-01T06:52:22Z

1. Stage inception artifacts:
```bash
git add aidlc-docs/platform/identity-service/
```

2. Commit:
```bash
git commit -m "feat: inception phase complete for platform/identity-service"
```

3. Push branch:
```bash
git push -u origin dev
```

4. Open a pull request on your git host from `dev` targeting `main` (or your default branch).
Use the PR Title and PR Description provided below.

5. Share the PR with your team:
- Scrum master / EM: review initiative scope, unit-of-work, story map, and JIRA tickets.
- Engineering team: review requirements and application design artifacts.

## PR Title
`feat(inception): platform/identity-service - inception phase complete`

## PR Description

`## Initiative Summary
This PR contains completed Inception artifacts for the identity-service initiative in soorma-core. The initiative defines a platform-tenant identity domain, principal lifecycle management, delegated trust model, and phased JWT rollout compatible with existing dependency injection contracts.

The scope and decomposition are structured for incremental mergeability across four units of work with explicit dependency order and security constraints.

## Key Requirements
- FR-1 to FR-5: platform tenant identity domain, principal lifecycle, onboarding, delegated issuer registration.
- FR-6 to FR-10: token issuance, claim contracts, delegated context policy, ingress authentication pattern.
- FR-11: phased JWT rollout with non-breaking DI/router compatibility.
- FR-12 and FR-13: two-layer SDK compliance and auditability.

## Scrum Master / Engineering Manager Review
- Unit of Work: `aidlc-docs/platform/identity-service/inception/application-design/unit-of-work.md`
- Story Map: `aidlc-docs/platform/identity-service/inception/application-design/unit-of-work-story-map.md`
- JIRA Tickets: `aidlc-docs/platform/identity-service/inception/jira-tickets/jira-tickets.md`

## Engineering Team Review
- Requirements: `aidlc-docs/platform/identity-service/inception/requirements/requirements.md`
- Application Design: `aidlc-docs/platform/identity-service/inception/application-design/application-design.md`
- Components: `aidlc-docs/platform/identity-service/inception/application-design/components.md`
- Component Methods: `aidlc-docs/platform/identity-service/inception/application-design/component-methods.md`
- Services: `aidlc-docs/platform/identity-service/inception/application-design/services.md`
- Component Dependency: `aidlc-docs/platform/identity-service/inception/application-design/component-dependency.md`
- Unit Dependency: `aidlc-docs/platform/identity-service/inception/application-design/unit-of-work-dependency.md`

## Additional Inception QA Artifacts
- Inception test cases root: `aidlc-docs/platform/identity-service/inception/test-cases/`
`

Once your PR has been reviewed and approved by your team, return to your AI IDE and confirm approval to continue the AI-DLC workflow.