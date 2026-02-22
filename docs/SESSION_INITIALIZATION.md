# AI Assistant Session Initialization Guide

**Purpose:** Ensure consistent, specification-driven development sessions for soorma-core contributions across all workflow phases: Planning → Implementation → Validation.

This guide is mandatory for all AI-assisted sessions to enforce constitutional requirements from [AGENT.md](../AGENT.md).

---

## 🎯 Workflow Overview

Soorma follows a **Specification-Driven Development** model with four phases:

1. **Phase 0: Gateway Verification** (MANDATORY for SDK/services work)
2. **Phase 1: Master Plan Creation** (Strategic planning)
3. **Phase 2: Action Plan Creation** (Tactical planning)
4. **Phase 3: TDD Implementation** (Execution)

Choose the appropriate session type based on your current phase.

---
## 📑 Quick Navigation Index

**Jump to the section you need:**

| What Do You Need? | Go To Section | Phase |
|-------------------|---------------|-------|
| **Quick Start Templates (Minimal)** |
| Gateway verification (quick) | [Quick Gateway Template](#gateway-verification-phase-0) | Phase 0 |
| Create master plan (quick) | [Quick Master Plan Template](#master-plan-phase-1) | Phase 1 |
| Create action plan (quick) | [Quick Action Plan Template](#action-plan-phase-2) | Phase 2 |
| Start implementation (quick) | [Quick Implementation Template](#implementation-phase-3) | Phase 3 |
| **Full Templates & Workflows** |
| Understand who does what | [Understanding Session Templates](#-understanding-the-session-templates) | All |
| Gateway verification (full) | [Phase 0: Gateway Verification](#-phase-0-gateway-verification-sdkservices-work-only) | Phase 0 |
| Master plan creation (full) | [Phase 1: Master Plan Creation](#-phase-1-master-plan-creation) | Phase 1 |
| Action plan creation (full) | [Phase 2: Action Plan Creation](#-phase-2-action-plan-creation) | Phase 2 |
| TDD implementation (full) | [Phase 3: TDD Implementation](#-phase-3-tdd-implementation) | Phase 3 |
| **Learning & Examples** |
| See complete workflow example | [Example 1: Complete Feature](#example-1-complete-feature-gateway--master--action--implementation) | All |
| Small task (no master plan) | [Example 2: Standalone Action Plan](#example-2-standalone-action-plan-no-master-plan) | Phase 2-3 |
| Just implement approved plan | [Example 3: Implementation Only](#example-3-implementation-only-plan-pre-approved) | Phase 3 |
| **Troubleshooting & Validation** |
| Spot violations before they happen | [Red Flags to Watch For](#-red-flags-to-watch-for) | All |
| Know what good looks like | [Correct Workflow Evidence](#-correct-workflow-evidence) | All |
| Fix gateway violations | [Gateway Correction Prompt](#for-gateway-violations) | Phase 0 |
| Fix planning violations | [Planning Correction Prompt](#for-planning-violations) | Phase 1-2 |
| Fix TDD violations | [TDD Correction Prompt](#for-tdd-violations) | Phase 3 |
| **Completion Checklists** |
| Finish planning session | [Planning Completion Checklist](#for-planning-sessions-phase-0-2) | Phase 0-2 |
| Finish implementation session | [Implementation Completion Checklist](#for-implementation-sessions-phase-3) | Phase 3 |
| **Reference & Context** |
| Pre-session preparation | [Pre-Session Checklist](#-pre-session-checklist-by-phase) | All |
| Why this process matters | [Why This Matters](#-why-this-matters) | All |
| Related documentation | [Related Documentation](#-related-documentation) | All |

**Most Common Paths:**
- 🆕 **New feature (SDK/services):** Phase 0 → Phase 1 → Phase 2 → Phase 3
- 🐛 **Small bug fix:** Phase 2 → Phase 3
- ✅ **Implement approved plan:** Phase 3 only
- 🚨 **Agent doing something wrong:** [Red Flags](#-red-flags-to-watch-for) → [Correction Prompts](#-mid-session-course-corrections)

---
## � Understanding the Session Templates

### Who Speaks What?

All session templates in this guide are **HUMAN PROMPT templates** - text that the human developer copy/pastes to start an AI assistant session.

**Format of each template:**
1. **Human provides:** Feature description / requirements / approval
2. **"AGENT INSTRUCTIONS:"** section tells the AI what to do
3. **Agent responds:** By executing the instructions

### Where Do Requirements Come From?

| Phase | Requirements Source | Human Provides |
|-------|-------------------|----------------|
| **Phase 0 (Gateway)** | Human's feature idea | "I want to add semantic search to memory service" |
| **Phase 1 (Master Plan)** | Human's feature description | "Add vector embeddings for similarity search. Current system only does exact match." |
| **Phase 2 (Action Plan)** | Master Plan reference OR standalone feature/bug | "Implement Phase 2 from MASTER_PLAN_X.md" OR "Fix: Events to offline subscribers fail" |
| **Phase 3 (Implementation)** | Approved Action Plan file | "I approve ACTION_PLAN_X.md - implement it" |

**Key Point:** The human always provides the initial requirements. The agent creates specifications (plans) from those requirements, then implements from approved specifications.

---

## �📋 Pre-Session Checklist by Phase

### For Planning Sessions (Phase 1-2):
- [ ] Feature requirement clearly defined by human developer
- [ ] Feature area identified (e.g., `docs/memory_system/`)
- [ ] Understanding of DisCo pattern (Planner/Worker/Tool trinity)
- [ ] Knowledge of 48-Hour Filter & FDE fallback patterns

### For Implementation Sessions (Phase 3):
- [ ] Action Plan reviewed and approved by human developer
- [ ] [ARCHITECTURE_PATTERNS.md](ARCHITECTURE_PATTERNS.md) read if working on SDK/services
- [ ] Dependencies installed (if adding new libraries)
- [ ] Understanding of TDD workflow (RED → GREEN → REFACTOR)

---

## 📝 PHASE 0: Gateway Verification (SDK/Services Work Only)

**When Required:** ANY work affecting SDK (`sdk/python/`), services (`services/`), or integration patterns.

**Skip this for:** Documentation-only changes, example updates that use existing SDK APIs.

### Gateway Verification Template

**This is a HUMAN PROMPT template** - copy/paste this to start the AI session.

```markdown
# Phase 0: Gateway Verification

**Feature Area:** {e.g., memory_system, event_system, gateway}
**Work Type:** {SDK | Services | Integration Patterns}
**Human Input:** {Brief description of feature/change being planned}

# AGENT INSTRUCTIONS:

# MANDATORY READING (Complete ALL before proceeding):

- [ ] Read [docs/ARCHITECTURE_PATTERNS.md](docs/ARCHITECTURE_PATTERNS.md) in full
- [ ] Understand Section 1: Authentication model (custom headers v0.7.x, JWT/API Key roadmap v0.8.0+)
- [ ] Understand Section 2: Two-layer SDK architecture (context wrappers vs. service clients)
- [ ] Understand Section 3: Event choreography (explicit response_event, no inference)
- [ ] Understand Section 4: Multi-tenancy via PostgreSQL RLS and session variables
- [ ] Understand Section 5: State management patterns (working memory, task context, plan context)
- [ ] Understand Section 6: Error handling in service clients vs. wrappers vs. handlers
- [ ] Understand Section 7: Testing patterns (unit mocks vs. integration tests)

# Self-Verification (Answer WITHOUT consulting docs):

1. **Question:** Why can't agent code import `MemoryServiceClient` directly?
   **Answer:** {Your answer here}

2. **Question:** What's the difference between a service endpoint and a wrapper method?
   **Answer:** {Your answer here}

3. **Question:** Where do tenant_id/user_id get extracted in the two-layer pattern?
   **Answer:** {Your answer here}

# Proceed to Planning
Once all checkboxes are complete and self-checks answered, you may proceed to Phase 1 (Master Plan) or Phase 2 (Action Plan).
```

---

## 📝 PHASE 1: Master Plan Creation

**When Needed:** Starting a new feature or major enhancement requiring multiple action plans.

**Location:** Store in `docs/{feature-area}/plans/MASTER_PLAN_{FeatureName}.md`

### Master Plan Session Template

**This is a HUMAN PROMPT template** - copy/paste this to start the AI session.

```markdown
# Session Goal
Create Master Plan for {High-Level Feature Name}

# Requirements (from Human)
{Describe the feature/problem you want solved. Example: "Add semantic search to Memory Service using vector embeddings"}

# Constitutional Requirements (MANDATORY)
Before creating the Master Plan, you (agent) MUST:

1. **Read Constitution**: You MUST read AGENT.md Section 1 (Architectural Mandates)
2. **Use Template**: You MUST use docs/templates/Master_Plan_Template.md as the base structure
3. **Feature Area**: Identified feature area is docs/{feature-area}/
4. **48-Hour Filter**: You MUST evaluate tasks for FDE (Forward Deployed) fallback if >48hr estimate

# Planning Workflow

1. **Discover Context:**
   - Read docs/{feature-area}/README.md (if exists)
   - Read docs/{feature-area}/ARCHITECTURE.md (if exists)
   - Search codebase for related patterns

2. **Apply Template:**
   - Load docs/templates/Master_Plan_Template.md
   - Fill Section 1: Executive Summary & Problem Statement
   - Fill Section 2: Target Architecture (include Mermaid diagram)
   - Fill Section 3: Phased Roadmap
   - Fill Section 4: Risks & Constraints

3. **SDK Layer Assessment (If Applicable):**
   - Identify affected services (Registry, Event Service, Memory, Tracker)
   - List new service endpoints
   - List required PlatformContext wrapper methods
   - Verify wrapper completeness strategy

4. **48-Hour Filter Evaluation:**
   - Identify tasks >48 hours
   - Propose FDE fallback for each (hardcoded config, CLI instead of UI, local storage vs. hosted)
   - Flag "Platform Bloat" risks

5. **Save Plan:**
   - Path: docs/{feature-area}/plans/MASTER_PLAN_{FeatureName}.md
   - Status: 📋 Proposed
   - Await developer approval before proceeding

# Deliverable
A complete Master Plan with phased roadmap, FDE evaluations, and SDK wrapper verification strategy.
```

---

## 📝 PHASE 2: Action Plan Creation

**When Needed:** Breaking down Master Plan phases into implementable tasks, or creating standalone action plans.

**Location:** Store in `docs/{feature-area}/plans/ACTION_PLAN_{TaskName}.md`

### Action Plan Session Template

**This is a HUMAN PROMPT template** - copy/paste this to start the AI session.

```markdown
# Session Goal
Create Action Plan for {Specific Task Name}

# Requirements (from Human)
{One of the following:
1. Reference to Master Plan phase: "Implement Phase 2 from MASTER_PLAN_SemanticSearch.md"
2. Standalone feature/fix: "Fix event service error handling for offline subscribers"
3. Bug report: "Events to offline subscribers cause 500 errors - should gracefully skip"}

# Constitutional Requirements (MANDATORY)
Before creating the Action Plan, you (agent) MUST:

1. **Read Constitution**: You MUST read AGENT.md Section 2 (Workflow Rituals)
2. **Use Template**: You MUST use docs/templates/Action_Plan_Template.md as the base structure
3. **Reference Master Plan**: If applicable, link to parent MASTER_PLAN_{FeatureName}.md
4. **Verify Wrappers**: If modifying services, confirm PlatformContext wrappers exist

# Planning Workflow

1. **Load Template:**
   - Start with docs/templates/Action_Plan_Template.md
   - Fill Section 1: Requirements & Core Objective
   - Fill Section 2: Technical Design

2. **SDK Layer Verification (CRITICAL for Service Changes):**
   - [ ] Service Client: List new methods in `{Service}ServiceClient` (low-level)
   - [ ] Wrapper Methods: List new methods in PlatformContext wrappers (high-level)
   - [ ] Wrapper Status: Verify wrappers exist OR create task to build them FIRST
   - [ ] Examples: Confirm examples will use `context.*` wrappers, not service clients

3. **Task Breakdown:**
   - Fill Section 3: Task Tracking Matrix
   - Mark Task 48H for FDE decisions
   - Sequence tasks: Design → Tests → Logic
   - Create wrapper tasks BEFORE dependent feature tasks

4. **TDD Strategy:**
   - Fill Section 4: Define unit and integration test approach
   - Specify pytest fixtures needed
   - Identify mocks vs. live service tests

5. **FDE Decision:**
   - Fill Section 5: Document what's being deferred/simplified
   - Examples: "Use in-memory list instead of Redis for v0.1"

6. **Save Plan:**
   - Path: docs/{feature-area}/plans/ACTION_PLAN_{TaskName}.md
   - Status: 📋 Planning
   - Await developer approval before implementation

# Deliverable
A complete Action Plan with wrapper verification checklist, task sequence, TDD strategy, and FDE decisions.
```

---

## 🎯 PHASE 3: TDD Implementation

**When Needed:** After Action Plan is approved by human developer.

**Prerequisites:** Action Plan must exist and be approved.

### Implementation Session Template

**This is a HUMAN PROMPT template** - copy/paste this to start the AI session.

```markdown
# Session Goal
Implement {ACTION_PLAN_NAME} from {ACTION_PLAN_FILE_PATH}

# Human Approval
I (human) have reviewed and approve the action plan at {ACTION_PLAN_FILE_PATH}.

# Constitutional Requirements (MANDATORY)
Before starting implementation, you (agent) MUST:

1. **Read Constitution**: Read AGENT.md in full
2. **Read Action Plan**: Read {ACTION_PLAN_FILE_PATH} including Section 2 (SDK Layer Verification)
3. **Confirm TDD Workflow**: Follow strict Test-Driven Development:
   - ❌ NEVER write implementation before tests
   - ✅ RED: Write failing test first
   - ✅ GREEN: Write minimal code to pass
   - ✅ REFACTOR: Clean up

4. **Task Tracking**: Use manage_todo_list for ALL tasks in the action plan

# Workflow Validation
Before you start Task 1, confirm you will:
- Write tests FIRST for each component
- Only implement after tests are written and failing
- Follow the RED → GREEN → REFACTOR cycle
- Use `context.*` wrappers (never direct service client imports in agent code)

If you understand and will follow this process, acknowledge and begin Task 1 with RED (tests first).
```

---

## ✅ Example Session Flows

### Example 1: Complete Feature (Gateway → Master → Action → Implementation)

<details>
<summary><strong>Scenario:</strong> Adding semantic search feature to Memory Service</summary>

**Phase 0: Gateway Verification**
```markdown
# Phase 0: Gateway Verification
**Feature Area:** memory_system
**Work Type:** SDK + Services

✅ Read ARCHITECTURE_PATTERNS.md (all sections)
✅ Self-check 1: Agent code can't import MemoryServiceClient because it violates two-layer pattern - agents use context.memory wrapper
✅ Self-check 2: Service endpoint = REST API method in MemoryService; wrapper method = high-level method in MemoryClient that delegates to service client
✅ Self-check 3: tenant_id/user_id extracted automatically in wrapper layer from event envelope
```

**Phase 1: Master Plan**
```markdown
# Session Goal
Create Master Plan for Semantic Search in Memory System

# Requirements (from Human)
Add semantic search capability to Memory Service using vector embeddings and similarity search. Current memory only supports exact key-value lookup.

# Planning Workflow
1. Read docs/memory_system/README.md ✅
2. Load docs/templates/Master_Plan_Template.md ✅
3. Fill Executive Summary: "Current memory only supports exact match; need vector similarity search"
4. Fill Target Architecture:
   - Service Layer: Add POST /search/semantic endpoint
   - Wrapper Layer: Add `context.memory.search_semantic(query, limit)` method
5. Fill Phased Roadmap:
   - Phase 1: ChromaDB integration (24hr) ✅
   - Phase 2: Vector embeddings (16hr) ✅
   - Phase 3: Hybrid search (>48hr) → FDE: Skip for v0.1, use pure semantic
6. Save: docs/memory_system/plans/MASTER_PLAN_SemanticSearch.md
```

**Phase 2: Action Plan**
```markdown
# Session Goal
Create Action Plan for Phase 1: ChromaDB Integration

# Planning Workflow
1. Load docs/templates/Action_Plan_Template.md ✅
2. SDK Layer Verification:
   - Service Client: Add `search_semantic()` to MemoryServiceClient ✅
   - Wrapper: Add `search_semantic()` to MemoryClient in context.py ✅
   - Status: Wrapper MISSING → Add Task 1.1 to create wrapper first
3. Task Breakdown:
   - Task 1.1: Create wrapper method (HIGH PRIORITY)
   - Task 1.2: Add ChromaDB dependency
   - Task 2: Write tests for /search/semantic endpoint
   - Task 3: Implement service logic
4. Save: docs/memory_system/plans/ACTION_PLAN_ChromaDBIntegration.md
```

**Phase 3: Implementation**
```markdown
# Session Goal
Implement ACTION_PLAN_ChromaDBIntegration.md

# TDD Workflow
Task 1.1 RED: Create tests/sdk/test_memory_wrappers.py → test_search_semantic fails (method doesn't exist)
Task 1.1 GREEN: Add search_semantic() to MemoryClient in context.py
Task 2 RED: Create tests/services/memory/test_search_semantic.py → fails (endpoint doesn't exist)
Task 2 GREEN: Implement POST /search/semantic in memory service
...
```

</details>

### Example 2: Standalone Action Plan (No Master Plan)

<details>
<summary><strong>Scenario:</strong> Bug fix in event service error handling</summary>

**Phase 2: Action Plan** (Skip Master Plan for small tasks)
```markdown
# Session Goal
Create Action Plan for Event Service Error Handling Fix

# Requirements (from Human)
Bug: Events published to offline subscribers cause 500 errors. Expected: should gracefully skip offline subscribers and continue processing.

# Planning Workflow
1. Load docs/templates/Action_Plan_Template.md ✅
2. Requirements: Events published to offline subscribers cause 500 errors; should gracefully skip
3. SDK Layer Verification: No wrapper changes needed (using existing context.bus.publish)
4. Task Breakdown:
   - Task 1: Write test for offline subscriber scenario
   - Task 2: Add try/except in publish logic
   - Task 48H: None (simple fix)
5. Save: docs/event_system/plans/ACTION_PLAN_OfflineSubscriberFix.md
```

**Phase 3: Implementation** (Standard TDD)

</details>

### Example 3: Implementation Only (Plan Pre-Approved)

<details>
<summary><strong>Scenario:</strong> Developer hands you an approved Action Plan</summary>

**Start Directly at Phase 3:**
```markdown
# Session Goal
Implement Stage 4 Phase 2 - Type-Safe Decisions from docs/agent_patterns/plans/ACTION_PLAN_Stage4_Phase2_Implementation.md

# Human Approval
I (human) have reviewed and approve the action plan at docs/agent_patterns/plans/ACTION_PLAN_Stage4_Phase2_Implementation.md.

# Constitutional Requirements (MANDATORY)
You (agent) MUST:

1. Read AGENT.md
2. Read ACTION_PLAN_Stage4_Phase2_Implementation.md
3. Follow TDD: RED → GREEN → REFACTOR
4. Use manage_todo_list for task tracking

# Begin Task 1 with RED (tests first)
```

</details>

---

## 🚨 Red Flags to Watch For

If the AI assistant does ANY of these, **STOP immediately** and issue a correction:

### ❌ Gateway Violations (Phase 0)

- Skips reading ARCHITECTURE_PATTERNS.md for SDK/services work
- Can't answer self-check questions without consulting docs
- Proceeds to planning without completing Gateway checklist
- Doesn't verify wrapper completeness before planning service changes

### ❌ Planning Violations (Phase 1-2)

- Doesn't use docs/templates/ templates (creates plan from scratch)
- Saves plan in wrong location (not in `docs/{feature-area}/plans/`)
- Skips SDK Layer Verification section when modifying services
- Doesn't identify missing wrapper methods before task breakdown
- Creates tasks that require service clients in agent code
- No FDE evaluation for tasks >48 hours
- Doesn't sequence wrapper creation tasks BEFORE dependent tasks

### ❌ TDD Violations (Phase 3)

- Creates implementation files before test files
- Says "I'll create the class first, then write tests"
- Implements multiple methods before writing any tests
- Skips the RED step (no failing test shown)
- Writes tests after implementation (post-facto testing)

### ❌ Constitutional Violations

- Doesn't read AGENT.md or Action Plan Section 0
- Skips Gateway Verification for SDK/services work
- Uses service clients directly in agent code (violates two-layer pattern)
- Missing type hints or docstrings
- Hardcodes API keys or secrets

### ❌ Process Violations

- Doesn't use manage_todo_list for task tracking
- Implements features not in the Action Plan (scope creep)
- Skips tests for "simple" code
- Doesn't run tests to verify RED state

---

## ✅ Correct Workflow Evidence

### Correct Planning Evidence (Phase 1-2)

You should observe these behaviors in a compliant planning session:

**Gateway Verification (Phase 0):**
```
✅ Reading docs/ARCHITECTURE_PATTERNS.md...
✅ Self-check 1: Agent code can't import MemoryServiceClient because it violates two-layer abstraction...
✅ Self-check 2: Service endpoint is a REST API method; wrapper method is high-level context.* API...
✅ Gateway verification complete - proceeding to planning
```

**Master Plan Creation (Phase 1):**
```
✅ Loading docs/templates/Master_Plan_Template.md
✅ Reading docs/memory_system/README.md for context
✅ Filling Section 1: Executive Summary...
✅ Filling Section 2: Target Architecture (creating Mermaid diagram)...
✅ 48-Hour Filter: Phase 3 estimated at 60hr → proposing FDE fallback (use local storage instead of cluster)
✅ Saving to docs/memory_system/plans/MASTER_PLAN_SemanticSearch.md
```

**Action Plan Creation (Phase 2):**
```
✅ Loading docs/templates/Action_Plan_Template.md
✅ SDK Layer Verification:
   - Service Client: Adding search_semantic() to MemoryServiceClient ✅
   - Wrapper: Checking MemoryClient in context.py... ❌ search_semantic() MISSING
   - Action: Creating Task 1.1 (HIGH PRIORITY) to add wrapper method BEFORE service implementation
✅ Task sequence: 1.1 Wrapper → 1.2 Dependencies → 2 Tests → 3 Implementation
✅ TDD Strategy: Unit tests with mocked ChromaDB, integration tests with live instance
✅ Saving to docs/memory_system/plans/ACTION_PLAN_ChromaDBIntegration.md
```

### Correct TDD Evidence (Phase 3)

You should observe these behaviors in a TDD-compliant session:

### Correct Workflow Sequence

1. **Task Announcement**: "Starting Task 1.1: Create decisions.py DTOs"
2. **RED Step**:
   ```
   Creating tests/test_decisions.py first...
   Running pytest tests/test_decisions.py
   ❌ ImportError: cannot import name 'PlanAction' from 'soorma_common.decisions'
   ```
3. **GREEN Step**:
   ```
   Creating soorma_common/decisions.py with minimal implementation...
   Running pytest tests/test_decisions.py
   ✅ All tests passed
   ```
4. **REFACTOR Step**:
   ```
   Adding docstrings and type hints...
   Running pytest tests/test_decisions.py
   ✅ All tests still pass
   ```

### Correct File Creation Order

```
✅ CORRECT:
1. Create test_decisions.py (imports non-existent classes)
2. Run pytest (shows failures)
3. Create decisions.py (minimal implementation)
4. Run pytest (shows success)
5. Refactor decisions.py (add docs, types)
6. Run pytest (verify nothing broke)

❌ WRONG:
1. Create decisions.py (full implementation)
2. Create test_decisions.py (tests existing code)
3. Run pytest (tests pass immediately) ← No RED step!
```

---

## 🔧 Mid-Session Course Corrections

If you notice violations during a session, use these prompts:

### For Gateway Violations

```markdown
STOP. You violated Gateway Requirements (AGENT.md Section 2 Step 0).

You are working on SDK/services code but skipped ARCHITECTURE_PATTERNS.md.

Per the constitution:
- Read docs/ARCHITECTURE_PATTERNS.md in full (Sections 1-7)
- Answer self-check questions WITHOUT consulting docs
- Verify wrapper completeness for service changes

Please:
1. Read ARCHITECTURE_PATTERNS.md now
2. Answer the 3 self-check questions
3. Verify wrapper methods exist for planned service endpoints
4. Resume planning only after checklist complete

Restart with Gateway Verification now.
```

### For Planning Violations

```markdown
STOP. You violated Planning Requirements (AGENT.md Section 2 Step 1).

Issue: {You created plan from scratch instead of using templates | You didn't verify wrapper completeness | You skipped FDE evaluation}

Per the constitution:
- Use docs/templates/{Master_Plan_Template.md | Action_Plan_Template.md}
- Complete SDK Layer Verification section for service changes
- Evaluate 48-Hour Filter and propose FDE fallbacks

Please:
1. Load correct template from docs/templates/
2. Fill all required sections (especially SDK Layer Verification)
3. Add wrapper creation tasks BEFORE dependent tasks
4. Document FDE decisions for >48hr tasks
5. Save to correct location: docs/{feature-area}/plans/

Restart planning with template now.
```

### For TDD Violations

```markdown
STOP. You violated TDD (AGENT.md Section 2 Step 3).

You wrote {FILE_NAME} before tests. Per the constitution:
- RED: Write failing test FIRST
- GREEN: Implement minimal code
- REFACTOR: Clean up

Please:
1. Acknowledge the violation
2. Create test_{FILE_NAME} with failing tests
3. Show the RED state (test failures)
4. Re-implement {FILE_NAME} to pass those tests
5. Show the GREEN state (test success)

Restart with RED step now.
```

---

## 📊 Session Completion Checklists

### For Planning Sessions (Phase 0-2)

**Gateway Verification (Phase 0):**
- [ ] Read ARCHITECTURE_PATTERNS.md (all 7 sections)
- [ ] Answered all 3 self-check questions correctly
- [ ] Verified wrapper completeness for planned service changes
- [ ] Ready to proceed to Master/Action Plan creation

**Master Plan Completion (Phase 1):**
- [ ] Used docs/templates/Master_Plan_Template.md as base
- [ ] Filled all required sections (Summary, Architecture, Roadmap, Risks)
- [ ] Created Mermaid diagram for architecture flow
- [ ] Completed SDK Layer Impact Assessment (if applicable)
- [ ] Evaluated 48-Hour Filter for all phases
- [ ] Proposed FDE fallbacks for >48hr tasks
- [ ] Saved to docs/{feature-area}/plans/MASTER_PLAN_{FeatureName}.md
- [ ] Status set to 📋 Proposed

**Action Plan Completion (Phase 2):**
- [ ] Used docs/templates/Action_Plan_Template.md as base
- [ ] Filled all required sections (Requirements, Design, Tasks, TDD Strategy)
- [ ] Completed SDK Layer Verification checklist
- [ ] Identified missing wrapper methods (if any)
- [ ] Created wrapper creation tasks BEFORE dependent tasks
- [ ] Task sequence follows: Design → Tests → Logic
- [ ] TDD strategy defined (unit vs. integration)
- [ ] FDE decision documented
- [ ] Saved to docs/{feature-area}/plans/ACTION_PLAN_{TaskName}.md
- [ ] Status set to 📋 Planning

### For Implementation Sessions (Phase 3)

- [ ] All tasks in manage_todo_list marked completed
- [ ] All tests passing (unit + integration)
- [ ] No errors from `get_errors` tool
- [ ] CHANGELOG.md updated (if applicable)
- [ ] Code has type hints (all functions)
- [ ] Code has docstrings (all public methods/classes)
- [ ] Architecture compliance verified (if SDK/services work)
- [ ] No hardcoded secrets or API keys

---

## 🎯 Quick Copy Templates (Minimal Versions)

For experienced developers who need minimal prompts:

### Gateway Verification (Phase 0)

**HUMAN PROMPT:** Copy/paste this to start planning session.

```markdown
Gateway Verification for {feature-area} ({SDK|Services|Integration} work)

Feature: {Brief description of what you want to build}

AGENT INSTRUCTIONS - MANDATORY READING:
- [ ] docs/ARCHITECTURE_PATTERNS.md (Sections 1-7)
- [ ] Self-checks: wrapper pattern, authentication flow, multi-tenancy

Confirm completion, then proceed to planning.
```

### Master Plan (Phase 1)

**HUMAN PROMPT:** Copy/paste this to start planning session.

```markdown
Create Master Plan for {FeatureName}

Feature Description: {What you want built and why}

AGENT INSTRUCTIONS:
1. Use docs/templates/Master_Plan_Template.md
2. Read docs/{feature-area}/README.md + ARCHITECTURE.md
3. Fill: Summary, Architecture (Mermaid), Roadmap, Risks
4. SDK Layer Impact: List service endpoints + wrapper methods
5. 48-Hour Filter: Propose FDE for >48hr tasks
6. Save: docs/{feature-area}/plans/MASTER_PLAN_{FeatureName}.md

Confirm, then begin.
```

### Action Plan (Phase 2)

**HUMAN PROMPT:** Copy/paste this to start planning session.

```markdown
Create Action Plan for {TaskName}

Task Description: {From Master Plan OR standalone feature/bug description}

AGENT INSTRUCTIONS:
1. Use docs/templates/Action_Plan_Template.md
2. SDK Layer Verification: Service clients + Wrappers checklist
3. Add wrapper tasks BEFORE dependent tasks (HIGH PRIORITY)
4. Task sequence: Design → Tests → Logic
5. TDD Strategy: Unit + Integration approach
6. Save: docs/{feature-area}/plans/ACTION_PLAN_{TaskName}.md

Confirm, then begin.
```

### Implementation (Phase 3)

**HUMAN PROMPT:** Copy/paste this to start implementation session.

```markdown
I (human) have reviewed and approve {ACTION_PLAN_FILE}.

AGENT INSTRUCTIONS - MANDATORY WORKFLOW:
1. Read AGENT.md + Action Plan (including SDK Layer Verification)
2. Follow TDD: RED (failing tests) → GREEN (minimal code) → REFACTOR
3. Use manage_todo_list for task tracking
4. Use context.* wrappers (never direct service client imports in agent code)

Confirm you will write TESTS FIRST before any implementation, then begin.
```

---

## 📚 Related Documentation

- [AGENT.md](../AGENT.md) - Core developer constitution
- [ARCHITECTURE_PATTERNS.md](ARCHITECTURE_PATTERNS.md) - SDK architecture requirements
- [AI_ASSISTANT_GUIDE.md](AI_ASSISTANT_GUIDE.md) - General AI assistant guidance
- [CONTRIBUTING_REFERENCE.md](CONTRIBUTING_REFERENCE.md) - Technical reference (CLI, testing, patterns)

---

## 💡 Why This Matters

### Without Specification-Driven Development:
- **No Gateway:** Service changes leak low-level details into agent code → violates two-layer pattern
- **No Planning:** Features built ad-hoc → architectural debt compounds over time
- **No FDE Evaluation:** 48+ hour tasks block progress → platform bloat
- **No TDD:** Tests become afterthoughts → untestable code, missing edge cases

### With Specification-Driven Development:
- **Gateway Verification:** Wrapper completeness verified before implementation → maintains abstraction layers
- **Master Plans:** Strategic alignment → phased roadmaps prevent over-engineering
- **Action Plans:** Tactical clarity → task dependencies explicit, wrapper tasks prioritized
- **TDD Implementation:** Tests drive design → 100% coverage, better architecture
- **FDE Decisions:** Platform stays lean → ship value in <48hr cycles

### Real Impact

| Phase | Without Process | With Process |
|-------|----------------|--------------|
| **Gateway** | Service client imports in agent code | Clean two-layer abstraction |
| **Planning** | 3 weeks of implementation, then "doesn't fit architecture" | 2 hours planning, architecture-compliant design |
| **Implementation** | 500 lines untested code, 3 days debugging | 500 lines with tests, works first time |
| **Maintenance** | 2 hours to understand code path | 15 minutes (per 15-Minute Rule) |

**Bottom line:** 
- **Gateway:** 30 minutes upfront → Saves days of refactoring wrapper violations
- **Planning:** 2 hours planning → Saves weeks of wrong-direction implementation  
- **TDD:** 2 minutes RED step → Saves hours of debugging later

---

**Last Updated:** February 21, 2026  
**Related:** 
- [AGENT.md](../AGENT.md) - Core developer constitution (all workflow phases)
- [ARCHITECTURE_PATTERNS.md](ARCHITECTURE_PATTERNS.md) - SDK architecture requirements (Gateway prerequisite)
- [AI_ASSISTANT_GUIDE.md](AI_ASSISTANT_GUIDE.md) - General AI assistant guidance
- [CONTRIBUTING_REFERENCE.md](CONTRIBUTING_REFERENCE.md) - Technical reference (CLI, testing, patterns)
- [docs/templates/Master_Plan_Template.md](templates/Master_Plan_Template.md) - Master Plan template
- [docs/templates/Action_Plan_Template.md](templates/Action_Plan_Template.md) - Action Plan template
