"""Add upsert and privacy support to semantic_memory

Revision ID: 002_semantic_memory_upsert_privacy
Revises: 001_initial_schema
Create Date: 2026-01-27

Changes:
- Add external_id column for application-controlled versioning (RF-ARCH-012)
- Add content_hash column for automatic deduplication (RF-ARCH-012)
- Add user_id column for user-scoped privacy (RF-ARCH-014)
- Add is_public flag for optional public knowledge (RF-ARCH-014)
- Add unique constraints for upsert behavior
- Update RLS policies for user isolation

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002_semantic_memory_upsert_privacy'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add upsert and privacy columns to semantic_memory."""
    
    # Add new columns for upsert support (RF-ARCH-012)
    op.add_column('semantic_memory', sa.Column('external_id', sa.String(255), nullable=True))
    op.add_column('semantic_memory', sa.Column('content_hash', sa.String(64), nullable=True))
    
    # Add new columns for privacy support (RF-ARCH-014)
    # user_id is required, but we need to backfill first, so initially nullable
    op.add_column('semantic_memory', sa.Column('user_id', sa.String(255), nullable=True))
    op.add_column('semantic_memory', sa.Column('is_public', sa.Boolean(), nullable=False, server_default='false'))
    
    # Backfill user_id with default user for existing records
    # In production, this would need a more sophisticated migration strategy
    op.execute("""
        UPDATE semantic_memory 
        SET user_id = '00000000-0000-0000-0000-000000000000'
        WHERE user_id IS NULL
    """)
    
    # Now make user_id NOT NULL
    op.alter_column('semantic_memory', 'user_id', nullable=False)
    
    # Generate content_hash for existing records (SHA-256 of content)
    # PostgreSQL's encode(digest(...), 'hex') generates SHA-256 hash
    op.execute("""
        UPDATE semantic_memory 
        SET content_hash = encode(digest(content, 'sha256'), 'hex')
        WHERE content_hash IS NULL
    """)
    
    # Now make content_hash NOT NULL
    op.alter_column('semantic_memory', 'content_hash', nullable=False)
    
    # Drop the old tenant_isolation_policy before creating new ones
    op.execute('DROP POLICY IF EXISTS tenant_isolation_policy ON semantic_memory')
    
    # Create conditional unique indexes for upsert behavior
    # 
    # For external_id:
    # - Private knowledge: unique per (tenant_id, user_id, external_id)
    # - Public knowledge: unique per (tenant_id, external_id)
    op.execute("""
        CREATE UNIQUE INDEX semantic_memory_user_external_id_private_idx
        ON semantic_memory (tenant_id, user_id, external_id)
        WHERE external_id IS NOT NULL AND is_public = FALSE
    """)
    
    op.execute("""
        CREATE UNIQUE INDEX semantic_memory_tenant_external_id_public_idx
        ON semantic_memory (tenant_id, external_id)
        WHERE external_id IS NOT NULL AND is_public = TRUE
    """)
    
    # For content_hash:
    # - Private knowledge: unique per (tenant_id, user_id, content_hash)
    # - Public knowledge: unique per (tenant_id, content_hash)
    op.execute("""
        CREATE UNIQUE INDEX semantic_memory_user_content_hash_private_idx
        ON semantic_memory (tenant_id, user_id, content_hash)
        WHERE is_public = FALSE
    """)
    
    op.execute("""
        CREATE UNIQUE INDEX semantic_memory_tenant_content_hash_public_idx
        ON semantic_memory (tenant_id, content_hash)
        WHERE is_public = TRUE
    """)
    
    # Create new RLS policies for user isolation (RF-ARCH-014)
    # Read: Users can read their own private knowledge OR public knowledge in tenant
    op.execute("""
        CREATE POLICY semantic_memory_read_policy ON semantic_memory
        FOR SELECT
        USING (
            (tenant_id = current_setting('app.current_tenant')::UUID)
            AND (
                (user_id = current_setting('app.current_user_id', true))
                OR (is_public = TRUE)
            )
        )
    """)
    
    # Write: Users can only write their own knowledge
    op.execute("""
        CREATE POLICY semantic_memory_write_policy ON semantic_memory
        FOR INSERT
        WITH CHECK (
            (tenant_id = current_setting('app.current_tenant')::UUID)
            AND (user_id = current_setting('app.current_user_id', true))
        )
    """)
    
    # Update: Users can only update their own knowledge
    op.execute("""
        CREATE POLICY semantic_memory_update_policy ON semantic_memory
        FOR UPDATE
        USING (
            (tenant_id = current_setting('app.current_tenant')::UUID)
            AND (user_id = current_setting('app.current_user_id', true))
        )
    """)


def downgrade() -> None:
    """Remove upsert and privacy columns from semantic_memory."""
    
    # Drop RLS policies
    op.execute('DROP POLICY IF EXISTS semantic_memory_update_policy ON semantic_memory')
    op.execute('DROP POLICY IF EXISTS semantic_memory_write_policy ON semantic_memory')
    op.execute('DROP POLICY IF EXISTS semantic_memory_read_policy ON semantic_memory')
    
    # Drop indexes
    op.execute('DROP INDEX IF EXISTS semantic_memory_tenant_content_hash_public_idx')
    op.execute('DROP INDEX IF EXISTS semantic_memory_user_content_hash_private_idx')
    op.execute('DROP INDEX IF EXISTS semantic_memory_tenant_external_id_public_idx')
    op.execute('DROP INDEX IF EXISTS semantic_memory_user_external_id_private_idx')
    
    # Drop columns
    op.drop_column('semantic_memory', 'is_public')
    op.drop_column('semantic_memory', 'user_id')
    op.drop_column('semantic_memory', 'content_hash')
    op.drop_column('semantic_memory', 'external_id')
    
    # Restore original tenant isolation policy
    op.execute("""
        CREATE POLICY tenant_isolation_policy ON semantic_memory
        USING (tenant_id = current_setting('app.current_tenant')::UUID)
    """)

