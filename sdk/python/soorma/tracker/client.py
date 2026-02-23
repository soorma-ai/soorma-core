"""
TrackerServiceClient - Low-level HTTP client for Tracker Service (Layer 1).

This client provides direct HTTP communication with the Tracker Service API.
It requires manual tenant_id/user_id parameters on all methods.

For agent handler code, use the high-level TrackerClient wrapper from
PlatformContext instead (context.tracker.*).
"""
from typing import Optional, List
import httpx

from soorma_common.tracker import (
    PlanProgress,
    TaskExecution,
    EventTimeline,
    AgentMetrics,
    PlanExecution,
    DelegationGroup,
)


class TrackerServiceClient:
    """
    Low-level HTTP client for Tracker Service (Layer 1).
    
    This client communicates directly with the Tracker Service API.
    All methods require explicit tenant_id and user_id parameters.
    
    For agent handlers, use the high-level TrackerClient wrapper instead
    (context.tracker.*) which automatically handles authentication.
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:8084",
        timeout: float = 30.0,
    ):
        """
        Initialize the Tracker Service client.
        
        Args:
            base_url: Base URL of the Tracker Service (default: http://localhost:8084)
            timeout: HTTP request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout)
    
    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def get_plan_progress(
        self,
        plan_id: str,
        tenant_id: str,
        user_id: str,
    ) -> Optional[PlanProgress]:
        """
        Get plan execution progress summary.
        
        Args:
            plan_id: Plan identifier
            tenant_id: Tenant ID (from event context)
            user_id: User ID (from event context)
            
        Returns:
            PlanProgress or None if plan not found
        """
        try:
            response = await self._client.get(
                f"{self.base_url}/v1/tracker/plans/{plan_id}",
                headers={
                    "X-Tenant-ID": tenant_id,
                    "X-User-ID": user_id,
                },
            )
            response.raise_for_status()
            return PlanProgress.model_validate(response.json())
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise
    
    async def get_plan_tasks(
        self,
        plan_id: str,
        tenant_id: str,
        user_id: str,
    ) -> List[TaskExecution]:
        """
        Get all tasks for a plan.
        
        Args:
            plan_id: Plan identifier
            tenant_id: Tenant ID (from event context)
            user_id: User ID (from event context)
            
        Returns:
            List of TaskExecution records
        """
        try:
            response = await self._client.get(
                f"{self.base_url}/v1/tracker/plans/{plan_id}/actions",
                headers={
                    "X-Tenant-ID": tenant_id,
                    "X-User-ID": user_id,
                },
            )
            response.raise_for_status()
            return [TaskExecution.model_validate(task) for task in response.json()]
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return []
            raise
    
    async def get_plan_timeline(
        self,
        plan_id: str,
        tenant_id: str,
        user_id: str,
    ) -> Optional[EventTimeline]:
        """
        Get event execution timeline for a plan.
        
        Args:
            plan_id: Plan identifier
            tenant_id: Tenant ID (from event context)
            user_id: User ID (from event context)
            
        Returns:
            EventTimeline or None if not found
        """
        try:
            response = await self._client.get(
                f"{self.base_url}/v1/tracker/plans/{plan_id}/timeline",
                headers={
                    "X-Tenant-ID": tenant_id,
                    "X-User-ID": user_id,
                },
            )
            response.raise_for_status()
            return EventTimeline.model_validate(response.json())
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise
    
    async def query_agent_metrics(
        self,
        agent_id: str,
        period: str,
        tenant_id: str,
        user_id: str,
    ) -> Optional[AgentMetrics]:
        """
        Query agent performance metrics.
        
        Args:
            agent_id: Agent identifier
            period: Time period (e.g., "7d", "30d", "1h")
            tenant_id: Tenant ID (from event context)
            user_id: User ID (from event context)
            
        Returns:
            AgentMetrics or None if not found
        """
        try:
            response = await self._client.get(
                f"{self.base_url}/v1/tracker/metrics",
                params={
                    "agent_id": agent_id,
                    "period": period,
                },
                headers={
                    "X-Tenant-ID": tenant_id,
                    "X-User-ID": user_id,
                },
            )
            response.raise_for_status()
            return AgentMetrics.model_validate(response.json())
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise
    
    async def get_sub_plans(
        self,
        plan_id: str,
        tenant_id: str,
        user_id: str,
    ) -> List[PlanExecution]:
        """
        Get child plans for a given plan (plan hierarchy).
        
        Args:
            plan_id: Parent plan identifier
            tenant_id: Tenant ID (from event context)
            user_id: User ID (from event context)
            
        Returns:
            List of child PlanExecution records
        """
        response = await self._client.get(
            f"{self.base_url}/v1/tracker/plans/{plan_id}/sub-plans",
            headers={
                "X-Tenant-ID": tenant_id,
                "X-User-ID": user_id,
            },
        )
        response.raise_for_status()
        return [PlanExecution.model_validate(plan) for plan in response.json()]
    
    async def get_session_plans(
        self,
        session_id: str,
        tenant_id: str,
        user_id: str,
    ) -> List[PlanExecution]:
        """
        Get all plans in a conversation session.
        
        Args:
            session_id: Session identifier
            tenant_id: Tenant ID (from event context)
            user_id: User ID (from event context)
            
        Returns:
            List of PlanExecution records in session
        """
        response = await self._client.get(
            f"{self.base_url}/v1/tracker/sessions/{session_id}/plans",
            headers={
                "X-Tenant-ID": tenant_id,
                "X-User-ID": user_id,
            },
        )
        response.raise_for_status()
        return [PlanExecution.model_validate(plan) for plan in response.json()]
    
    async def get_delegation_group(
        self,
        group_id: str,
        tenant_id: str,
        user_id: str,
    ) -> Optional[DelegationGroup]:
        """
        Get parallel delegation group status.
        
        Args:
            group_id: Delegation group identifier
            tenant_id: Tenant ID (from event context)
            user_id: User ID (from event context)
            
        Returns:
            DelegationGroup or None if not found
        """
        try:
            response = await self._client.get(
                f"{self.base_url}/v1/tracker/delegation-groups/{group_id}",
                headers={
                    "X-Tenant-ID": tenant_id,
                    "X-User-ID": user_id,
                },
            )
            response.raise_for_status()
            return DelegationGroup.model_validate(response.json())
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise
