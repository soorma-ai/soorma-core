"""Configuration settings for Tracker Service."""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    """Application settings."""

    # Application
    is_prod: bool = os.environ.get("IS_PROD", "false").lower() == "true"
    is_local_testing: bool = os.environ.get("IS_LOCAL_TESTING", "true").lower() == "true"
    service_name: str = "tracker-service"

    # Database
    database_url: str = os.environ.get(
        "DATABASE_URL", "postgresql+asyncpg://soorma:soorma@localhost:5432/tracker"
    )
    sync_database_url: Optional[str] = os.environ.get("SYNC_DATABASE_URL")

    # Event Service
    event_service_url: str = os.environ.get("EVENT_SERVICE_URL", "http://localhost:8082")

    # Tenancy
    default_tenant_id: str = os.environ.get(
        "DEFAULT_TENANT_ID", "00000000-0000-0000-0000-000000000000"
    )
    default_tenant_name: str = os.environ.get("DEFAULT_TENANT_NAME", "Default Tenant")
    default_user_id: str = os.environ.get(
        "DEFAULT_USER_ID", "00000000-0000-0000-0000-000000000001"
    )
    default_username: str = os.environ.get("DEFAULT_USERNAME", "default-user")

    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=False
    )

    @property
    def sync_db_url(self) -> str:
        """Get sync database URL for Alembic."""
        if self.sync_database_url:
            return self.sync_database_url
        # Convert async URL to sync URL
        return self.database_url.replace("+asyncpg", "+psycopg2")


# Global settings instance
settings = Settings()
