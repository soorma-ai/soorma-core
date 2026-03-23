"""Core package initialization."""

from memory_service.core.config import settings
from memory_service.core.database import get_db

__all__ = ["settings", "get_db"]
