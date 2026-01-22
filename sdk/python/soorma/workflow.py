"""
WorkflowState helper class for managing plan-scoped state.

Provides a simplified interface for working memory management,
reducing boilerplate in agent code.
"""

from typing import Any, Dict, List, Optional
from soorma.memory.client import MemoryClient


class WorkflowState:
    """
    Helper class for managing plan-scoped workflow state.
    
    Simplifies working memory operations by providing a clean interface
    for common state management patterns.
    
    Example:
        ```python
        state = WorkflowState(context, plan_id)
        
        # Record actions
        await state.record_action("research.started")
        
        # Store/retrieve data
        await state.set("research_data", {"findings": [...]})
        data = await state.get("research_data")
        
        # Get action history
        history = await state.get_action_history()
        ```
    """
    
    def __init__(self, memory_client: MemoryClient, plan_id: str):
        """
        Initialize workflow state.
        
        Args:
            memory_client: MemoryClient instance from PlatformContext
            plan_id: Plan identifier
        """
        self.memory = memory_client
        self.plan_id = plan_id
        self._action_history_key = "_action_history"
    
    async def record_action(self, event_name: str) -> None:
        """
        Record an action/event in the plan's history.
        
        Args:
            event_name: Name of the event/action to record
        """
        try:
            history_response = await self.memory.get_plan_state(
                self.plan_id,
                self._action_history_key,
            )
            history = history_response.value
        except Exception:
            # Key doesn't exist yet
            history = {"actions": []}
        
        if "actions" not in history:
            history["actions"] = []
        
        history["actions"].append(event_name)
        
        await self.memory.set_plan_state(
            self.plan_id,
            self._action_history_key,
            history,
        )
    
    async def get_action_history(self) -> List[str]:
        """
        Get the list of recorded actions for this plan.
        
        Returns:
            List of action names in chronological order
        """
        try:
            history_response = await self.memory.get_plan_state(
                self.plan_id,
                self._action_history_key,
            )
            history = history_response.value
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
        await self.memory.set_plan_state(
            self.plan_id,
            key,
            {"value": value},
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
            response = await self.memory.get_plan_state(self.plan_id, key)
            return response.value.get("value", default)
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
            await self.memory.get_plan_state(self.plan_id, key)
            return True
        except Exception:
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Delete a key from plan-scoped state.
        
        Note: The Memory Service doesn't have a delete endpoint yet,
        so this sets the value to None as a workaround.
        
        Args:
            key: State key
            
        Returns:
            True if deleted, False if key didn't exist
        """
        if await self.has(key):
            await self.set(key, None)
            return True
        return False
    
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
