"""
API dependencies for authentication and request context.

Event Service Authentication Model (v0.7.x):
  platform_tenant_id is extracted from the X-Tenant-ID header by TenancyMiddleware
  and stored on request.state. get_platform_tenant_id reads it as a plain str.

  v0.8.0+: this extraction path can shift to API key / JWT without changing
  route business logic.
"""

from soorma_service_common import get_platform_tenant_id  # noqa: F401

from soorma_service_common import RouteAuthPolicy  # noqa: F401


default_event_route_policy = RouteAuthPolicy(
  route_id="event-service.default",
  auth_required=True,
  allow_delegated_context=False,
)

__all__ = [
  "get_platform_tenant_id",
  "default_event_route_policy",
]
