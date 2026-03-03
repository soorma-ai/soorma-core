"""Custom exceptions for soorma-nats library."""


class NATSConnectionError(Exception):
    """Raised when NATS connection fails or is lost."""
    pass


class NATSSubscriptionError(Exception):
    """Raised when NATS subscription fails."""
    pass
