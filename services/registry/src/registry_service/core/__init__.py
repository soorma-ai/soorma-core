"""
Core configuration and infrastructure for registry service.
"""

from .config import settings, check_required_settings, Settings
from .database import (
    get_db,
    init_db,
    drop_db,
    engine,
    AsyncSessionLocal,
    create_db_url,
)
from .cache import (
    cache_agent,
    cache_event,
    invalidate_agent_cache,
    invalidate_event_cache,
    get_cache_stats,
)
from .background_tasks import background_task_manager

__all__ = [
    # Config
    "settings",
    "check_required_settings",
    "Settings",
    # Database
    "get_db",
    "init_db",
    "drop_db",
    "engine",
    "AsyncSessionLocal",
    "create_db_url",
    # Cache
    "cache_agent",
    "cache_event",
    "invalidate_agent_cache",
    "invalidate_event_cache",
    "get_cache_stats",
    # Background tasks
    "background_task_manager",
]
