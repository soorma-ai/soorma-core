"""Configuration settings for Memory Service."""

import os
from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    """Application settings."""

    # Application
    is_prod: bool = os.environ.get("IS_PROD", "false").lower() == "true"
    service_name: str = "memory-service"

    # Database — PostgreSQL only (asyncpg for runtime, psycopg2 for Alembic)
    database_url: str = os.environ.get(
        "DATABASE_URL", "postgresql+asyncpg://soorma:soorma@localhost:5432/memory"
    )

    # OpenAI
    openai_api_key: str = os.environ.get("OPENAI_API_KEY", "")
    openai_embedding_model: str = os.environ.get(
        "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"
    )
    embedding_dimensions: int = int(os.environ.get("EMBEDDING_DIMENSIONS", "1536"))

    # Tenancy — three-column identity model
    # default_tenant_id is the spt_-prefixed platform tenant used for all pre-existing rows
    default_tenant_id: str = os.environ.get(
        "DEFAULT_TENANT_ID", "spt_00000000-0000-0000-0000-000000000000"
    )

    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=False
    )

    @property
    def sync_db_url(self) -> str:
        """Get sync database URL for Alembic."""
        # Convert async URL to sync URL
        return self.database_url.replace("+asyncpg", "+psycopg2")


# Global settings instance
settings = Settings()
