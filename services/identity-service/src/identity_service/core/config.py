"""Configuration settings for Identity Service."""

import os

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    is_prod: bool = os.environ.get("IS_PROD", "false").lower() == "true"
    service_name: str = "identity-service"

    database_url: str = os.environ.get(
        "DATABASE_URL", "postgresql+asyncpg://soorma:soorma@localhost:5432/identity"
    )
    sync_database_url: str | None = os.environ.get("SYNC_DATABASE_URL")

    identity_admin_api_key: str = os.environ.get("IDENTITY_ADMIN_API_KEY", "dev-identity-admin")

    model_config = ConfigDict(env_file=".env", case_sensitive=False)

    @property
    def sync_db_url(self) -> str:
        """Get sync database URL for migrations."""
        if self.sync_database_url:
            return self.sync_database_url
        return self.database_url.replace("+asyncpg", "+psycopg2")


settings = Settings()
