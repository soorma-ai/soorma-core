"""
WorkflowState helper class for managing plan-scoped state.

Provides a simplified interface for working memory management,
reducing boilerplate in agent code.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from soorma.context import MemoryClient


class WorkflowState:
    """
    Helper class for managing plan-scoped workflow state.
    
    Simplifies working memory operations by providing a clean interface
    for common state management patterns.
    
    Example:
        ```python
        # Get tenant_id and user_id from event context
        tenant_id = event.get("tenantId")
        user_id = event.get("userId")
        
        state = WorkflowState(context.memory, plan_id, tenant_id, user_id)
        
        # Record actions
        await state.record_action("research.started")
        
        # Store/retrieve data
        await state.set("research_data", {"findings": [...]})
        data = await state.get("research_data")
        
        # Get action history
        history = await state.get_action_history()
        ```
    """
    
    def __init__(self, memory_client: "MemoryClient", plan_id: str, tenant_id: str, user_id: str):
        """
        Initialize workflow state.
        
        Args:
            memory_client: MemoryClient instance from PlatformContext
            plan_id: Plan identifier
            tenant_id: Tenant ID from event context
            user_id: User ID from event context
        """
        self.memory = memory_client
        self.plan_id = plan_id
        self.tenant_id = tenant_id
        self.user_id = user_id
        self._action_history_key = "_action_history"
    
    async def record_action(self, event_name: str) -> None:
        """
        Record an action/event in the plan's history.
        
        Args:
            event_name: Name of the event/action to record
        """
        try:
            history = await self.memory.retrieve(
                self._action_history_key,
                plan_id=self.plan_id,
                tenant_id=self.tenant_id,
                user_id=self.user_id,
            )
        except Exception:
            # Key doesn't exist yet
            history = None
        
        if history is None:
            history = {"actions": []}
        
        if "actions" not in history:
            history["actions"] = []
        
        history["actions"].append(event_name)
        
        await self.memory.store(
            self._action_history_key,
            history,
            plan_id=self.plan_id,
            tenant_id=self.tenant_id,
            user_id=self.user_id,
        )
    
    async def get_action_history(self) -> List[str]:
        """
        Get the list of recorded actions for this plan.
        
        Returns:
            List of action names in chronological order
        """
        try:
            history = await self.memory.retrieve(
                self._action_history_key,
                plan_id=self.plan_id,
                tenant_id=self.tenant_id,
                user_id=self.user_id,
            )
            if history is None:
                return []
            return history.get("actions", [])
        except Exception:
            return []
    
    async def set(self, key: str, value: Any) -> None:
        """
        Store a value in plan-scoped state.
        
        Args:
            key: State key
            value: Value to store (must be JSON-serializable)
        """
        await self.memory.store(
            key,
            value,
            plan_id=self.plan_id,
            tenant_id=self.tenant_id,
            user_id=self.user_id,
        )
    
    async def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieve a value from plan-scoped state.
        
        Args:
            key: State key
            default: Default value if key not found
            
        Returns:
            Stored value or default
        """
        try:
            value = await self.memory.retrieve(
                key, 
                plan_id=self.plan_id,
                tenant_id=self.tenant_id,
                user_id=self.user_id,
            )
            return value if value is not None else default
        except Exception:
            return default
    
    async def has(self, key: str) -> bool:
        """
        Check if a key exists in plan-scoped state.
        
        Args:
            key: State key
            
        Returns:
            True if key exists, False otherwise
        """
        try:
            value = await self.memory.retrieve(
                key,
                plan_id=self.plan_id,
                tenant_id=self.tenant_id,
                user_id=self.user_id,
            )
            return value is not None
        except Exception:
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Delete a key from plan-scoped state.
        
        Permanently removes the key from working memory.
        
        Args:
            key: State key
            
        Returns:
            True if deleted, False if key didn't exist
            
        Example:
            ```python
            # Delete sensitive data after processing
            if await state.delete("credit_card"):
                print("Sensitive data deleted")
            ```
        """
        result = await self.memory.delete_key(
            plan_id=self.plan_id,
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            key=key,
        )
        return result.deleted
    
    async def cleanup(self) -> int:
        """
        Delete all state for this plan.
        
        Removes all working memory keys for the plan. Useful for cleanup
        after plan completion or when reclaiming resources.
        
        Returns:
            Number of keys deleted
            
        Example:
            ```python
            # Clean up after plan completes
            count = await state.cleanup()
            print(f"Cleaned up {count} state entries")
            
            # Or explicitly handle sensitive data
            await state.cleanup()  # Clear everything including temp state
            ```
        """
        result = await self.memory.cleanup_plan(
            plan_id=self.plan_id,
            tenant_id=self.tenant_id,
            user_id=self.user_id,
        )
        return result.count_deleted
    
    async def increment(self, key: str, delta: int = 1) -> int:
        """
        Increment a numeric counter.
        
        Args:
            key: State key
            delta: Amount to increment by (default: 1)
            
        Returns:
            New counter value
        """
        current = await self.get(key, 0)
        if not isinstance(current, (int, float)):
            current = 0
        
        new_value = current + delta
        await self.set(key, new_value)
        return new_value
    
    async def append(self, key: str, item: Any) -> List[Any]:
        """
        Append an item to a list.
        
        Args:
            key: State key
            item: Item to append
            
        Returns:
            Updated list
        """
        current = await self.get(key, [])
        if not isinstance(current, list):
            current = []
        
        current.append(item)
        await self.set(key, current)
        return current
    
    async def extend(self, key: str, items: List[Any]) -> List[Any]:
        """
        Extend a list with multiple items.
        
        Args:
            key: State key
            items: Items to append
            
        Returns:
            Updated list
        """
        current = await self.get(key, [])
        if not isinstance(current, list):
            current = []
        
        current.extend(items)
        await self.set(key, current)
        return current
    
    async def update_dict(self, key: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a dictionary with new key-value pairs.
        
        Args:
            key: State key
            updates: Dictionary of updates
            
        Returns:
            Updated dictionary
        """
        current = await self.get(key, {})
        if not isinstance(current, dict):
            current = {}
        
        current.update(updates)
        await self.set(key, current)
        return current
