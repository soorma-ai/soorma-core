"""Shared auth-token provider primitives for SDK clients."""

from __future__ import annotations

import inspect
from typing import Any, Awaitable, Callable, Optional, TypeAlias


AuthTokenProvider: TypeAlias = Callable[[], str | None | Awaitable[str | None]]


async def resolve_auth_token(
    auth_token: Optional[str],
    auth_token_provider: Optional[AuthTokenProvider],
) -> Optional[str]:
    """Resolve a bearer token from explicit value or provider."""
    if auth_token_provider is None:
        resolved = auth_token
    else:
        resolved = auth_token_provider()
        if inspect.isawaitable(resolved):
            resolved = await resolved

    token = str(resolved or "").strip()
    return token or None


def build_optional_auth_kwargs(
    auth_token: Optional[str],
    auth_token_provider: Optional[AuthTokenProvider],
) -> dict[str, Any]:
    """Return only explicitly configured auth kwargs for client constructors."""
    kwargs: dict[str, Any] = {}
    if auth_token is not None:
        kwargs["auth_token"] = auth_token
    if auth_token_provider is not None:
        kwargs["auth_token_provider"] = auth_token_provider
    return kwargs
