# Gateway Service - Design Required

**Status:** \u26a0\ufe0f Blocking Implementation  
**Created:** February 15, 2026

---

## Critical Notice

**The current README.md and ARCHITECTURE.md in this directory are DRAFT PROPOSALS ONLY.**

They represent preliminary thinking to document the overall documentation structure, but **have NOT been formally designed or reviewed**.

---

## Required Before Implementation

### 1. Discovery & Requirements

- [ ] Analyze use cases (web apps, mobile, external integrations)
- [ ] Research HTTP/Event bridge patterns (correlation-based, websockets, SSE)
- [ ] Survey alternative approaches (GraphQL, gRPC, polling vs push)
- [ ] Define authentication requirements (API keys, OAuth2, JWT)
- [ ] Determine rate limiting and quota needs
- [ ] Identify security threats (injection, DoS, data leakage)

### 2. Design Phase

- [ ] Create RFC/ADR (Architecture Decision Record) documenting:
  - Problem statement
  - Alternatives considered
  - Selected approach with rationale
  - Trade-offs and risks
  - Security considerations
  - Performance characteristics

- [ ] API Design:
  - REST conventions (resource naming, HTTP methods)
  - Request/response schemas
  - Error handling and status codes
  - Versioning strategy
  - OpenAPI specification

- [ ] Technical Architecture:
  - ResponseWaiter implementation (in-memory vs Redis)
  - Connection pooling and resource management
  - Timeout handling and async fallback
  - Health checks and observability

### 3. Review & Approval

- [ ] Technical review with team
- [ ] Security review
- [ ] Validate against AGENT.md constitution
- [ ] Update gateway/README.md and gateway/ARCHITECTURE.md with finalized design
- [ ] Create implementation plan (Stage N refactoring docs)

---

## Current State

- **Dockerfile:** Placeholder only (`echo "Coming Soon"`)
- **Documentation:** DRAFT proposals in README.md and ARCHITECTURE.md
- **Implementation:** NONE - do not start without approved design

---

## Next Steps

When ready to implement Gateway Service:

1. **Start with design discovery, NOT implementation**
2. Create RFC in `docs/refactoring/arch/0N-GATEWAY-SERVICE.md`
3. Review and iterate on design
4. Update gateway documentation with approved design
5. Only then create SDK and service implementation plans

---

## References

- [Current Draft README](../README.md) - Preliminary user guide (NOT approved)
- [Current Draft ARCHITECTURE](../ARCHITECTURE.md) - Preliminary technical design (NOT approved)
- [AGENT.md Constitution](../../../AGENT.md) - Documentation standards
