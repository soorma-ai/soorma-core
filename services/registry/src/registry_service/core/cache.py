"""
In-memory caching utilities for registry service.

Uses TTLCache from cachetools for simple in-memory caching with time-based expiration.
Good for read-heavy operations on data that changes infrequently.

Note: This is per-instance caching. In multi-instance deployments without Redis,
each instance maintains its own cache, which may lead to temporary inconsistencies
(up to TTL duration) when data is modified.
"""
from functools import wraps
from typing import Callable, Optional
from cachetools import TTLCache
import hashlib
import json


# Global cache instances
# Separate caches for events and agents to allow different eviction policies
_event_cache = TTLCache(maxsize=1000, ttl=30)  # 30 second TTL, max 1000 events
_agent_cache = TTLCache(maxsize=1000, ttl=30)  # 30 second TTL, max 1000 agents


def _make_key(*args, **kwargs) -> str:
    """
    Create a cache key from function arguments.
    
    Args:
        *args: Positional arguments
        **kwargs: Keyword arguments
        
    Returns:
        String cache key
    """
    # Skip 'self' and 'db' arguments (first two)
    cache_args = args[2:] if len(args) > 2 else args
    key_data = {
        "args": [str(arg) for arg in cache_args],
        "kwargs": {k: str(v) for k, v in kwargs.items() if k != "db"}
    }
    key_str = json.dumps(key_data, sort_keys=True)
    return hashlib.md5(key_str.encode()).hexdigest()


def cache_event(func: Callable) -> Callable:
    """
    Decorator to cache event query results.
    
    Args:
        func: Async function to cache
        
    Returns:
        Wrapped function with caching
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Generate cache key
        key = f"{func.__name__}:{_make_key(*args, **kwargs)}"
        
        # Check cache
        if key in _event_cache:
            return _event_cache[key]
        
        # Call function
        result = await func(*args, **kwargs)
        
        # Cache result (only if not None)
        if result is not None:
            _event_cache[key] = result
        
        return result
    
    return wrapper


def cache_agent(func: Callable) -> Callable:
    """
    Decorator to cache agent query results.
    
    Args:
        func: Async function to cache
        
    Returns:
        Wrapped function with caching
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Generate cache key
        key = f"{func.__name__}:{_make_key(*args, **kwargs)}"
        
        # Check cache
        if key in _agent_cache:
            return _agent_cache[key]
        
        # Call function
        result = await func(*args, **kwargs)
        
        # Cache result (only if not None for single results, always cache lists)
        if result is not None or isinstance(result, list):
            _agent_cache[key] = result
        
        return result
    
    return wrapper


def invalidate_event_cache(event_name: Optional[str] = None) -> None:
    """
    Invalidate event cache entries.
    
    Args:
        event_name: If provided, invalidate only entries for this event.
                   If None, clear entire event cache.
    
    Note: Currently clears the entire cache when event_name is provided
    because cache keys are hashed and don't contain the event_name directly.
    This is acceptable given the short TTL (30s) and read-heavy workload.
    """
    # Since cache keys are hashed, we can't selectively invalidate by event_name
    # Clear entire cache to ensure consistency
    _event_cache.clear()


def invalidate_agent_cache(agent_id: Optional[str] = None) -> None:
    """
    Invalidate agent cache entries.
    
    Args:
        agent_id: If provided, invalidate only entries for this agent.
                 If None, clear entire agent cache.
    
    Note: Currently clears the entire cache when agent_id is provided
    because cache keys are hashed and don't contain the agent_id directly.
    This is acceptable given the short TTL (30s) and read-heavy workload.
    """
    # Since cache keys are hashed, we can't selectively invalidate by agent_id
    # Clear entire cache to ensure consistency
    _agent_cache.clear()


def get_cache_stats() -> dict:
    """
    Get cache statistics for monitoring.
    
    Returns:
        Dictionary with cache statistics
    """
    return {
        "event_cache": {
            "size": len(_event_cache),
            "maxsize": _event_cache.maxsize,
            "ttl": _event_cache.ttl,
            "currsize": _event_cache.currsize
        },
        "agent_cache": {
            "size": len(_agent_cache),
            "maxsize": _agent_cache.maxsize,
            "ttl": _agent_cache.ttl,
            "currsize": _agent_cache.currsize
        }
    }
