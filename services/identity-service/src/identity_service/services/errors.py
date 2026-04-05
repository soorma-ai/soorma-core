"""Domain exceptions for identity-service business failures."""


class IdentityServiceError(Exception):
    """Typed business error with stable HTTP mapping and safe message."""

    def __init__(self, code: str, message: str, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
