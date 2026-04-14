"""Provider facade abstraction."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
import os
from typing import Any

import jwt
from jwt.algorithms import RSAAlgorithm

from cryptography.hazmat.primitives.serialization import load_pem_public_key


_SIGNING_ALGORITHM_ENV = "IDENTITY_SIGNING_ALGORITHM"
_ACTIVE_SIGNING_KID_ENV = "IDENTITY_ACTIVE_SIGNING_KID"
_SIGNING_KEY_ID_ENV = "IDENTITY_SIGNING_KEY_ID"
_SIGNING_KEYRING_ENV = "IDENTITY_SIGNING_KEYRING_JSON"

_SIGNING_PRIVATE_KEY_PEM_ENV = "IDENTITY_SIGNING_PRIVATE_KEY_PEM"
_SIGNING_PUBLIC_KEY_PEM_ENV = "IDENTITY_SIGNING_PUBLIC_KEY_PEM"
_SIGNING_PRIVATE_KEYRING_ENV = "IDENTITY_SIGNING_PRIVATE_KEYRING_JSON"
_SIGNING_PUBLIC_KEYRING_ENV = "IDENTITY_SIGNING_PUBLIC_KEYRING_JSON"

_VERIFIER_JWKS_ENV = "IDENTITY_VERIFIER_JWKS_JSON"
_JWKS_PUBLICATION_ENV = "IDENTITY_JWKS_PUBLICATION_JSON"
_IDENTITY_ISSUER_ENV = "IDENTITY_ISSUER"


class ProviderFacade:
    """Provider adapter abstraction for signing/trust backends."""

    def _load_json_keyring(self, env_var_name: str) -> dict[str, str]:
        """Load keyring mapping from JSON environment variable."""
        keyring_raw = str(os.getenv(env_var_name) or "").strip()
        if keyring_raw:
            try:
                parsed = json.loads(keyring_raw)
                if isinstance(parsed, dict):
                    return {
                        str(kid).strip(): str(key).strip()
                        for kid, key in parsed.items()
                        if str(kid).strip() and str(key).strip()
                    }
            except json.JSONDecodeError:
                pass

        return {}

    def _load_symmetric_signing_keyring(self) -> dict[str, str]:
        """Load symmetric fallback signing keys keyed by kid."""
        keyring = self._load_json_keyring(_SIGNING_KEYRING_ENV)
        if keyring:
            return keyring

        fallback_key = os.getenv("IDENTITY_SIGNING_KEY", "dev-identity-signing-key")
        fallback_kid = str(os.getenv(_SIGNING_KEY_ID_ENV, "default") or "default").strip() or "default"
        return {fallback_kid: fallback_key}

    def _load_asymmetric_signing_keyring(self) -> dict[str, tuple[str, str]]:
        """Load asymmetric signing keyring as kid -> (private_pem, public_pem)."""
        private_ring = self._load_json_keyring(_SIGNING_PRIVATE_KEYRING_ENV)
        public_ring = self._load_json_keyring(_SIGNING_PUBLIC_KEYRING_ENV)

        paired_ring: dict[str, tuple[str, str]] = {
            kid: (private_ring[kid], public_ring[kid])
            for kid in private_ring.keys() & public_ring.keys()
        }
        if paired_ring:
            return paired_ring

        private_key_pem = str(os.getenv(_SIGNING_PRIVATE_KEY_PEM_ENV) or "").strip()
        public_key_pem = str(os.getenv(_SIGNING_PUBLIC_KEY_PEM_ENV) or "").strip()
        if private_key_pem and public_key_pem:
            kid = str(os.getenv(_SIGNING_KEY_ID_ENV, "default-rs256") or "default-rs256").strip() or "default-rs256"
            return {kid: (private_key_pem, public_key_pem)}

        return {}

    def _resolve_signing_algorithm(self) -> str:
        """Resolve signing algorithm with explicit config priority."""
        configured_algorithm = str(os.getenv(_SIGNING_ALGORITHM_ENV) or "").strip().upper()
        if configured_algorithm in {"RS256", "HS256"}:
            return configured_algorithm

        if self._load_asymmetric_signing_keyring():
            return "RS256"
        return "HS256"

    def _resolve_active_signing_material(self) -> tuple[str, str, str]:
        """Resolve active signing kid/key/algorithm for token issuance."""
        algorithm = self._resolve_signing_algorithm()
        configured_kid = str(os.getenv(_ACTIVE_SIGNING_KID_ENV) or "").strip()

        if algorithm == "RS256":
            keyring = self._load_asymmetric_signing_keyring()
            if not keyring:
                raise ValueError("RS256 signing selected but asymmetric key material is not configured")

            if configured_kid and configured_kid in keyring:
                return configured_kid, keyring[configured_kid][0], algorithm
            if configured_kid and configured_kid not in keyring:
                first_kid, (private_key_pem, _) = next(iter(keyring.items()))
                return first_kid, private_key_pem, algorithm

            first_kid, (private_key_pem, _) = next(iter(keyring.items()))
            return first_kid, private_key_pem, algorithm

        keyring = self._load_symmetric_signing_keyring()
        if configured_kid and configured_kid in keyring:
            return configured_kid, keyring[configured_kid], algorithm
        if configured_kid and configured_kid not in keyring:
            first_kid, key = next(iter(keyring.items()))
            return first_kid, key, algorithm

        first_kid, key = next(iter(keyring.items()))
        return first_kid, key, algorithm

    def _load_verifier_jwks(self) -> dict[str, Any]:
        """Load verifier JWKS JSON payload when configured."""
        raw_jwks = str(os.getenv(_VERIFIER_JWKS_ENV) or os.getenv(_JWKS_PUBLICATION_ENV) or "").strip()
        if not raw_jwks:
            return {}
        try:
            parsed = json.loads(raw_jwks)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return {}
        return {}

    def _load_jwks_primary_verifier_keys(self, algorithm: str) -> dict[str, Any]:
        """Load verifier keys from JWKS publication for primary verification path."""
        if algorithm != "RS256":
            return {}

        jwks_payload = self._load_verifier_jwks()
        jwk_keys = jwks_payload.get("keys") if isinstance(jwks_payload, dict) else None
        if not isinstance(jwk_keys, list):
            return {}

        verifier_keys: dict[str, Any] = {}
        for key_entry in jwk_keys:
            if not isinstance(key_entry, dict):
                continue
            kid = str(key_entry.get("kid") or "").strip()
            if not kid:
                continue
            try:
                verifier_keys[kid] = RSAAlgorithm.from_jwk(json.dumps(key_entry))
            except Exception:
                continue

        return verifier_keys

    def _load_static_fallback_verifier_keys(self, algorithm: str) -> dict[str, Any]:
        """Load static fallback verifier keys for deterministic precedence chain."""
        if algorithm == "RS256":
            return {
                kid: public_key_pem
                for kid, (_, public_key_pem) in self._load_asymmetric_signing_keyring().items()
            }
        return self._load_symmetric_signing_keyring()

    def _verify_token(
        self,
        issuer_id: str,
        assertion: str,
        algorithm: str,
        verification_key: Any,
    ) -> bool:
        """Verify token and enforce issuer match."""
        try:
            claims = jwt.decode(
                assertion,
                verification_key,
                algorithms=[algorithm],
                options={"verify_aud": False},
            )
        except jwt.PyJWTError:
            return False
        return claims.get("iss") == issuer_id

    def get_jwks(self) -> dict[str, list[dict[str, Any]]]:
        """Publish signing public keys as JWKS for consumers."""
        if self._resolve_signing_algorithm() != "RS256":
            return {"keys": []}

        jwks_keys: list[dict[str, Any]] = []
        for kid, (_, public_key_pem) in self._load_asymmetric_signing_keyring().items():
            try:
                public_key_obj = load_pem_public_key(public_key_pem.encode("utf-8"))
                jwk_payload = json.loads(RSAAlgorithm.to_jwk(public_key_obj))
            except Exception:
                continue

            jwk_payload.update(
                {
                    "kid": kid,
                    "use": "sig",
                    "alg": "RS256",
                }
            )
            jwks_keys.append(jwk_payload)

        return {"keys": jwks_keys}

    def get_openid_configuration(self, service_base_url: str) -> dict[str, Any]:
        """Publish compatibility discovery metadata for verifier consumers."""
        issuer = str(os.getenv(_IDENTITY_ISSUER_ENV) or service_base_url).rstrip("/")
        return {
            "issuer": issuer,
            "jwks_uri": f"{issuer}/v1/identity/.well-known/jwks.json",
            "token_endpoint": f"{issuer}/v1/identity/tokens/issue",
            "id_token_signing_alg_values_supported": [self._resolve_signing_algorithm()],
        }

    async def issue_signed_token(self, claims: dict[str, object]) -> str:
        """Issue signed token from provider adapter."""
        signing_kid, signing_key, signing_algorithm = self._resolve_active_signing_material()
        issued_at = datetime.now(UTC)
        normalized_claims = dict(claims)
        normalized_claims.setdefault("iat", int(issued_at.timestamp()))
        normalized_claims.setdefault("exp", int((issued_at + timedelta(minutes=15)).timestamp()))
        normalized_claims.setdefault("iss", "soorma-identity-service")
        return jwt.encode(
            normalized_claims,
            signing_key,
            algorithm=signing_algorithm,
            headers={"kid": signing_kid, "alg": signing_algorithm, "typ": "JWT"},
        )

    async def validate_delegated_assertion(self, issuer_id: str, assertion: str) -> bool:
        """Validate delegated assertion against provider trust backend."""
        try:
            unverified_header = jwt.get_unverified_header(assertion)
        except jwt.PyJWTError:
            return False

        kid = str(unverified_header.get("kid") or "").strip()
        algorithm = str(unverified_header.get("alg") or "").strip().upper()
        if not kid or algorithm not in {"HS256", "RS256"}:
            return False

        primary_jwks_keys = self._load_jwks_primary_verifier_keys(algorithm)
        if primary_jwks_keys:
            primary_key = primary_jwks_keys.get(kid)
            if primary_key is not None:
                return self._verify_token(issuer_id, assertion, algorithm, primary_key)

        fallback_keys = self._load_static_fallback_verifier_keys(algorithm)
        fallback_key = fallback_keys.get(kid)
        if fallback_key is None:
            return False
        return self._verify_token(issuer_id, assertion, algorithm, fallback_key)


provider_facade = ProviderFacade()
