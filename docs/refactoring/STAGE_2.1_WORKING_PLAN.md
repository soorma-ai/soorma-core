# Stage 2.1 Working Plan - Semantic Memory Enhancements & Working Memory Deletion

**Status:** 📋 Planning / Review  
**Created:** January 26, 2026  
**Updated:** January 26, 2026 - Added privacy requirements

---

## Overview

Stage 2.1 completes the Memory Service foundation with three critical features:
1. **Semantic Memory Upsert** - Prevent duplicate embeddings, support versioning (P1 - High)
2. **Semantic Memory Privacy** - Private by default (user-scoped), optional public flag (P1 - High)
3. **Working Memory Deletion** - Enable plan state cleanup (P2 - Medium)

**Total Estimated Effort:** 8-13 days

**Key Design Change:** Semantic memory is now **private by default** (user-scoped). This reflects the realization that semantic memory is **agent memory (CoALA framework)**, not a general RAG solution. Knowledge should be private to users unless explicitly marked public.

---

## Reference Design Documents

Before implementing any tasks, review the detailed design documents:

| Task | Architecture Design | SDK Design |
|------|---------------------|-----------|
| **Phase 1 (Upsert)** | [arch/02-MEMORY-SERVICE.md - RF-ARCH-012](arch/02-MEMORY-SERVICE.md#rf-arch-012-semantic-memory-upsert) | [sdk/02-MEMORY-SDK.md - RF-SDK-019](sdk/02-MEMORY-SDK.md#rf-sdk-019-semantic-memory-upsert-sdk) |
| **Phase 2 (Privacy)** | [arch/02-MEMORY-SERVICE.md - RF-ARCH-014](arch/02-MEMORY-SERVICE.md#rf-arch-014-semantic-memory-privacy) | [sdk/02-MEMORY-SDK.md - RF-SDK-021](sdk/02-MEMORY-SDK.md#rf-sdk-021-semantic-memory-privacy-sdk) |
| **Phase 3 (Deletion)** | [arch/02-MEMORY-SERVICE.md - RF-ARCH-013](arch/02-MEMORY-SERVICE.md#rf-arch-013-working-memory-deletion) | [sdk/02-MEMORY-SDK.md - RF-SDK-020](sdk/02-MEMORY-SDK.md#rf-sdk-020-working-memory-deletion-sdk) |

**Implementation Workflow:**
1. Read the reference design docs for your current phase
2. Work through tasks in the working plan (uses design docs as source of truth)
3. Code changes should follow the design document specs exactly
4. Tests should validate the design document requirements

---

## Phase 1: Semantic Memory Upsert (RF-ARCH-012 + RF-SDK-019)

**Priority:** P1 (High)  
**Estimated:** 2-3 days  
**Goal:** Prevent duplicate embeddings using external_id OR content_hash

### Background

Current implementation only prevents duplicates via tenant_id + content_hash. This means:
- ❌ Can't update existing knowledge by external ID (e.g., document ID)
- ❌ Different versions of same document create multiple embeddings
- ❌ No way to "upsert" - must query first, then insert or update

**Design Document:** [services/memory/SEMANTIC_MEMORY_UPSERT.md](../../services/memory/SEMANTIC_MEMORY_UPSERT.md)

### Architecture Changes (RF-ARCH-012)

#### Task 1: Read Existing Design Doc
- [ ] Review [services/memory/SEMANTIC_MEMORY_UPSERT.md](../../services/memory/SEMANTIC_MEMORY_UPSERT.md)
- [ ] Review [arch/02-MEMORY-SERVICE.md - RF-ARCH-012](arch/02-MEMORY-SERVICE.md#rf-arch-012-semantic-memory-upsert)
- [ ] Review [arch/02-MEMORY-SERVICE.md - RF-ARCH-014](arch/02-MEMORY-SERVICE.md#rf-arch-014-semantic-memory-privacy)
- [ ] Review [sdk/02-MEMORY-SDK.md - RF-SDK-019](sdk/02-MEMORY-SDK.md#rf-sdk-019-semantic-memory-upsert-sdk)
- [ ] Review [sdk/02-MEMORY-SDK.md - RF-SDK-021](sdk/02-MEMORY-SDK.md#rf-sdk-021-semantic-memory-privacy-sdk)
- [ ] Understand dual-constraint logic (external_id OR content_hash)
- [ ] Note RLS implications

#### Task 2: Database Schema Changes
**File:** `services/memory/src/db/migrations/` (new Alembic migration)

**Changes needed:**
```sql
-- Add columns
ALTER TABLE semantic_memory 
ADD COLUMN external_id VARCHAR(255),
ADD COLUMN content_hash VARCHAR(64);

-- Add unique constraint for external_id per tenant
CREATE UNIQUE INDEX idx_semantic_memory_tenant_external_id 
ON semantic_memory(tenant_id, external_id) 
WHERE external_id IS NOT NULL;

-- Keep existing content_hash constraint
-- (or add if not present)
CREATE UNIQUE INDEX idx_semantic_memory_tenant_content_hash 
ON semantic_memory(tenant_id, content_hash);
```

**Questions:**
- [ ] **Q1:** Should we create Alembic migration now, or handle separately?
- [ ] **Q2:** What should be the VARCHAR length for external_id? (255 seems reasonable)
- [ ] **Q3:** Should content_hash be nullable or required?

#### Task 3: Write Tests First (TDD)
**File:** `services/memory/test/test_semantic_crud.py`

**Test scenarios:**
```python
# Scenario 1: Upsert by external_id (version update)
test_upsert_by_external_id_creates_new()
test_upsert_by_external_id_updates_existing()
test_upsert_by_external_id_different_tenants()

# Scenario 2: Upsert by content_hash (deduplication)
test_upsert_by_content_hash_prevents_duplicate()
test_upsert_by_content_hash_different_content()

# Scenario 3: Both external_id and content_hash provided
test_upsert_both_ids_external_id_takes_precedence()

# Scenario 4: Neither provided (insert only)
test_insert_without_ids_allows_duplicates()

# Scenario 5: RLS enforcement
test_upsert_respects_tenant_isolation()
```

**Questions:**
- [ ] **Q4:** Should we enforce that at least ONE of (external_id, content_hash) must be provided?
- [ ] **Q5:** If both are provided, should external_id take precedence? Or error?

#### Task 4: Implement CRUD Function
**File:** `services/memory/src/crud/semantic.py`

**Reference Design:** [arch/02-MEMORY-SERVICE.md - RF-ARCH-012 CRUD Functions](arch/02-MEMORY-SERVICE.md#rf-arch-012-semantic-memory-upsert)

**Function signature:**
```python
async def upsert_semantic_memory(
    db: AsyncSession,
    tenant_id: str,
    content: str,
    embedding: List[float],
    metadata: Optional[Dict[str, Any]] = None,
    external_id: Optional[str] = None,
    content_hash: Optional[str] = None,
    tags: Optional[List[str]] = None,
    source: Optional[str] = None,
    plan_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> SemanticMemory:
    """
    Upsert semantic memory entry.
    
    Logic:
    1. If external_id provided: UPDATE existing or INSERT new
    2. Else if content_hash provided: UPDATE existing or INSERT new
    3. Else: INSERT new (no deduplication)
    """
```

**Implementation notes:**
- Use PostgreSQL `INSERT ... ON CONFLICT ... DO UPDATE`
- Ensure RLS policies are respected
- Update `updated_at` timestamp on conflict

#### Task 5: Update Service Layer
**File:** `services/memory/src/services/semantic.py`

**Changes:**
```python
async def store_knowledge(
    request: SemanticMemoryCreate,
    tenant_context: TenantContext,
    db: AsyncSession
) -> SemanticMemory:
    # Add external_id handling
    # Call upsert_semantic_memory instead of create
```

#### Task 6: Update API Endpoint
**File:** `services/memory/src/app/api/v1/semantic.py`

**Changes:**
```python
@router.post("/semantic", response_model=SemanticMemoryResponse)
async def store_knowledge(
    request: SemanticMemoryCreate,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db)
):
    # No changes needed if DTO updated in soorma-common
```

---

### SDK Changes (RF-SDK-019)

#### Task 7: Update DTO in soorma-common
**File:** `libs/soorma-common/src/soorma_common/models/memory.py`

**Changes:**
```python
class SemanticMemoryCreate(BaseModel):
    content: str
    embedding: List[float]
    metadata: Optional[Dict[str, Any]] = None
    external_id: Optional[str] = None  # NEW
    tags: Optional[List[str]] = None
    source: Optional[str] = None
    plan_id: Optional[str] = None
    session_id: Optional[str] = None
```

**Questions:**
- [ ] **Q6:** Should external_id be optional for backward compatibility? (Assuming YES)

#### Task 8: Write SDK Tests First (TDD)
**File:** `sdk/python/tests/test_memory_client.py`

**Test scenarios:**
```python
# Upsert by external_id
test_store_knowledge_with_external_id_creates()
test_store_knowledge_with_external_id_updates()

# Upsert by content (implicit content_hash)
test_store_knowledge_deduplicates_by_content()

# Backward compatibility
test_store_knowledge_without_external_id_works()
```

#### Task 9: Update MemoryClient Method
**File:** `sdk/python/soorma/memory/client.py`

**Changes:**
```python
async def store_knowledge(
    self,
    content: str,
    embedding: List[float],
    metadata: Optional[Dict[str, Any]] = None,
    external_id: Optional[str] = None,  # NEW parameter
    tags: Optional[List[str]] = None,
    source: Optional[str] = None,
    plan_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Store knowledge in semantic memory with optional deduplication.
    
    Args:
        external_id: Optional unique identifier for versioning/updating
                    If provided, will update existing entry with same external_id
    """
```

---

## Phase 2: Semantic Memory Privacy (RF-ARCH-014 + RF-SDK-021)

**Priority:** P1 (High)  
**Estimated:** 2-3 days  
**Goal:** Make semantic memory private by default (user-scoped) with optional public flag

### Background

**Key Insight:** Semantic memory is **agent memory (CoALA framework)**, not a general RAG solution.

Original design was tenant-wide (public to all users in tenant). Through examples development, we realized:
- ❌ Agent memory should be private to the user by default
- ❌ Cross-user memory leakage is a privacy/security concern
- ✅ Knowledge should only be public when explicitly marked
- ✅ Semantic memory ≠ RAG database (that's a separate concern)

**Use Cases:**
- **Private (default):** User's research findings, personal notes, conversation history
- **Public (explicit):** Shared team knowledge, organization-wide facts, approved documents

### Architecture Changes (RF-ARCH-014)

#### Task 10: Database Schema Changes
**File:** `services/memory/src/db/migrations/` (new Alembic migration)

**Reference Design:** [arch/02-MEMORY-SERVICE.md - RF-ARCH-014 Database Schema](arch/02-MEMORY-SERVICE.md#rf-arch-014-semantic-memory-privacy)

**Changes needed:**
```sql
-- Add user_id column (required)
ALTER TABLE semantic_memory 
ADD COLUMN user_id VARCHAR(255) NOT NULL;

-- Add is_public flag (default private)
ALTER TABLE semantic_memory 
ADD COLUMN is_public BOOLEAN NOT NULL DEFAULT FALSE;

-- Update unique constraints to include user_id
-- For external_id: unique per user (unless public)
CREATE UNIQUE INDEX idx_semantic_memory_user_external_id 
ON semantic_memory(tenant_id, user_id, external_id) 
WHERE external_id IS NOT NULL AND is_public = FALSE;

-- For public knowledge: unique per tenant
CREATE UNIQUE INDEX idx_semantic_memory_tenant_external_id_public
ON semantic_memory(tenant_id, external_id) 
WHERE external_id IS NOT NULL AND is_public = TRUE;

-- Content hash: unique per user (unless public)
CREATE UNIQUE INDEX idx_semantic_memory_user_content_hash 
ON semantic_memory(tenant_id, user_id, content_hash)
WHERE is_public = FALSE;

CREATE UNIQUE INDEX idx_semantic_memory_tenant_content_hash_public
ON semantic_memory(tenant_id, content_hash)
WHERE is_public = TRUE;
```

**Questions:**
- [ ] **Q10:** Should we backfill existing rows with a system user_id, or require manual migration?
- [ ] **Q11:** Should querying public knowledge also return user's private knowledge? (Answer: Yes, union)

#### Task 11: Update RLS Policies
**File:** `services/memory/src/db/rls_policies.sql` (or migration)

**Reference Design:** [arch/02-MEMORY-SERVICE.md - RF-ARCH-014 RLS Policies](arch/02-MEMORY-SERVICE.md#rf-arch-014-semantic-memory-privacy)

**New policies:**
```sql
-- Read: Users can read their own private knowledge OR public knowledge in their tenant
CREATE POLICY semantic_memory_read_policy ON semantic_memory
FOR SELECT
USING (
  (tenant_id = current_setting('app.current_tenant_id')::TEXT)
  AND (
    (user_id = current_setting('app.current_user_id')::TEXT) OR
    (is_public = TRUE)
  )
);

-- Write: Users can only write their own private knowledge
-- (public knowledge requires separate permission check)
CREATE POLICY semantic_memory_write_policy ON semantic_memory
FOR INSERT
WITH CHECK (
  (tenant_id = current_setting('app.current_tenant_id')::TEXT)
  AND (user_id = current_setting('app.current_user_id')::TEXT)
);

-- Update: Users can only update their own knowledge
CREATE POLICY semantic_memory_update_policy ON semantic_memory
FOR UPDATE
USING (
  (tenant_id = current_setting('app.current_tenant_id')::TEXT)
  AND (user_id = current_setting('app.current_user_id')::TEXT)
);
```

**Questions:**
- [ ] **Q12:** Should there be a separate "admin" role that can create public knowledge?
- [ ] **Q13:** Can users update their private knowledge to public, or is that admin-only?

#### Task 12: Write Tests First (TDD)
**File:** `services/memory/test/test_semantic_crud.py`

**Test scenarios:**
```python
# Privacy isolation
test_private_knowledge_not_visible_to_other_users()
test_private_knowledge_visible_to_owner()

# Public knowledge
test_public_knowledge_visible_to_all_users_in_tenant()
test_public_knowledge_not_visible_across_tenants()

# Upsert with privacy
test_upsert_private_knowledge_by_external_id()
test_upsert_public_knowledge_by_external_id()
test_upsert_respects_user_id_constraint()

# Query behavior
test_query_returns_private_and_public_knowledge()
test_query_filters_by_user_id_correctly()

# Edge cases
test_cannot_update_other_users_private_knowledge()
test_can_create_duplicate_content_for_different_users()
```

#### Task 13: Update CRUD Functions
**File:** `services/memory/src/crud/semantic.py`

**Reference Design:** [arch/02-MEMORY-SERVICE.md - RF-ARCH-014 CRUD Functions](arch/02-MEMORY-SERVICE.md#rf-arch-014-semantic-memory-privacy)

**Updated signature:**
```python
async def upsert_semantic_memory(
    db: AsyncSession,
    tenant_id: str,
    user_id: str,  # NEW: Required
    content: str,
    embedding: List[float],
    metadata: Optional[Dict[str, Any]] = None,
    external_id: Optional[str] = None,
    content_hash: Optional[str] = None,
    is_public: bool = False,  # NEW: Default private
    tags: Optional[List[str]] = None,
    source: Optional[str] = None,
    plan_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> SemanticMemory:
    """
    Upsert semantic memory entry (private by default).
    """

async def query_semantic_memory(
    db: AsyncSession,
    tenant_id: str,
    user_id: str,  # NEW: Required
    query_embedding: List[float],
    top_k: int = 10,
    include_public: bool = True,  # NEW: Include public knowledge by default
) -> List[SemanticMemory]:
    """
    Query semantic memory (user's private + public knowledge).
    """
```

#### Task 14: Update Service Layer
**File:** `services/memory/src/services/semantic.py`

**Changes:**
- Extract user_id from TenantContext
- Pass user_id to CRUD functions
- Validate is_public flag permissions (if needed)

#### Task 15: Update API Endpoints
**File:** `services/memory/src/app/api/v1/semantic.py`

**No changes needed** if user_id is extracted from TenantContext.

---

### SDK Changes (RF-SDK-021)

#### Task 16: Update DTO in soorma-common
**File:** `libs/soorma-common/src/soorma_common/models/memory.py`

**Reference Design:** [arch/02-MEMORY-SERVICE.md - RF-ARCH-014 API Update](arch/02-MEMORY-SERVICE.md#rf-arch-014-semantic-memory-privacy)

**Changes:**
```python
class SemanticMemoryCreate(BaseModel):
    content: str
    embedding: List[float]
    metadata: Optional[Dict[str, Any]] = None
    external_id: Optional[str] = None
    user_id: str  # NEW: Required
    is_public: bool = False  # NEW: Default private
    tags: Optional[List[str]] = None
    source: Optional[str] = None
    plan_id: Optional[str] = None
    session_id: Optional[str] = None

class SemanticMemoryQuery(BaseModel):
    query_embedding: List[float]
    top_k: int = 10
    user_id: str  # NEW: Required
    include_public: bool = True  # NEW: Include public knowledge
    filters: Optional[Dict[str, Any]] = None
```

#### Task 17: Write SDK Tests First (TDD)
**File:** `sdk/python/tests/test_memory_client.py`

**Test scenarios:**
```python
# Store private knowledge
test_store_knowledge_private_by_default()
test_store_knowledge_requires_user_id()

# Store public knowledge
test_store_knowledge_public_flag()

# Query behavior
test_query_knowledge_returns_private_and_public()
test_query_knowledge_filters_by_user_id()
test_query_knowledge_exclude_public()
```

#### Task 18: Update MemoryClient Method
**File:** `sdk/python/soorma/memory/client.py`

**Reference Design:** [sdk/02-MEMORY-SDK.md - RF-SDK-021 MemoryClient Updates](sdk/02-MEMORY-SDK.md#rf-sdk-021-semantic-memory-privacy-sdk)

**Changes:**
```python
async def store_knowledge(
    self,
    content: str,
    embedding: List[float],
    user_id: str,  # NEW: Required parameter
    metadata: Optional[Dict[str, Any]] = None,
    external_id: Optional[str] = None,
    is_public: bool = False,  # NEW: Default private
    tags: Optional[List[str]] = None,
    source: Optional[str] = None,
    plan_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Store knowledge in semantic memory (private by default).
    
    Args:
        user_id: Required. User who owns this knowledge.
        is_public: If True, knowledge is visible to all users in tenant.
                  If False (default), only visible to this user.
    """

async def query_knowledge(
    self,
    query_embedding: List[float],
    user_id: str,  # NEW: Required parameter
    top_k: int = 10,
    include_public: bool = True,  # NEW: Include public knowledge
    filters: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Query semantic memory (user's private + optional public knowledge).
    
    Args:
        user_id: Required. User performing the query.
        include_public: If True (default), includes public knowledge.
                       If False, only returns user's private knowledge.
    """
```

---

## Phase 3: Working Memory Deletion (RF-ARCH-013 + RF-SDK-020)

**Priority:** P2 (Medium)  
**Estimated:** 1-2 days  
**Goal:** Enable cleanup of plan-scoped working memory

### Background

Current implementation only supports SET/GET for working memory. No DELETE means:
- ❌ Completed plans accumulate state data indefinitely
- ❌ No way to explicitly clean up sensitive data
- ❌ Test cleanup requires direct DB access

### Architecture Changes (RF-ARCH-013)

#### Task 19: Write Tests First (TDD)
**File:** `services/memory/test/test_working_crud.py`

**Test scenarios:**
```python
# Delete individual key
test_delete_working_memory_key()
test_delete_working_memory_key_not_found()

# Delete all keys for plan
test_delete_all_working_memory_for_plan()
test_delete_all_working_memory_empty_plan()

# RLS enforcement
test_delete_respects_tenant_isolation()

# Edge cases
test_delete_with_invalid_plan_id()
```

#### Task 20: Implement CRUD Functions
**File:** `services/memory/src/crud/working.py`

**New functions:**
```python
async def delete_working_memory_key(
    db: AsyncSession,
    tenant_id: str,
    plan_id: str,
    key: str,
) -> bool:
    """Delete a single working memory key."""

async def delete_working_memory_plan(
    db: AsyncSession,
    tenant_id: str,
    plan_id: str,
) -> int:
    """Delete all working memory for a plan. Returns count deleted."""
```

#### Task 21: Add API Endpoints
**Files:** 
- `services/memory/src/services/working.py` (service layer)
- `services/memory/src/app/api/v1/working.py` (API routes)

**New endpoints:**
```python
@router.delete("/working/{plan_id}/{key}")
async def delete_working_memory_key(
    plan_id: str,
    key: str,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Delete a single working memory key for a plan."""

@router.delete("/working/{plan_id}")
async def delete_working_memory_plan(
    plan_id: str,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Delete all working memory for a plan."""
```

---

### SDK Changes (RF-SDK-020)

#### Task 22: Write SDK Tests First (TDD)
**File:** `sdk/python/tests/test_memory_client.py`

**Test scenarios:**
```python
# Delete single key
test_delete_plan_state_key()
test_delete_plan_state_key_not_found()

# Delete all keys
test_delete_plan_state_all_keys()

# WorkflowState helper
test_workflow_state_delete_key()
test_workflow_state_cleanup_all()
```

#### Task 23: Add MemoryClient Methods
**File:** `sdk/python/soorma/memory/client.py`

**New methods:**
```python
async def delete_plan_state(
    self,
    plan_id: str,
    key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Delete working memory state for a plan.
    
    Args:
        plan_id: The plan identifier
        key: Optional specific key to delete. If None, deletes all keys.
    """
```

#### Task 24: Update WorkflowState Helper
**File:** `sdk/python/soorma/workflow.py`

**New methods:**
```python
class WorkflowState:
    async def delete(self, key: str) -> bool:
        """Delete a specific state key."""
        
    async def cleanup(self) -> int:
        """Delete all state for this plan. Returns count deleted."""
```

**Usage documentation:**
```python
# Pattern 1: Explicit cleanup (recommended for sensitive data)
state = WorkflowState(context, plan_id)
await state.cleanup()

# Pattern 2: Selective cleanup
await state.delete("temporary_data")

# Pattern 3: Accept persistence (default - no cleanup)
# Working memory will remain until manually deleted
```

**Questions:**
- [ ] **Q7:** Should WorkflowState.cleanup() be called automatically on plan completion?
- [ ] **Q8:** Should we add a TTL feature for automatic expiration? (Future enhancement?)
- [ ] **Q9:** Document best practices - when to cleanup vs when to persist?

---

## Phase 4: Final Validation & Documentation

#### Task 25: Update CHANGELOG Files

**Files to update:**
- `services/memory/CHANGELOG.md`
- `sdk/python/CHANGELOG.md`
- `libs/soorma-common/CHANGELOG.md`

**Entry format:**
```markdown
## [Unreleased]

### Added
- RF-ARCH-012: Semantic memory upsert with external_id and content_hash
- RF-ARCH-014: Semantic memory privacy (user-scoped by default, optional public flag)
- RF-ARCH-013: DELETE endpoints for working memory cleanup
- RF-SDK-019: external_id parameter to store_knowledge() for versioning
- RF-SDK-021: user_id (required) and is_public parameters for semantic memory privacy
- RF-SDK-020: delete_plan_state() method and WorkflowState cleanup helpers

### Changed
- SemanticMemoryCreate DTO now includes optional external_id, required user_id, and optional is_public fields
- Semantic memory queries now filter by user_id and optionally include public knowledge
```

#### Task 26: Run Full Test Suite

**Commands:**
```bash
# Memory Service tests
cd services/memory
pytest test/ -v
# Expected: All tests pass (37+ new tests)

# SDK tests
cd sdk/python
pytest tests/ -v
# Expected: All tests pass (192+ new tests)

# soorma-common tests
cd libs/soorma-common
pytest tests/ -v
# Expected: All tests pass (44+ new tests)
```

---

## Open Questions Summary

### Critical (Need answers before starting)

- [ ] **Q1:** Should we create Alembic migration now, or handle separately?
  - **Recommendation:** Create migration as part of RF-ARCH-012 and RF-ARCH-014
  
- [ ] **Q4:** Should we enforce that at least ONE of (external_id, content_hash) must be provided?
  - **Recommendation:** No - allow INSERT without either for flexibility
  
- [ ] **Q5:** If both external_id and content_hash are provided, should external_id take precedence? Or error?
  - **Recommendation:** external_id takes precedence (more explicit)

- [ ] **Q6:** Should external_id be optional for backward compatibility?
  - **Recommendation:** YES - optional field

- [ ] **Q10:** Should we backfill existing rows with a system user_id, or require manual migration?
  - **Recommendation:** Add a migration script with default user_id (e.g., "system" or "legacy")

- [ ] **Q11:** Should querying public knowledge also return user's private knowledge?
  - **Answer:** YES - union of user's private knowledge + public knowledge

- [ ] **Q12:** Should there be a separate "admin" role that can create public knowledge?
  - **Recommendation:** Not in this phase - allow any user to create public knowledge for now
  
- [ ] **Q13:** Can users update their private knowledge to public, or is that admin-only?
  - **Recommendation:** Allow users to update is_public flag for their own knowledge

### Important (Can decide during implementation)

- [ ] **Q2:** What should be VARCHAR length for external_id?
  - **Recommendation:** 255 (standard for IDs)
  
- [ ] **Q3:** Should content_hash be nullable or required?
  - **Current:** Nullable, auto-generated if not provided
  
- [ ] **Q7:** Should WorkflowState.cleanup() be called automatically on plan completion?
  - **Recommendation:** NO - explicit is better than implicit
  
- [ ] **Q8:** Should we add a TTL feature for automatic expiration?
  - **Recommendation:** Future enhancement (Stage 3+)
  
- [ ] **Q9:** Document best practices - when to cleanup vs when to persist?
  - **Recommendation:** Add usage guide in SDK docs

---

## Implementation Strategy

### Coordination Points

**Service ↔ SDK alignment:**
1. Phase 1 (Semantic Upsert): Complete architecture before SDK
2. Phase 2 (Privacy): Can parallelize database work and DTO updates
3. Phase 3 (Deletion): Can parallelize CRUD + SDK work

### Suggested Order

**Week 1 (Days 1-3): Semantic Memory Upsert**
1. ✅ Review design doc (Task 1)
2. ✅ Answer open questions Q1-Q6, Q10-Q13
3. 🔨 Database migration for upsert fields (Task 2)
4. 🔨 Service tests + implementation (Tasks 3-6)
5. 🔨 DTO update in soorma-common (Task 7)
6. 🔨 SDK tests + implementation (Tasks 8-9)
7. ✅ Validate Phase 1 complete

**Week 1-2 (Days 3-6): Semantic Memory Privacy**
8. 🔨 Database migration for privacy fields (Task 10)
9. 🔨 Update RLS policies (Task 11)
10. 🔨 Privacy tests + CRUD implementation (Tasks 12-13)
11. 🔨 Service layer updates (Tasks 14-15)
12. 🔨 DTO updates in soorma-common (Task 16)
13. 🔨 SDK tests + implementation (Tasks 17-18)
14. ✅ Validate Phase 2 complete

**Week 2 (Days 7-9): Working Memory Deletion**
15. 🔨 Working memory deletion tests (Task 19)
16. 🔨 CRUD + API implementation (Tasks 20-21)
17. 🔨 SDK tests + implementation (Tasks 22-24)
18. ✅ Validate Phase 3 complete

**Final (Days 9-10): Validation & Documentation**
19. 📝 Update all CHANGELOGs (Task 25)
20. ✅ Run full test suite (Task 26)
21. 📝 Update refactoring README status

---

## Success Criteria

- [ ] **Semantic Upsert:** Can update existing knowledge by external_id
- [ ] **Semantic Upsert:** Duplicate content (by hash) prevented
- [ ] **Semantic Upsert:** Backward compatible (external_id optional)
- [ ] **Privacy:** Semantic memory is private by default (user-scoped)
- [ ] **Privacy:** Users can explicitly mark knowledge as public
- [ ] **Privacy:** Queries return user's private + public knowledge
- [ ] **Privacy:** RLS enforces user isolation for private knowledge
- [ ] **Deletion:** Can delete individual working memory keys
- [ ] **Deletion:** Can delete all keys for a plan
- [ ] **Deletion:** WorkflowState helper provides convenient cleanup
- [ ] **Tests:** All service tests pass (50+ total, up from 37)
- [ ] **Tests:** All SDK tests pass (210+ total, up from 192)
- [ ] **Tests:** All soorma-common tests pass (50+ total, up from 44)
- [ ] **Docs:** CHANGELOGs updated for all components
- [ ] **RLS:** Tenant isolation enforced in all operations
- [ ] **Breaking Change:** Existing semantic memory calls require user_id parameter

---

## Notes & Feedback

<!-- Use this section for iteration notes, decisions made during planning -->

### Planning Session 1 (Jan 26, 2026)

**Decisions:**
- TBD

**Changes to plan:**
- TBD

**Blockers:**
- TBD

---

## Next Steps

1. **Review this plan** - Add feedback, answer questions, adjust priorities
2. **Answer open questions** - Make decisions on Q1-Q9
3. **Mark task 1 complete** - Update todo list
4. **Begin implementation** - Start with Task 1 (read design doc)

---

**Status:** ⏸️ Waiting for review and feedback
