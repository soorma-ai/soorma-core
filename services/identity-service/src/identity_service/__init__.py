"""Identity service package."""

from soorma_common import __version__

def get_app():
    """Get the FastAPI application instance (lazy import to avoid initialization issues)."""
    from .main import app
    return app

__all__ = ["get_app", "__version__"]
