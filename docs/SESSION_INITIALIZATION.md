# AI Assistant Session Initialization Guide

**Purpose:** Ensure consistent, TDD-compliant development sessions for soorma-core contributions.

This guide is mandatory for all AI-assisted implementation sessions to enforce constitutional requirements from [AGENT.md](../AGENT.md).

---

## 📋 Pre-Session Checklist

Before starting any implementation session:

- [ ] Action Plan reviewed and approved by human developer
- [ ] [ARCHITECTURE_PATTERNS.md](ARCHITECTURE_PATTERNS.md) read if working on SDK/services
- [ ] Dependencies installed (if adding new libraries)
- [ ] Understanding of TDD workflow (RED → GREEN → REFACTOR)

---

## 🎯 Session Start Template

**Copy/paste this template at the start of EVERY implementation session:**

```markdown
# Session Goal
Implement {ACTION_PLAN_NAME} from {ACTION_PLAN_FILE_PATH}

# Constitutional Requirements (MANDATORY)
I have read and approve the action plan. Before starting implementation:

1. **Read Constitution**: You MUST read /path/to/soorma-core/AGENT.md in full
2. **Read Action Plan**: You MUST read {ACTION_PLAN_FILE_PATH} including Section 0 (Gateway Verification)
3. **Confirm TDD Workflow**: You MUST follow strict Test-Driven Development:
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

If you understand and will follow this process, acknowledge and begin Task 1 with RED (tests first).
```

---

## ✅ Example Session Initialization

Here's a real example from Stage 4 Phase 2:

```markdown
# Session Goal
Implement Stage 4 Phase 2 - Type-Safe Decisions from docs/agent_patterns/plans/ACTION_PLAN_Stage4_Phase2_Implementation.md

# Constitutional Requirements (MANDATORY)
I have read and approve the action plan. Before starting implementation:

1. **Read Constitution**: You MUST read AGENT.md in full
2. **Read Action Plan**: You MUST read docs/agent_patterns/plans/ACTION_PLAN_Stage4_Phase2_Implementation.md including Section 0
3. **Confirm TDD Workflow**: You MUST follow strict Test-Driven Development:
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

If you understand and will follow this process, acknowledge and begin Task 1 with RED (tests first).
```

---

## 🚨 Red Flags to Watch For

If the AI assistant does ANY of these, **STOP immediately** and issue a correction:

### ❌ TDD Violations

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

## ✅ Correct TDD Evidence

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

## 🔧 Mid-Session Course Correction

If you notice TDD violations during a session, use this prompt:

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

## 📊 Session Completion Checklist

Before ending a session, verify:

- [ ] All tasks in manage_todo_list marked completed
- [ ] All tests passing (unit + integration)
- [ ] No errors from `get_errors` tool
- [ ] CHANGELOG.md updated (if applicable)
- [ ] Code has type hints (all functions)
- [ ] Code has docstrings (all public methods/classes)
- [ ] Architecture compliance verified (if SDK/services work)
- [ ] No hardcoded secrets or API keys

---

## 🎯 Quick Copy Template (Minimal Version)

For experienced developers who need a minimal prompt:

```markdown
I have reviewed and approve {ACTION_PLAN_FILE}.

MANDATORY WORKFLOW:
1. Read AGENT.md + Action Plan (including Section 0)
2. Follow TDD: RED (failing tests) → GREEN (minimal code) → REFACTOR
3. Use manage_todo_list for task tracking

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

**Without this process:**
- Tests become afterthoughts (post-facto validation)
- Implementation-first leads to untestable code
- Missing test coverage for edge cases
- Constitutional violations go unnoticed

**With this process:**
- Tests drive design (better architecture)
- 100% test coverage guaranteed
- Edge cases caught early
- Architecture compliance enforced

**Bottom line:** This 2-minute initialization saves hours of refactoring later.

---

**Last Updated:** February 21, 2026  
**Related:** [AGENT.md Section 2: Workflow Rituals](../AGENT.md#2-workflow-rituals-hierarchical-planning--tdd)
