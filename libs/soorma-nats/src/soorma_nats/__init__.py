"""soorma-nats: Shared NATS client for Soorma infrastructure services.

Public API::

    from soorma_nats import NATSClient, NATSConnectionError, NATSSubscriptionError
"""

from .client import NATSClient, MessageCallback
from .exceptions import NATSConnectionError, NATSSubscriptionError

__all__ = [
    "NATSClient",
    "MessageCallback",
    "NATSConnectionError",
    "NATSSubscriptionError",
]
