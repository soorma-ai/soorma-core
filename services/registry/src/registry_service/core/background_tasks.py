"""
Background tasks for periodic cleanup and maintenance operations.
"""
import asyncio
import logging
from typing import Optional

from .database import AsyncSessionLocal
from .config import settings

logger = logging.getLogger(__name__)


class BackgroundTaskManager:
    """Manages background tasks for the application."""
    
    def __init__(self):
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self):
        """Start all background tasks."""
        if self._running:
            logger.warning("Background tasks are already running")
            return
        
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_expired_agents_loop())
        logger.info("Background tasks started")
    
    async def stop(self):
        """Stop all background tasks."""
        if not self._running:
            return
        
        self._running = False
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Background tasks stopped")
    
    async def _cleanup_expired_agents_loop(self):
        """
        Periodic task to cleanup expired agent registrations.
        Runs every AGENT_CLEANUP_INTERVAL_SECONDS.
        """
        # Import here to avoid circular imports
        from ..services import AgentRegistryService
        
        logger.info(
            f"Starting agent cleanup task (interval: {settings.AGENT_CLEANUP_INTERVAL_SECONDS}s, "
            f"TTL: {settings.AGENT_TTL_SECONDS}s)"
        )
        
        while self._running:
            try:
                await asyncio.sleep(settings.AGENT_CLEANUP_INTERVAL_SECONDS)
                
                if not self._running:
                    break
                
                # Perform cleanup through the service layer
                async with AsyncSessionLocal() as db:
                    deleted_count = await AgentRegistryService.cleanup_expired_agents(
                        db,
                        settings.AGENT_TTL_SECONDS
                    )
                    # Note: commit is handled by the service method
                    
                    if deleted_count > 0:
                        logger.info(f"Cleaned up {deleted_count} expired agent(s)")
                    else:
                        logger.debug("No expired agents to cleanup")
                        
            except asyncio.CancelledError:
                logger.info("Agent cleanup task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in agent cleanup task: {e}", exc_info=True)
                # Continue running despite errors


# Global instance
background_task_manager = BackgroundTaskManager()
