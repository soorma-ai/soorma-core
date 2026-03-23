"""
Centralized application configuration management.
Loads settings from environment variables and .env files.
"""
import os
from typing import List
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


def get_version() -> str:
    """
    Get the service version from pyproject.toml.
    Falls back to environment variable SERVICE_VERSION if pyproject.toml is not found.
    This allows CI/CD to override the version dynamically.
    """
    # Check for environment variable first (allows CI/CD override)
    env_version = os.getenv("SERVICE_VERSION")
    if env_version:
        return env_version
    
    # Try to read from pyproject.toml
    try:
        import tomli
    except ImportError:
        # For Python 3.11+, use built-in tomllib
        try:
            import tomllib as tomli
        except ImportError:
            return "0.0.0"  # Fallback if no toml library available
    
    # Find pyproject.toml (go up from current file to project root)
    current_file = Path(__file__)
    project_root = current_file.parent.parent.parent.parent  # src/registry_service/core/config.py -> registry/
    pyproject_path = project_root / "pyproject.toml"
    
    try:
        with open(pyproject_path, "rb") as f:
            pyproject_data = tomli.load(f)
            return pyproject_data.get("project", {}).get("version", "0.0.0")
    except (FileNotFoundError, KeyError):
        return "0.0.0"  # Fallback version


class Settings(BaseSettings):
    """
    Defines the application's configuration settings.
    Pydantic automatically reads these from environment variables.
    For local development, create a .env file (see .env.example).
    
    IMPORTANT: Defaults are optimized for LOCAL DEVELOPMENT.
    Production deployments MUST set environment variables explicitly.
    """
    model_config = SettingsConfigDict(
        env_file='.env', 
        env_file_encoding='utf-8', 
        extra='ignore'
    )
    
    # --- Service Settings ---
    SERVICE_NAME: str = "registry-service"
    SERVICE_VERSION: str = get_version()  # Read from pyproject.toml or environment
    API_PREFIX: str = "/api"
    
    # --- Environment ---
    # In production, set IS_PROD=true to disable docs and enable security features
    IS_PROD: bool = False

    # --- Database Settings ---
    # In production, set DATABASE_URL to the PostgreSQL connection string.
    # For local testing, set DATABASE_URL to a SQLite URL (e.g. sqlite+aiosqlite:///./registry.db).
    DATABASE_URL: str = "postgresql+asyncpg://localhost/registry"
    # In production, set to specific allowed origins
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    # --- Agent Registry Settings ---
    # TTL for agent registration (5 minutes default)
    AGENT_TTL_SECONDS: int = 300
    # Cleanup interval for expired agents (1 minute default)
    AGENT_CLEANUP_INTERVAL_SECONDS: int = 60


# Global settings instance
settings = Settings()
