# Semantic Memory Upsert Design

**Status:** 📝 Design Document  
**Last Updated:** January 22, 2026  
**Author:** System Architecture Team

## Overview

This document describes the design for semantic memory upsert functionality, enabling both **document versioning** (application-controlled updates) and **automatic deduplication** (system-level protection) in the Memory Service.

---

## Problem Statement

### Current Limitations

**Schema:**
```python
class SemanticMemory(Base):
    id = Column(UUID, primary_key=True)              # Random UUID
    tenant_id = Column(UUID, FK, not null)
    content = Column(Text, not null)                 # No uniqueness
    embedding = Column(Vector(1536))
    memory_metadata = Column(JSON, default={})
    created_at = Column(DateTime)
    updated_at = Column(DateTime)                     # Has timestamp but no update mechanism
    
    # NO unique constraints
```

**Issues:**
1. **No document versioning**: Cannot replace outdated content (e.g., v2 of API docs)
2. **Duplicate prevention is manual**: Applications must search before storing
3. **No true updates**: Only append-only inserts, no way to update existing records
4. **Performance penalty**: Search-based deduplication is slow and unreliable

### Use Cases

| Scenario | Current Behavior | Desired Behavior |
|----------|------------------|------------------|
| **Doc update** | v1 and v2 both stored as separate records | v2 replaces v1 (same logical document) |
| **Script re-run** | Duplicate facts created | Silently skip duplicates |
| **Content change** | No way to update existing | Update content + regenerate embedding |
| **Exact duplicate** | Requires pre-search check | DB-level rejection |

---

## Solution: 3-Level Hybrid Approach

### Level 1: External ID (Application-Controlled Versioning)

**Purpose:** Enable applications to identify and update logical documents.

```python
external_id = Column(String(255), nullable=True)  # e.g., "doc:api-guide:v2"

__table_args__ = (
    UniqueConstraint("tenant_id", "external_id", 
                     name="unique_external_id_per_tenant"),
)
```

**Example:**
```python
# Initial storage
await context.memory.store_knowledge(
    content="API v1 documentation...",
    external_id="doc:api-guide",
    metadata={"version": "1.0"}
)

# Later update (replaces previous)
await context.memory.store_knowledge(
    content="API v2 documentation...",
    external_id="doc:api-guide",  # Same ID
    metadata={"version": "2.0"}
)
# Result: Only v2 exists in database
```

### Level 2: Content Hash (System-Level Deduplication)

**Purpose:** Automatically prevent exact content duplicates without application logic.

```python
content_hash = Column(String(64), nullable=False)  # SHA256(content)

__table_args__ = (
    UniqueConstraint("tenant_id", "content_hash", 
                     name="unique_content_per_tenant"),
)
```

**Example:**
```python
# First run
await context.memory.store_knowledge(
    content="Python is a programming language"
)
# Creates new record

# Second run (same script)
await context.memory.store_knowledge(
    content="Python is a programming language"  # Identical content
)
# Database constraint prevents duplicate, silently updates timestamp
```

### Level 3: Smart Upsert API

**Purpose:** Single API that handles both update modes intelligently.

```python
async def store_knowledge(
    content: str,
    user_id: str,
    external_id: Optional[str] = None,
    metadata: Optional[Dict] = None,
) -> str:
    """
    Store or update knowledge (smart upsert).
    
    Behavior:
    - If external_id provided: Upsert by external_id (app-controlled)
    - If no external_id: Insert with content_hash (auto-dedupe)
    - On conflict: Update content + regenerate embedding if changed
    
    Returns:
        Memory ID (str)
    """
```

---

## Schema Design

### Database Model

```python
class SemanticMemory(Base):
    """Semantic memory with versioning and deduplication support."""
    
    __tablename__ = "semantic_memory"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Tenant isolation
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    # Application-controlled versioning (LEVEL 1)
    external_id = Column(
        String(255), 
        nullable=True,
        comment="Optional application-provided ID for document versioning"
    )
    
    # System-level deduplication (LEVEL 2)
    content_hash = Column(
        String(64), 
        nullable=False,
        comment="SHA256 hash of content for automatic deduplication"
    )
    
    # Content and embeddings
    content = Column(Text, nullable=False)
    embedding = Column(Vector(1536))
    memory_metadata = Column(JSON, default={}, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow, 
        nullable=False
    )
    
    # Constraints
    __table_args__ = (
        # App-controlled uniqueness (when external_id provided)
        UniqueConstraint(
            "tenant_id", "external_id",
            name="unique_external_id_per_tenant"
        ),
        
        # System-level deduplication (always enforced)
        UniqueConstraint(
            "tenant_id", "content_hash",
            name="unique_content_per_tenant"
        ),
        
        # Indexes for fast lookups
        Index("idx_semantic_external_id", "tenant_id", "external_id"),
        Index("idx_semantic_content_hash", "tenant_id", "content_hash"),
    )
```

### Migration (Alembic)

```python
"""Add external_id and content_hash for upsert support

Revision ID: 002_semantic_upsert
"""

def upgrade() -> None:
    # Add new columns
    op.add_column('semantic_memory', 
        sa.Column('external_id', sa.String(255), nullable=True))
    op.add_column('semantic_memory', 
        sa.Column('content_hash', sa.String(64), nullable=True))
    
    # Backfill content_hash for existing records
    op.execute("""
        UPDATE semantic_memory 
        SET content_hash = encode(sha256(content::bytea), 'hex')
        WHERE content_hash IS NULL
    """)
    
    # Make content_hash required
    op.alter_column('semantic_memory', 'content_hash', nullable=False)
    
    # Add unique constraints
    op.create_unique_constraint(
        'unique_external_id_per_tenant',
        'semantic_memory',
        ['tenant_id', 'external_id']
    )
    op.create_unique_constraint(
        'unique_content_per_tenant',
        'semantic_memory',
        ['tenant_id', 'content_hash']
    )
    
    # Add indexes
    op.create_index(
        'idx_semantic_external_id',
        'semantic_memory',
        ['tenant_id', 'external_id']
    )
    op.create_index(
        'idx_semantic_content_hash',
        'semantic_memory',
        ['tenant_id', 'content_hash']
    )

def downgrade() -> None:
    op.drop_index('idx_semantic_content_hash')
    op.drop_index('idx_semantic_external_id')
    op.drop_constraint('unique_content_per_tenant', 'semantic_memory')
    op.drop_constraint('unique_external_id_per_tenant', 'semantic_memory')
    op.drop_column('semantic_memory', 'content_hash')
    op.drop_column('semantic_memory', 'external_id')
```

---

## API Design

### DTOs (soorma-common/models.py)

```python
class SemanticMemoryCreate(BaseDTO):
    """Create or update semantic memory."""
    content: str = Field(..., description="Knowledge content")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Additional metadata"
    )
    external_id: Optional[str] = Field(
        None,
        description="Optional application-provided ID for versioning. "
                    "If provided, updates existing record with same external_id."
    )

class SemanticMemoryResponse(BaseDTO):
    """Semantic memory response."""
    id: str = Field(..., description="Memory ID")
    tenant_id: str = Field(..., description="Tenant ID")
    external_id: Optional[str] = Field(None, description="External ID (if provided)")
    content: str = Field(..., description="Knowledge content")
    content_hash: str = Field(..., description="Content hash (SHA256)")
    metadata: Dict[str, Any] = Field(..., description="Additional metadata")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    score: Optional[float] = Field(None, description="Similarity score (for search)")
    
    # NEW: Indicate what happened
    action: Optional[str] = Field(
        None,
        description="Action taken: 'created', 'updated', 'duplicate_skipped'"
    )
```

### CRUD Layer (memory_service/crud/semantic.py)

```python
import hashlib
from sqlalchemy.dialects.postgresql import insert

async def upsert_semantic_memory(
    db: AsyncSession,
    tenant_id: UUID,
    data: SemanticMemoryCreate,
) -> Tuple[SemanticMemory, str]:
    """
    Insert or update semantic memory (smart upsert).
    
    Logic:
    1. Calculate content_hash = SHA256(content)
    2. Generate embedding for content
    3. If external_id provided:
       - Upsert by external_id (app-controlled versioning)
       - Always update content, hash, embedding
    4. If no external_id:
       - Upsert by content_hash (system deduplication)
       - On conflict, only touch updated_at
    
    Returns:
        Tuple of (memory record, action)
        action: 'created', 'updated', or 'duplicate_skipped'
    """
    # Calculate content hash
    content_hash = hashlib.sha256(data.content.encode('utf-8')).hexdigest()
    
    # Generate embedding
    embedding = await embedding_service.generate_embedding(data.content)
    
    # Prepare base values
    values = {
        'tenant_id': tenant_id,
        'content': data.content,
        'content_hash': content_hash,
        'embedding': embedding,
        'memory_metadata': data.metadata,
    }
    
    if data.external_id:
        # Path 1: App-controlled versioning via external_id
        values['external_id'] = data.external_id
        
        stmt = insert(SemanticMemory).values(**values)
        stmt = stmt.on_conflict_do_update(
            constraint='unique_external_id_per_tenant',
            set_={
                'content': data.content,
                'content_hash': content_hash,
                'embedding': embedding,
                'memory_metadata': data.metadata,
                'updated_at': datetime.now(timezone.utc),
            }
        ).returning(
            SemanticMemory,
            # PostgreSQL-specific: check if row was inserted or updated
            literal_column("(xmax = 0)").label("inserted")
        )
        
    else:
        # Path 2: System-level deduplication via content_hash
        stmt = insert(SemanticMemory).values(**values)
        stmt = stmt.on_conflict_do_update(
            constraint='unique_content_per_tenant',
            set_={
                'updated_at': datetime.now(timezone.utc),
                # Don't update content/embedding - it's identical
            }
        ).returning(
            SemanticMemory,
            literal_column("(xmax = 0)").label("inserted")
        )
    
    result = await db.execute(stmt)
    row = result.fetchone()
    memory = row[0]
    was_inserted = row[1]
    
    await db.refresh(memory)
    
    # Determine action
    if data.external_id:
        action = 'created' if was_inserted else 'updated'
    else:
        action = 'created' if was_inserted else 'duplicate_skipped'
    
    return memory, action
```

### Service Layer (memory_service/services/semantic_memory_service.py)

```python
async def ingest(
    self,
    db: AsyncSession,
    tenant_id: UUID,
    data: SemanticMemoryCreate,
) -> SemanticMemoryResponse:
    """
    Ingest semantic memory with smart upsert logic.
    
    Transaction boundary: Commits after successful operation.
    """
    memory, action = await crud_upsert(db, tenant_id, data)
    await db.commit()
    
    response = self._to_response(memory)
    response.action = action  # Include action in response
    return response
```

### REST API (memory_service/api/v1/semantic.py)

```python
@router.post("", response_model=SemanticMemoryResponse, status_code=201)
async def ingest_semantic_memory(
    data: SemanticMemoryCreate,
    context: TenantContext = Depends(get_tenant_context),
):
    """
    Store or update semantic memory (smart upsert).
    
    Behavior:
    - If `external_id` provided: Updates existing record with that ID
    - If no `external_id`: Creates new record (auto-deduplicates by content hash)
    
    Example with versioning:
    ```json
    {
        "external_id": "doc:api-guide",
        "content": "Updated documentation...",
        "metadata": {"version": "2.0"}
    }
    ```
    
    Example without versioning (auto-dedupe):
    ```json
    {
        "content": "Python is a programming language",
        "metadata": {"category": "programming"}
    }
    ```
    """
    return await semantic_memory_service.ingest(
        context.db,
        context.tenant_id,
        data
    )
```

### SDK (soorma/context.py)

```python
async def store_knowledge(
    self,
    content: str,
    user_id: str,
    external_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """
    Store or update knowledge in Semantic Memory (smart upsert).
    
    Args:
        content: Knowledge content to store
        user_id: User identifier (required in single-tenant mode)
        external_id: Optional ID for document versioning. If provided,
                     updates existing record with same external_id.
        metadata: Optional metadata (source, version, tags, etc.)
        
    Returns:
        Memory ID if successful, None otherwise
        
    Examples:
        # Document versioning (updates if exists)
        await context.memory.store_knowledge(
            content="API v2 docs...",
            user_id="system",
            external_id="doc:api-guide",
            metadata={"version": "2.0"}
        )
        
        # Auto-deduplication (skips if duplicate)
        await context.memory.store_knowledge(
            content="Python fact...",
            user_id="knowledge-base",
            metadata={"category": "programming"}
        )
    """
    if self._use_local:
        logger.debug("store_knowledge (local): semantic memory not available")
        return None
    
    client = await self._ensure_client()
    try:
        result = await client.store_knowledge(
            content, 
            user_id=user_id, 
            external_id=external_id,
            metadata=metadata or {}
        )
        
        # Log action for debugging
        if hasattr(result, 'action'):
            logger.debug(f"store_knowledge: {result.action} (id={result.id})")
        
        return str(result.id)
    except Exception as e:
        logger.debug(f"store_knowledge failed: {e}")
        self._use_local = True
        return None
```

---

## Decision Matrix

| Scenario | external_id | content_hash | Behavior |
|----------|-------------|--------------|----------|
| **Doc v2 replaces v1** | `doc:123` | different | Update by external_id, regenerate embedding |
| **Re-run same script** | None | **same** | Duplicate rejected by DB, update timestamp only |
| **Similar content** | None | different | Both stored (legitimately different) |
| **Update doc metadata** | `doc:123` | **same** | Update by external_id, keep embedding |
| **Two apps, same content** | different IDs | same hash | **CONFLICT** - Need to choose constraint priority |

### Constraint Priority

PostgreSQL will check constraints in order. We need to decide:

**Option A: external_id takes precedence**
```python
# Check external_id first if provided, else check content_hash
# This means: same content, different external_id = 2 records (app versioning wins)
```

**Option B: content_hash always checked**
```python
# Always enforce content uniqueness, external_id secondary
# This means: same content fails even with different external_id (deduplication wins)
```

**Decision: Option A (external_id precedence)**
- Applications explicitly requesting versioning should be honored
- If app wants v1 and v2 to coexist temporarily, they can use different external_ids
- Content deduplication only applies when no external_id provided (auto-pilot mode)

---

## Implementation Details

### Content Hash Calculation

```python
import hashlib

def calculate_content_hash(content: str) -> str:
    """Calculate SHA256 hash of content for deduplication."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()
```

**Considerations:**
- Normalize whitespace? **No** - treat exact content as-is
- Case-sensitive? **Yes** - "Python" ≠ "python"
- Unicode normalization? **Yes** - use UTF-8 encoding

### Embedding Regeneration

**When to regenerate:**
```python
if action == 'updated' and old_content_hash != new_content_hash:
    # Content changed, regenerate embedding
    new_embedding = await embedding_service.generate_embedding(content)
else:
    # Content unchanged, reuse existing embedding (performance)
    pass
```

**Cost consideration:**
- Embedding generation is expensive (OpenAI API call)
- Only regenerate when content actually changes
- For metadata-only updates, keep existing embedding

### Search Behavior

Search remains unchanged - uses vector similarity:
```python
# Search finds by semantic similarity, not external_id
results = await context.memory.search_knowledge(
    query="What is Docker?",
    limit=5
)
# Returns all matching records, regardless of external_id
```

---

## Use Cases & Examples

### Use Case 1: Document Versioning (Research Advisor)

```python
# Researcher stores initial findings
await context.memory.store_knowledge(
    content="NATS is a messaging system...",
    user_id="system",
    external_id="research:nats",
    metadata={
        "source_url": "https://nats.io/docs",
        "timestamp": "2026-01-15T10:00:00Z"
    }
)

# Later: Updated research replaces old version
await context.memory.store_knowledge(
    content="NATS is a cloud-native messaging system with JetStream...",
    user_id="system",
    external_id="research:nats",  # Same ID
    metadata={
        "source_url": "https://nats.io/docs/jetstream",
        "timestamp": "2026-01-20T14:30:00Z",
        "updated": True
    }
)
# Result: Only latest version in database
```

### Use Case 2: Knowledge Base Population (Auto-Dedupe)

```python
# store_knowledge.py script
facts = [
    "Python was created by Guido van Rossum...",
    "Python emphasizes code readability...",
    # ... 20 more facts
]

for fact in facts:
    await context.memory.store_knowledge(
        content=fact,
        user_id="knowledge-base",
        metadata={"category": "programming"}
    )

# Run script again -> No duplicates created
# Database constraints prevent re-insertion of identical content
```

### Use Case 3: Content Chunking with Versioning

```python
# Store document chunks with parent versioning
for i, chunk in enumerate(document_chunks):
    await context.memory.store_knowledge(
        content=chunk,
        user_id="system",
        external_id=f"doc:{doc_id}:chunk:{i}",
        metadata={
            "doc_id": doc_id,
            "chunk_index": i,
            "doc_version": "2.0"
        }
    )

# Update entire document: chunks get replaced automatically
```

### Use Case 4: Multiple Sources, Same Fact

```python
# Source 1: Wikipedia
await context.memory.store_knowledge(
    content="Docker is a container platform...",
    user_id="system",
    metadata={"source": "wikipedia"}
)

# Source 2: Documentation (same content)
await context.memory.store_knowledge(
    content="Docker is a container platform...",
    user_id="system",
    metadata={"source": "docker.com"}
)
# Result: Only one record (content_hash deduplication)
# Latest metadata wins
```

---

## Performance Considerations

### Database Operations

| Operation | Index Used | Performance |
|-----------|------------|-------------|
| Insert (new) | None | O(1) |
| Upsert by external_id | `idx_semantic_external_id` | O(log n) |
| Upsert by content_hash | `idx_semantic_content_hash` | O(log n) |
| Vector search | `semantic_embedding_idx` (HNSW) | O(log n) |

### Embedding Generation

- **Cost**: $0.0001 per 1K tokens (OpenAI text-embedding-3-small)
- **Latency**: ~100-500ms per request
- **Optimization**: Only regenerate when content changes

```python
# Pseudocode for optimization
if external_id and existing_record:
    if existing_record.content_hash == new_content_hash:
        # Content unchanged, skip embedding generation
        keep_existing_embedding = True
    else:
        # Content changed, regenerate
        new_embedding = await generate_embedding(content)
```

### Memory Usage

- Content hash: 64 bytes (SHA256 hex)
- External ID: Up to 255 bytes
- Total overhead: ~320 bytes per record
- Negligible compared to embedding size (1536 floats = 6KB)

---

## Trade-offs & Limitations

### Pros

✅ **True document versioning** - Applications control lifecycle  
✅ **Zero-config deduplication** - Protection by default  
✅ **Database-level enforcement** - No application logic needed  
✅ **Fast lookups** - Hash/ID indexes faster than vector search  
✅ **Backward compatible** - external_id is optional  
✅ **Clear semantics** - Action feedback tells app what happened  

### Cons

⚠️ **Schema complexity** - Two unique constraints to manage  
⚠️ **Content sensitivity** - Minor whitespace changes create new records  
⚠️ **Partial index needed** - external_id nullable requires WHERE clause  
⚠️ **Embedding cost** - Regeneration on every content update  
⚠️ **No partial updates** - Can't update metadata without content  

### Limitations

**Content hash deduplication only catches exact matches:**
```python
# Different hashes = both stored
"Python is a programming language."
"Python is a programming language"  # Missing period
```

**Workaround:** Applications can normalize content before storing:
```python
content = content.strip().lower()  # Normalize
await store_knowledge(content=content, ...)
```

**No delete API yet:**
- Records can be replaced (via external_id) but not deleted
- Future: Add `DELETE /v1/memory/semantic/{id}` endpoint

---

## Testing Strategy

### Unit Tests

```python
@pytest.mark.asyncio
async def test_upsert_with_external_id_creates_new():
    """Test upsert creates record when external_id doesn't exist."""
    memory, action = await upsert_semantic_memory(
        db, tenant_id,
        SemanticMemoryCreate(
            external_id="doc:test",
            content="Test content",
            metadata={}
        )
    )
    assert action == "created"
    assert memory.external_id == "doc:test"

@pytest.mark.asyncio
async def test_upsert_with_external_id_updates_existing():
    """Test upsert updates record when external_id exists."""
    # Create initial
    await upsert_semantic_memory(...)
    
    # Update
    memory, action = await upsert_semantic_memory(
        db, tenant_id,
        SemanticMemoryCreate(
            external_id="doc:test",
            content="Updated content",
            metadata={"version": "2"}
        )
    )
    assert action == "updated"
    assert memory.content == "Updated content"

@pytest.mark.asyncio
async def test_upsert_without_external_id_deduplicates():
    """Test content hash deduplication."""
    # First insert
    memory1, action1 = await upsert_semantic_memory(
        db, tenant_id,
        SemanticMemoryCreate(content="Test fact", metadata={})
    )
    assert action1 == "created"
    
    # Duplicate insert
    memory2, action2 = await upsert_semantic_memory(
        db, tenant_id,
        SemanticMemoryCreate(content="Test fact", metadata={})
    )
    assert action2 == "duplicate_skipped"
    assert memory1.id == memory2.id  # Same record
```

### Integration Tests

```python
@pytest.mark.integration
async def test_store_knowledge_versioning(context):
    """Test document versioning through SDK."""
    # V1
    id1 = await context.memory.store_knowledge(
        content="Version 1",
        user_id="test",
        external_id="doc:test"
    )
    
    # V2 (replaces V1)
    id2 = await context.memory.store_knowledge(
        content="Version 2",
        user_id="test",
        external_id="doc:test"
    )
    
    assert id1 == id2  # Same record ID
    
    # Search returns only V2
    results = await context.memory.search_knowledge(
        query="version",
        user_id="test"
    )
    assert len(results) == 1
    assert results[0].content == "Version 2"
```

---

## Migration Path (Pre-Launch)

Since we're pre-launch, we can use a **breaking change** approach:

### Step 1: Schema Migration
```bash
cd services/memory
alembic revision --autogenerate -m "Add semantic memory upsert support"
alembic upgrade head
```

### Step 2: Update DTOs
```bash
# Edit libs/soorma-common/src/soorma_common/models.py
# Add external_id field to SemanticMemoryCreate
```

### Step 3: Update CRUD Layer
```bash
# Replace create_semantic_memory with upsert_semantic_memory
# Update all callers
```

### Step 4: Update SDK
```bash
# Add external_id parameter to store_knowledge()
```

### Step 5: Update Examples
```bash
# Update store_knowledge.py to remove manual deduplication check
# Add external_id to research-advisor if needed
```

### No Data Migration Needed
- New columns are nullable initially
- Content hash calculated automatically via SQL expression
- Existing records continue working (external_id remains NULL)

---

## Open Questions

1. **Partial updates?**
   - Should we support updating only metadata without re-generating embedding?
   - **Decision:** Not in MVP, add later if needed

2. **Delete API?**
   - Should we add DELETE endpoint for cleanup?
   - **Decision:** Add in Phase 2 (not blocking)

3. **Batch upsert?**
   - Should we support bulk upsert operations?
   - **Decision:** Nice-to-have, not critical for MVP

4. **External ID format?**
   - Should we enforce a specific format (e.g., `type:id:version`)?
   - **Decision:** Free-form string, applications decide

5. **Conflict resolution for content_hash vs external_id?**
   - What if same content has multiple external_ids?
   - **Decision:** Allow it - external_id takes precedence

---

## References

- [Working Memory Upsert Implementation](./src/memory_service/crud/working.py) - Reference for ON CONFLICT logic
- [PostgreSQL INSERT ... ON CONFLICT](https://www.postgresql.org/docs/current/sql-insert.html#SQL-ON-CONFLICT) - Official docs
- [SQLAlchemy insert().on_conflict_do_update()](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#postgresql-insert-on-conflict) - API reference
- [CoALA Framework](https://arxiv.org/abs/2309.02427) - Semantic memory in cognitive architectures

---

## Changelog

| Date | Change | Author |
|------|--------|--------|
| 2026-01-22 | Initial design document | System Architecture |

---

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| **3-level approach** | Covers all use cases: versioning + deduplication + smart API |
| **external_id optional** | Backward compatible, applications opt-in to versioning |
| **content_hash required** | Always enforce deduplication, even without external_id |
| **Smart upsert API** | Single method handles both modes, reduces API surface |
| **external_id precedence** | Respect application intent for versioning |
| **No migration** | Pre-launch allows breaking changes |
| **Action feedback** | API tells caller what happened (created/updated/skipped) |

---

**Status:** ✅ Design Approved - Ready for Implementation
