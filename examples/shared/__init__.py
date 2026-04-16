"""Shared helpers for Soorma examples."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__all__ = [
    "ExampleTokenProvider",
    "build_example_token_provider",
    "ensure_example_auth_token",
]


if TYPE_CHECKING:
    from .auth import ExampleTokenProvider, build_example_token_provider, ensure_example_auth_token


def __getattr__(name: str) -> Any:
    """Lazily expose shared auth helpers without pre-importing the module."""
    if name in __all__:
        from . import auth

        return getattr(auth, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")