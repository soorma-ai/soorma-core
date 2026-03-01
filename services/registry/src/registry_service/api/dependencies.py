"""
API dependencies for authentication and request context.

This module provides FastAPI dependencies for extracting authentication
context from request headers (v0.7.x development pattern).
"""
from uuid import UUID
from fastapi import Header, HTTPException, status
from typing import Tuple


async def get_auth_context(
    x_tenant_id: str = Header(..., description="Tenant ID from authentication"),
    x_user_id: str = Header(..., description="User ID from authentication")
) -> Tuple[UUID, UUID]:
    """
    Extract tenant_id and user_id from request headers.
    
    This is the v0.7.x development authentication pattern using custom headers.
    In v0.8.0+, this will be replaced with JWT/API Key validation.
    
    Args:
        x_tenant_id: Tenant ID from X-Tenant-ID header
        x_user_id: User ID from X-User-ID header
        
    Returns:
        Tuple of (tenant_id, user_id) as UUIDs
        
    Raises:
        HTTPException: 400 if headers are missing or invalid
        HTTPException: 401 if authentication fails (future JWT validation)
    """
    try:
        tenant_id = UUID(x_tenant_id)
        user_id = UUID(x_user_id)
        return (tenant_id, user_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid UUID format in authentication headers: {str(e)}"
        )
