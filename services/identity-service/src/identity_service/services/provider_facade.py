"""Provider facade abstraction."""

from datetime import UTC, datetime, timedelta
import os

import jwt


class ProviderFacade:
    """Provider adapter abstraction for signing/trust backends."""

    async def issue_signed_token(self, claims: dict[str, object]) -> str:
        """Issue signed token from provider adapter."""
        signing_key = os.getenv("IDENTITY_SIGNING_KEY", "dev-identity-signing-key")
        issued_at = datetime.now(UTC)
        normalized_claims = dict(claims)
        normalized_claims.setdefault("iat", int(issued_at.timestamp()))
        normalized_claims.setdefault("exp", int((issued_at + timedelta(minutes=15)).timestamp()))
        normalized_claims.setdefault("iss", "soorma-identity-service")
        return jwt.encode(normalized_claims, signing_key, algorithm="HS256")

    async def validate_delegated_assertion(self, issuer_id: str, assertion: str) -> bool:
        """Validate delegated assertion against provider trust backend."""
        signing_key = os.getenv("IDENTITY_SIGNING_KEY", "dev-identity-signing-key")
        try:
            claims = jwt.decode(assertion, signing_key, algorithms=["HS256"], options={"verify_aud": False})
        except Exception:
            return False
        return claims.get("iss") == issuer_id


provider_facade = ProviderFacade()
