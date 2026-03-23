"""Configuration settings for Tracker Service."""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from soorma_common.tenancy import DEFAULT_PLATFORM_TENANT_ID


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

    # NATS — direct message bus subscription (replaces SDK Event Service HTTP/SSE)
    nats_url: str = os.environ.get("NATS_URL", "nats://localhost:4222")

    # Tenancy
    default_platform_tenant_id: str = os.environ.get(
        "DEFAULT_PLATFORM_TENANT_ID", DEFAULT_PLATFORM_TENANT_ID
    )
    default_service_tenant_id: str = os.environ.get(
        "DEFAULT_SERVICE_TENANT_ID", "st_default-tenant"
    )
    default_service_user_id: str = os.environ.get(
        "DEFAULT_SERVICE_USER_ID", "su_default-user"
    )
    default_tenant_name: str = os.environ.get("DEFAULT_TENANT_NAME", "Default Tenant")
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
