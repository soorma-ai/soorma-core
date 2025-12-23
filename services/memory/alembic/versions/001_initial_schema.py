"""Initial migration - Create memory tables with pgvector support

Revision ID: 001_initial_schema
Revises: 
Create Date: 2025-12-23

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    # Create tenants table
    op.create_table(
        'tenants',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Insert default tenant for local development
    op.execute("""
        INSERT INTO tenants (id, name) 
        VALUES ('00000000-0000-0000-0000-000000000000', 'Default Tenant')
        ON CONFLICT DO NOTHING
    """)

    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('username', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Enable RLS on users
    op.execute('ALTER TABLE users ENABLE ROW LEVEL SECURITY')

    # Insert default user for local development
    op.execute("""
        INSERT INTO users (id, tenant_id, username) 
        VALUES ('00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000000', 'default-user')
        ON CONFLICT DO NOTHING
    """)

    # Create semantic_memory table
    op.create_table(
        'semantic_memory',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('embedding', postgresql.ARRAY(sa.Float()), nullable=True),  # Will be converted to vector
        sa.Column('memory_metadata', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Alter embedding column to use vector type
    op.execute('ALTER TABLE semantic_memory ALTER COLUMN embedding TYPE vector(1536) USING embedding::vector(1536)')

    # Create HNSW index for semantic_memory
    op.execute('CREATE INDEX semantic_embedding_idx ON semantic_memory USING hnsw (embedding vector_cosine_ops)')

    # Enable RLS on semantic_memory
    op.execute('ALTER TABLE semantic_memory ENABLE ROW LEVEL SECURITY')
    op.execute("""
        CREATE POLICY tenant_isolation_policy ON semantic_memory
        USING (tenant_id = current_setting('app.current_tenant')::UUID)
    """)

    # Create episodic_memory table
    op.create_table(
        'episodic_memory',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_id', sa.Text(), nullable=False),
        sa.Column('role', sa.Text(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('embedding', postgresql.ARRAY(sa.Float()), nullable=True),
        sa.Column('memory_metadata', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("role IN ('user', 'assistant', 'system', 'tool')", name='role_check'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Alter embedding column to use vector type
    op.execute('ALTER TABLE episodic_memory ALTER COLUMN embedding TYPE vector(1536) USING embedding::vector(1536)')

    # Create indexes for episodic_memory
    op.execute('CREATE INDEX episodic_embedding_idx ON episodic_memory USING hnsw (embedding vector_cosine_ops)')
    op.create_index('episodic_time_idx', 'episodic_memory', ['user_id', 'agent_id', sa.text('created_at DESC')])

    # Enable RLS on episodic_memory
    op.execute('ALTER TABLE episodic_memory ENABLE ROW LEVEL SECURITY')
    op.execute("""
        CREATE POLICY user_agent_isolation ON episodic_memory
        USING (
            tenant_id = current_setting('app.current_tenant')::UUID 
            AND user_id = current_setting('app.current_user')::UUID
        )
    """)

    # Create procedural_memory table
    op.create_table(
        'procedural_memory',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_id', sa.Text(), nullable=False),
        sa.Column('trigger_condition', sa.Text(), nullable=True),
        sa.Column('embedding', postgresql.ARRAY(sa.Float()), nullable=True),
        sa.Column('procedure_type', sa.Text(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("procedure_type IN ('system_prompt', 'few_shot_example')", name='procedure_type_check'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Alter embedding column to use vector type
    op.execute('ALTER TABLE procedural_memory ALTER COLUMN embedding TYPE vector(1536) USING embedding::vector(1536)')

    # Create HNSW index for procedural_memory
    op.execute('CREATE INDEX procedural_embedding_idx ON procedural_memory USING hnsw (embedding vector_cosine_ops)')

    # Enable RLS on procedural_memory
    op.execute('ALTER TABLE procedural_memory ENABLE ROW LEVEL SECURITY')
    op.execute("""
        CREATE POLICY procedural_isolation ON procedural_memory
        USING (
            tenant_id = current_setting('app.current_tenant')::UUID 
            AND user_id = current_setting('app.current_user')::UUID
        )
    """)

    # Create working_memory table
    op.create_table(
        'working_memory',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('plan_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('key', sa.Text(), nullable=False),
        sa.Column('value', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('plan_id', 'key', name='plan_key_unique')
    )

    # Enable RLS on working_memory
    op.execute('ALTER TABLE working_memory ENABLE ROW LEVEL SECURITY')
    op.execute("""
        CREATE POLICY plan_isolation ON working_memory
        USING (tenant_id = current_setting('app.current_tenant')::UUID)
    """)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('working_memory')
    op.drop_table('procedural_memory')
    op.drop_table('episodic_memory')
    op.drop_table('semantic_memory')
    op.drop_table('users')
    op.drop_table('tenants')

    # Drop extensions
    op.execute('DROP EXTENSION IF EXISTS vector')
    op.execute('DROP EXTENSION IF EXISTS "uuid-ossp"')
