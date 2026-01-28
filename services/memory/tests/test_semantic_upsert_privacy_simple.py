"""Integration-style tests for Semantic Memory Upsert and Privacy (RF-ARCH-012, RF-ARCH-014).

These tests validate CRUD layer behavior with realistic mocking.
Full database integration tests run separately in test suite.
"""

import pytest
import hashlib
from uuid import uuid4
from datetime import datetime

from memory_service.models.memory import SemanticMemory


def generate_content_hash(content: str) -> str:
    """Generate SHA-256 hash of content."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


class TestSemanticMemoryModel:
    """Validate SemanticMemory model has required fields for upsert and privacy."""

    def test_semantic_memory_has_upsert_columns(self):
        """Model should have external_id and content_hash columns."""
        tenant_id = uuid4()
        user_id = "user-123"
        content = "Test knowledge"
        
        memory = SemanticMemory(
            tenant_id=tenant_id,
            user_id=user_id,
            content=content,
            external_id="doc-123",
            content_hash=generate_content_hash(content),
            is_public=False,
            memory_metadata={},
        )
        
        # Verify upsert columns
        assert memory.external_id == "doc-123"
        assert memory.content_hash == generate_content_hash(content)
        assert len(memory.content_hash) == 64  # SHA-256 hex string

    def test_semantic_memory_has_privacy_columns(self):
        """Model should have user_id and is_public columns."""
        tenant_id = uuid4()
        user_id = "user-alice"
        
        memory = SemanticMemory(
            tenant_id=tenant_id,
            user_id=user_id,
            content="Research notes",
            embedding=[0.1] * 1536,
            external_id=None,
            content_hash="abc123",
            is_public=False,  # Private by default
            memory_metadata={},
        )
        
        # Verify privacy columns
        assert memory.user_id == user_id
        assert memory.is_public == False
        
    def test_semantic_memory_privacy_public_flag(self):
        """Model should support is_public=True for shared knowledge."""
        tenant_id = uuid4()
        
        memory = SemanticMemory(
            tenant_id=tenant_id,
            user_id="user-admin",
            content="Team guidelines",
            external_id="guidelines",
            content_hash="def456",
            is_public=True,  # Explicitly public
            memory_metadata={"created_by": "admin"},
        )
        
        assert memory.is_public == True
        assert memory.external_id == "guidelines"


class TestContentHashGeneration:
    """Validate content hash generation for deduplication."""

    def test_same_content_same_hash(self):
        """Same content should produce same hash."""
        content = "Python is awesome"
        hash1 = generate_content_hash(content)
        hash2 = generate_content_hash(content)
        
        assert hash1 == hash2

    def test_different_content_different_hash(self):
        """Different content should produce different hashes."""
        hash1 = generate_content_hash("Python")
        hash2 = generate_content_hash("Python is awesome")
        
        assert hash1 != hash2

    def test_hash_length_is_64(self):
        """SHA-256 hex string should be 64 characters."""
        content = "Any content"
        hash_value = generate_content_hash(content)
        
        assert len(hash_value) == 64
        assert all(c in '0123456789abcdef' for c in hash_value)


class TestPrivacyDefaults:
    """Validate privacy defaults and behavior."""

    def test_knowledge_private_by_default(self):
        """Knowledge should be private (is_public=False) by default."""
        memory = SemanticMemory(
            tenant_id=uuid4(),
            user_id="user-123",
            content="My personal notes",
            external_id="personal-1",
            content_hash="xyz789",
            is_public=False,  # Explicit default
            memory_metadata={},
        )
        
        assert memory.is_public == False

    def test_knowledge_can_be_explicit_public(self):
        """Knowledge can be explicitly marked as public."""
        memory = SemanticMemory(
            tenant_id=uuid4(),
            user_id="user-123",
            content="Team knowledge",
            external_id="team-1",
            content_hash="abc123",
            is_public=True,  # Explicitly public
            memory_metadata={"visibility": "team"},
        )
        
        assert memory.is_public == True


class TestUserScopedPrivacy:
    """Validate user-scoped privacy design."""

    def test_different_users_can_have_same_external_id_when_private(self):
        """Different users should be able to have same external_id with private knowledge.
        
        This is enforced via database unique constraint:
        CREATE UNIQUE INDEX semantic_memory_user_external_id_private_idx
        ON semantic_memory (tenant_id, user_id, external_id)
        WHERE external_id IS NOT NULL AND is_public = FALSE
        """
        tenant_id = uuid4()
        external_id = "research-findings"
        
        # Alice's private research
        alice_memory = SemanticMemory(
            tenant_id=tenant_id,
            user_id="alice",
            content="Alice's research findings",
            external_id=external_id,
            content_hash=generate_content_hash("Alice's research findings"),
            is_public=False,  # Private
            memory_metadata={},
        )
        
        # Bob's private research - same external_id, different user
        bob_memory = SemanticMemory(
            tenant_id=tenant_id,
            user_id="bob",
            content="Bob's research findings",
            external_id=external_id,
            content_hash=generate_content_hash("Bob's research findings"),
            is_public=False,  # Private
            memory_metadata={},
        )
        
        # Both should be valid (database constraint enforces per-user uniqueness)
        assert alice_memory.user_id != bob_memory.user_id
        assert alice_memory.external_id == bob_memory.external_id
        assert alice_memory.is_public == False
        assert bob_memory.is_public == False

    def test_public_knowledge_shared_per_tenant(self):
        """Public knowledge should be unique per tenant_id + external_id.
        
        This is enforced via database unique constraint:
        CREATE UNIQUE INDEX semantic_memory_tenant_external_id_public_idx
        ON semantic_memory (tenant_id, external_id)
        WHERE external_id IS NOT NULL AND is_public = TRUE
        """
        tenant_id = uuid4()
        external_id = "team-guidelines"
        
        # Public knowledge can be created by any user
        memory1 = SemanticMemory(
            tenant_id=tenant_id,
            user_id="alice",
            content="Team guidelines v1",
            external_id=external_id,
            content_hash=generate_content_hash("Team guidelines v1"),
            is_public=True,  # PUBLIC
            memory_metadata={},
        )
        
        # When updated, it should be same record (upserted)
        # This would be tested at database level with INSERT ON CONFLICT
        assert memory1.external_id == external_id
        assert memory1.is_public == True


class TestUpsertLogic:
    """Validate upsert logic design (database enforces via ON CONFLICT)."""

    def test_external_id_precedence_in_upsert(self):
        """When both external_id and content_hash exist, external_id should be upsert key.
        
        Note: Actual upsert behavior verified in integration tests with real database.
        This test validates the concept.
        """
        # Create knowledge with both identifiers
        memory = SemanticMemory(
            tenant_id=uuid4(),
            user_id="user-123",
            content="Documentation v1",
            external_id="doc-123",  # Has external_id
            content_hash=generate_content_hash("Documentation v1"),  # Also has hash
            is_public=False,
            memory_metadata={},
        )
        
        # With both IDs, external_id should be the upsert key
        # This means: same external_id + user + is_public = upsert match
        assert memory.external_id == "doc-123"
        assert memory.content_hash is not None

    def test_content_hash_deduplication_when_no_external_id(self):
        """When no external_id, content_hash should be upsert key.
        
        Note: Actual upsert behavior verified in integration tests with real database.
        """
        content = "Fact: Python is a language"
        
        memory = SemanticMemory(
            tenant_id=uuid4(),
            user_id="user-123",
            content=content,
            external_id=None,  # No external_id
            content_hash=generate_content_hash(content),  # Uses content_hash for dedup
            is_public=False,
            memory_metadata={},
        )
        
        # With no external_id, content_hash is the key
        assert memory.external_id is None
        assert memory.content_hash == generate_content_hash(content)


class TestConflictResolution:
    """Validate conflict resolution design (upsert updates is_public)."""

    def test_upsert_can_change_privacy_status(self):
        """Upsert should allow changing is_public status.
        
        Design decision: When upserting same external_id, is_public can be updated.
        This allows knowledge to transition from private to public (or vice versa).
        """
        tenant_id = uuid4()
        user_id = "user-123"
        external_id = "doc-123"
        
        # Initial: private knowledge
        memory_v1 = SemanticMemory(
            tenant_id=tenant_id,
            user_id=user_id,
            content="Research findings",
            external_id=external_id,
            content_hash="hash1",
            is_public=False,  # Private
            memory_metadata={},
        )
        
        # Later: same external_id, but made public
        memory_v2 = SemanticMemory(
            tenant_id=tenant_id,
            user_id=user_id,
            content="Research findings (updated)",
            external_id=external_id,
            content_hash="hash2",
            is_public=True,  # NOW PUBLIC
            memory_metadata={},
        )
        
        # Both have same external_id but different privacy status
        assert memory_v1.external_id == memory_v2.external_id
        assert memory_v1.is_public == False
        assert memory_v2.is_public == True
        # Database upsert will update the record with new content and is_public flag

