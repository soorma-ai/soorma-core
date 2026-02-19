# Action Plan: [Task Name] (SOOR-XXX)

**Status:** 📋 Planning | 🟢 Implementation | 🔴 Blocked

## 1. Requirements & Core Objective
- Summary of the specific task from the Master Plan (if applicable).
- Acceptance Criteria.

## 2. Technical Design
- **Component:** (sdk | libs | services | examples)
- **Data Models:** List specific Pydantic models being added/modified.
- **Event Schema:** Identify topic and payload structure.

### SDK Layer Verification (If Modifying Services)

When adding or modifying service endpoints, verify the two-layer SDK pattern:

- [ ] **Service Client (Low-Level):** New methods exist in service client (e.g., `MemoryServiceClient`, `EventClient`)
  - File: `sdk/python/soorma/[service]/client.py`
  - Methods: List method signatures
  - Verified: (Yes/No with line numbers)

- [ ] **PlatformContext Wrapper (High-Level):** Wrapper methods exist in context layer
  - File: `sdk/python/soorma/context.py`
  - Wrapper class: (e.g., `MemoryClient`, `BusClient`)
  - Methods: List wrapper methods that delegate to service client
  - Status: (Exists/Missing - if missing, add task to create wrappers)

- [ ] **Examples:** All examples use `context.memory` / `context.bus`, NOT service clients directly
  - Review: List example files checked
  - Compliance: (Yes/No)

**Note:** If wrapper methods are missing, add a HIGH PRIORITY task to create them BEFORE implementing dependent features.

## 3. Task Tracking Matrix
- [ ] **Task 1: Design** (Update models/interfaces) (Status: ⏳)
- [ ] **Task 48H: The FDE Fix** (What are we skipping for now?)
- [ ] **Task 2: Tests** (Write failing pytest cases) (Status: 📋)
- [ ] **Task 3: Logic** (Core implementation) (Status: 📋)

## 4. TDD Strategy
- **Unit Test:** [Describe logic test]
- **Integration Test:** [Describe service-to-service test]

## 5. Forward Deployed Logic Decision
- **Decision:** [e.g., "Using an in-memory list for Phase 1 instead of Redis."]
