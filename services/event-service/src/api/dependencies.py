"""
API dependencies for authentication and request context.

Event Service Authentication Model (v0.8.x):
  platform_tenant_id is extracted from validated bearer-token identity by
  TenancyMiddleware and stored on request.state. get_platform_tenant_id reads it
  as a plain str.

  Event Service remains the trust boundary for platform-tenant enrichment; SDK
  callers must not inject platform_tenant_id into outbound event payloads.
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
