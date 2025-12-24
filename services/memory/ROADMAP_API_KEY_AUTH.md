# API Key Authentication Implementation (Future Release)

## Status: 📋 PLANNED

API Key authentication is planned for a future release (v0.6.0 or later) alongside JWT authentication.

## Overview

The Memory Service will support dual authentication modes to handle both user-facing applications and autonomous agent operations in a future release. **The current release (v0.5.0) operates in single-tenant, unauthenticated mode** with explicit `user_id` and `agent_id` parameters.

## Authentication Modes

### Mode 1: JWT Token (Planned - Future Release)
**Use Case**: User-facing applications, web apps, direct user interactions

**Flow**:
```
User → JWT Token (tenant_id + user_id) → Memory Service
```

**Properties**:
- Auth: `Authorization: Bearer <jwt-token>`
- JWT contains: `{"tenant_id": "...", "user_id": "...", ...}`
- `user_id` extracted from token automatically
- `agent_id` passed as parameter

**Example**:
```python
client = MemoryClient(auth_token="jwt-token")
await client.get_recent_history(agent_id="chatbot", limit=10)
# user_id comes from JWT
```

### Mode 2: API Key (Planned - Future Release)
**Use Case**: Autonomous agents, background jobs, scheduled tasks, agent-to-agent communication

**Flow**:
```
Agent → API Key (tenant_id + agent_id) → Memory Service
```

**Properties**:
- Auth: `X-API-Key: sk_test_...`
- API Key contains: `{"tenant_id": "...", "agent_id": "...", ...}`
- `user_id` MUST be passed as explicit parameter
- `agent_id` passed as parameter (can differ from auth agent_id)

**Example**:
```python
client = MemoryClient(api_key="sk_test_...")
await client.get_recent_history(
    agent_id="background-processor",
    user_id="alice",  # REQUIRED - explicit parameter
    limit=10
)
```

## Implementation Status

### Current State (v0.5.0)

⚠️ **Single-Tenant, Unauthenticated Mode**
- The Memory Service operates without authentication in v0.5.0
- All methods require explicit `user_id` and `agent_id` parameters
- No JWT or API Key authentication is implemented
- Suitable for development and single-tenant deployments

### Planned for Future Release (v0.6.0+)

📋 **Middleware Updates** - `services/memory/src/memory_service/core/middleware.py`
- Add support for both JWT and API Key authentication
- Extract `tenant_id` + `user_id` from JWT
- Extract `tenant_id` + `agent_id` from API Key
- Handle `user_id` from query parameters when using API Key

📋 **API Endpoint Updates**
- `services/memory/src/memory_service/api/v1/episodic.py` - Support authentication middleware
- `services/memory/src/memory_service/api/v1/procedural.py` - Support authentication middleware

📋 **SDK Client Updates** - `sdk/python/soorma/memory/client.py`
- Add `auth_token` parameter for JWT authentication
- Add `api_key` parameter for API Key authentication
- Update authentication headers appropriately

📋 **Context Wrapper Updates** - `sdk/python/soorma/context.py`
- Support authenticated and unauthenticated modes
- Handle optional vs required `user_id` parameter based on auth mode

📋 **API Key Management** - New module to be created
- `generate_api_key()` - Generate API keys with tenant_id + agent_id
- `verify_api_key()` - Verify and decode API keys
- `check_permission()` - Permission checking for API keys

📋 **Configuration** - `services/memory/src/memory_service/core/config.py`
- Add `jwt_secret` setting
- Add `api_key_secret` setting
- Add `api_key_enabled` setting

## Implementation Tasks

### 1. Middleware Updates (`services/memory/src/memory_service/core/middleware.py`)

**Current**:
```python
class TenancyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Only handles JWT tokens
        auth_header = request.headers.get("Authorization")
        token = auth_header.split(" ")[1]
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        
        request.state.tenant_id = payload["tenant_id"]
        request.state.user_id = payload["user_id"]
```

**Needed**:
```python
class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        tenant_id = None
        user_id = None
        auth_agent_id = None  # Agent ID from API Key
        
        # Try JWT first
        if "Authorization" in request.headers:
            token = request.headers["Authorization"].replace("Bearer ", "")
            payload = jwt.decode(token, secret_key, algorithms=["HS256"])
            tenant_id = payload["tenant_id"]
            user_id = payload["user_id"]  # Available from JWT
            
        # Try API Key
        elif "X-API-Key" in request.headers:
            api_key = request.headers["X-API-Key"]
            payload = verify_api_key(api_key)  # New function needed
            tenant_id = payload["tenant_id"]
            auth_agent_id = payload["agent_id"]  # From API Key
            user_id = None  # Must come from request parameters
            
        request.state.tenant_id = tenant_id
        request.state.user_id = user_id
        request.state.auth_agent_id = auth_agent_id
```

### 2. API Endpoint Updates

All episodic and procedural memory endpoints need optional `user_id` query parameter:

**Current** (`services/memory/src/memory_service/api/v1/episodic.py`):
```python
@router.get("/recent")
async def get_recent_history(
    request: Request,
    agent_id: str = Query(..., description="Agent identifier"),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = UUID(get_tenant_id(request))
    user_id = UUID(get_user_id(request))  # Always from auth
```

**Needed**:
```python
@router.get("/recent")
async def get_recent_history(
    request: Request,
    agent_id: str = Query(..., description="Agent identifier"),
    user_id: Optional[str] = Query(None, description="User identifier (required with API Key auth)"),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = UUID(get_tenant_id(request))
    
    # Use user_id from parameter if provided (API Key mode), else from auth (JWT mode)
    if user_id:
        user_id_uuid = UUID(user_id)
    else:
        user_id_uuid = UUID(get_user_id(request))
        if not user_id_uuid:
            raise HTTPException(400, "user_id required when using API Key authentication")
```

**Files to update**:
- `services/memory/src/memory_service/api/v1/episodic.py`:
  - `POST /episodic` - add optional `user_id` query param
  - `GET /episodic/recent` - add optional `user_id` query param
  - `GET /episodic/search` - add optional `user_id` query param
- `services/memory/src/memory_service/api/v1/procedural.py`:
  - `GET /procedural/context` - add optional `user_id` query param
- `services/memory/src/memory_service/api/v1/semantic.py`:
  - No changes needed (tenant-scoped only, no user_id)

### 3. SDK Client Updates (`sdk/python/soorma/memory/client.py`)

**Current**:
```python
class MemoryClient:
    def __init__(self, base_url: str, auth_token: Optional[str] = None):
        headers = {}
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
```

**Needed**:
```python
class MemoryClient:
    def __init__(
        self, 
        base_url: str, 
        auth_token: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        headers = {}
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
        elif api_key:
            headers["X-API-Key"] = api_key
```

**Method updates**:
```python
async def get_recent_history(
    self,
    agent_id: str,
    user_id: Optional[str] = None,  # NEW - optional for JWT, required for API Key
    limit: int = 10,
) -> List[EpisodicMemoryResponse]:
    params = {"agent_id": agent_id, "limit": limit}
    if user_id:
        params["user_id"] = user_id
    
    response = await self._client.get(
        f"{self.base_url}/v1/memory/episodic/recent",
        params=params,
    )
```

**Methods to update**:
- `log_interaction()` - add optional `user_id` parameter
- `get_recent_history()` - add optional `user_id` parameter
- `search_interactions()` - add optional `user_id` parameter
- `get_relevant_skills()` - add optional `user_id` parameter

### 4. Context Wrapper Updates (`sdk/python/soorma/context.py`)

Add `user_id` parameter to high-level wrapper methods:

```python
async def get_recent_history(
    self,
    agent_id: str,
    user_id: Optional[str] = None,  # NEW
    limit: int = 10,
) -> List[Dict[str, Any]]:
    client = await self._ensure_client()
    try:
        results = await client.get_recent_history(
            agent_id, 
            user_id=user_id,  # Pass through
            limit=limit
        )
```

### 5. API Key Management Service (NEW)

Create new service/module for API key management:

```python
# services/memory/src/memory_service/core/api_keys.py

from typing import Dict, Any
import jwt
from datetime import datetime, timedelta

def generate_api_key(tenant_id: str, agent_id: str, permissions: list) -> str:
    """Generate a new API key for an agent."""
    payload = {
        "tenant_id": tenant_id,
        "agent_id": agent_id,
        "permissions": permissions,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(days=365),  # 1 year expiration
    }
    return jwt.encode(payload, settings.api_key_secret, algorithm="HS256")

def verify_api_key(api_key: str) -> Dict[str, Any]:
    """Verify and decode an API key."""
    try:
        payload = jwt.decode(api_key, settings.api_key_secret, algorithms=["HS256"])
        return payload
    except jwt.InvalidTokenError as e:
        raise HTTPException(401, f"Invalid API key: {str(e)}")
```

### 6. Configuration Updates

Add API key configuration to settings:

```python
# services/memory/src/memory_service/core/config.py

class Settings(BaseSettings):
    # Existing JWT settings
    jwt_secret: Optional[str] = None
    jwt_algorithm: str = "HS256"
    
    # NEW: API Key settings
    api_key_secret: Optional[str] = None  # Separate secret for API keys
    api_key_enabled: bool = True  # Enable/disable API key auth
```

### 7. Tests

Add test coverage for API key authentication:

```python
# services/memory/tests/test_api_key_auth.py

async def test_api_key_authentication():
    """Test API key authentication flow."""
    api_key = generate_api_key(
        tenant_id="test-tenant",
        agent_id="test-agent",
        permissions=["memory:read", "memory:write"]
    )
    
    client = MemoryClient(api_key=api_key)
    
    # Must provide user_id explicitly
    await client.log_interaction(
        agent_id="test-agent",
        user_id="test-user",  # Explicit
        role="system",
        content="Test message"
    )
```

## Migration Guide

### For Users (No Changes Required)

JWT authentication continues to work exactly as before:

```python
# v0.5.0 - Works
client = MemoryClient(auth_token="jwt-token")
await client.get_recent_history("chatbot", limit=10)

# v0.6.0 - Still works (backward compatible)
client = MemoryClient(auth_token="jwt-token")
await client.get_recent_history("chatbot", limit=10)
```

### For Agents (New Capability)

Agents can now use API keys:

```python
# v0.6.0 - NEW
client = MemoryClient(api_key="sk_test_...")
await client.get_recent_history(
    agent_id="processor",
    user_id="alice",  # Now required with API Key
    limit=10
)
```

## Backward Compatibility

✅ **Fully backward compatible**:
- JWT authentication unchanged
- All existing code continues to work
- `user_id` parameter is optional (defaults to value from JWT)
## Timeline

- **v0.5.0** (Current): Single-tenant, unauthenticated mode - explicit `user_id` and `agent_id` parameters
- **v0.6.0** (Q1 2026): Dual authentication (JWT + API Key) implementation
- **v0.7.0** (Q2 2026): API key management UI/CLI, advanced permissions
- **v0.8.0** (Q2 2026): API key rotation, audit logging enhancementsret
2. **Key Rotation**: Implement API key rotation mechanism
3. **Permissions**: API keys should have scoped permissions (read/write/admin)
4. **Audit Logging**: Log all API key usage for security monitoring
5. **Rate Limiting**: Implement rate limits per API key
6. **Tenant Isolation**: RLS still enforces tenant isolation regardless of auth method

## Timeline

- **v0.5.0** (Current): ✅ Dual authentication (JWT + API Key) implemented
- **v0.6.0** (Q1 2026): API key management UI/CLI, advanced permissions
- **v0.7.0** (Q2 2026): API key rotation, audit logging enhancements

## Related Documentation

- [MEMORY_SERVICE.md](../../sdk/python/docs/MEMORY_SERVICE.md) - SDK documentation with dual auth examples
- [soorma-common README](../../libs/soorma-common/README.md) - DTOs with scoping details
