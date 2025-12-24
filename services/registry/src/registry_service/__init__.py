"""
Registry Service - Event and Agent Registry for Soorma platform.
"""

__version__ = "0.5.0"


def get_app():
    """Get the FastAPI application instance (lazy import to avoid initialization issues)."""
    from .main import app
    return app


__all__ = ["get_app", "__version__"]

