"""TrackerServiceClient - Low-level HTTP client for Tracker Service (Layer 1)."""

from typing import Dict, List, Optional

import httpx

from soorma_common.tenancy import DEFAULT_PLATFORM_TENANT_ID
from soorma_common.tracker import (
    AgentMetrics,
    DelegationGroup,
    EventTimeline,
    PlanExecution,
    PlanProgress,
    TaskExecution,
)


class TrackerServiceClient:
    """Low-level HTTP client for Tracker Service (Layer 1)."""

    def __init__(
        self,
        base_url: str = "http://localhost:8084",
        timeout: float = 30.0,
        platform_tenant_id: Optional[str] = None,
    ):
        """Initialize the Tracker Service client."""
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.platform_tenant_id = platform_tenant_id or DEFAULT_PLATFORM_TENANT_ID
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

    def _build_identity_headers(
        self,
        service_tenant_id: str,
        service_user_id: str,
    ) -> Dict[str, str]:
        """Build required identity headers for Tracker Service requests."""
        if not service_tenant_id or not service_user_id:
            raise ValueError("service_tenant_id and service_user_id are required")

        return {
            "X-Tenant-ID": self.platform_tenant_id,
            "X-Service-Tenant-ID": service_tenant_id,
            "X-User-ID": service_user_id,
        }

    async def get_plan_progress(
        self,
        plan_id: str,
        service_tenant_id: str,
        service_user_id: str,
    ) -> Optional[PlanProgress]:
        """Get plan execution progress summary."""
        try:
            response = await self._client.get(
                f"{self.base_url}/v1/tracker/plans/{plan_id}",
                headers=self._build_identity_headers(service_tenant_id, service_user_id),
            )
            response.raise_for_status()
            return PlanProgress.model_validate(response.json())
        except httpx.HTTPStatusError as error:
            if error.response.status_code == 404:
                return None
            raise

    async def get_plan_tasks(
        self,
        plan_id: str,
        service_tenant_id: str,
        service_user_id: str,
    ) -> List[TaskExecution]:
        """Get all tasks for a plan."""
        try:
            response = await self._client.get(
                f"{self.base_url}/v1/tracker/plans/{plan_id}/actions",
                headers=self._build_identity_headers(service_tenant_id, service_user_id),
            )
            response.raise_for_status()
            return [TaskExecution.model_validate(task) for task in response.json()]
        except httpx.HTTPStatusError as error:
            if error.response.status_code == 404:
                return []
            raise

    async def get_plan_timeline(
        self,
        plan_id: str,
        service_tenant_id: str,
        service_user_id: str,
    ) -> Optional[EventTimeline]:
        """Get event execution timeline for a plan."""
        try:
            response = await self._client.get(
                f"{self.base_url}/v1/tracker/plans/{plan_id}/timeline",
                headers=self._build_identity_headers(service_tenant_id, service_user_id),
            )
            response.raise_for_status()
            return EventTimeline.model_validate(response.json())
        except httpx.HTTPStatusError as error:
            if error.response.status_code == 404:
                return None
            raise

    async def query_agent_metrics(
        self,
        agent_id: str,
        period: str,
        service_tenant_id: str,
        service_user_id: str,
    ) -> Optional[AgentMetrics]:
        """Query agent performance metrics."""
        try:
            response = await self._client.get(
                f"{self.base_url}/v1/tracker/metrics",
                params={"agent_id": agent_id, "period": period},
                headers=self._build_identity_headers(service_tenant_id, service_user_id),
            )
            response.raise_for_status()
            return AgentMetrics.model_validate(response.json())
        except httpx.HTTPStatusError as error:
            if error.response.status_code == 404:
                return None
            raise

    async def get_sub_plans(
        self,
        plan_id: str,
        service_tenant_id: str,
        service_user_id: str,
    ) -> List[PlanExecution]:
        """Get child plans for a given plan."""
        response = await self._client.get(
            f"{self.base_url}/v1/tracker/plans/{plan_id}/sub-plans",
            headers=self._build_identity_headers(service_tenant_id, service_user_id),
        )
        response.raise_for_status()
        return [PlanExecution.model_validate(plan) for plan in response.json()]

    async def get_session_plans(
        self,
        session_id: str,
        service_tenant_id: str,
        service_user_id: str,
    ) -> List[PlanExecution]:
        """Get all plans in a conversation session."""
        response = await self._client.get(
            f"{self.base_url}/v1/tracker/sessions/{session_id}/plans",
            headers=self._build_identity_headers(service_tenant_id, service_user_id),
        )
        response.raise_for_status()
        return [PlanExecution.model_validate(plan) for plan in response.json()]

    async def get_delegation_group(
        self,
        group_id: str,
        service_tenant_id: str,
        service_user_id: str,
    ) -> Optional[DelegationGroup]:
        """Get parallel delegation group status."""
        try:
            response = await self._client.get(
                f"{self.base_url}/v1/tracker/delegation-groups/{group_id}",
                headers=self._build_identity_headers(service_tenant_id, service_user_id),
            )
            response.raise_for_status()
            return DelegationGroup.model_validate(response.json())
        except httpx.HTTPStatusError as error:
            if error.response.status_code == 404:
                return None
            raise
