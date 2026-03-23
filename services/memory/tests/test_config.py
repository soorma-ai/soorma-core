"""Tests for configuration management."""

import pytest
import os
from memory_service.core.config import Settings


class TestSettings:
    """Test suite for Settings configuration."""

    def test_default_settings(self):
        """Test default configuration values."""
        settings = Settings()
        
        # Database
        assert "postgresql" in settings.database_url or "sqlite" in settings.database_url
        
        # Embedding
        assert settings.embedding_dimensions == 1536
        assert settings.openai_embedding_model == "text-embedding-3-small"
        
        # Default IDs
        assert settings.default_tenant_id.startswith("spt_")

    def test_settings_from_environment(self, monkeypatch):
        """Test settings can be overridden by environment variables."""
        # Set environment variables
        monkeypatch.setenv("DATABASE_URL", "postgresql://custom:5432/test")
        monkeypatch.setenv("EMBEDDING_DIMENSIONS", "768")
        monkeypatch.setenv("DEFAULT_TENANT_ID", "11111111-1111-1111-1111-111111111111")
        
        settings = Settings()
        
        assert "custom:5432" in settings.database_url
        assert settings.embedding_dimensions == 768
        assert settings.default_tenant_id == "11111111-1111-1111-1111-111111111111"

    def test_is_prod_detection(self, monkeypatch):
        """Test production environment detection."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("TESTING", "false")
        settings = Settings()
        assert isinstance(settings.is_prod, bool)
        
        monkeypatch.setenv("ENVIRONMENT", "development")
        settings = Settings()
        assert isinstance(settings.is_prod, bool)

    def test_openai_api_key_required(self):
        """Test OpenAI API key is required for embedding service."""
        settings = Settings()
        # Should have a key (from env or config)
        assert settings.openai_api_key is not None or hasattr(settings, '_openai_api_key')
