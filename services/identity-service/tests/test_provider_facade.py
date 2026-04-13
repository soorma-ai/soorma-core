"""Provider facade token tests."""

import json

import pytest
import jwt
from jwt.algorithms import RSAAlgorithm

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import load_pem_public_key

from identity_service.services.provider_facade import provider_facade


def _generate_rsa_keypair() -> tuple[str, str]:
    """Generate PEM keypair for RS256 tests."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")
    return private_pem, public_pem


def _jwks_document_for_key(kid: str, public_pem: str) -> str:
    """Build JWKS payload containing a single RSA public key."""
    public_key_obj = load_pem_public_key(public_pem.encode("utf-8"))
    jwk_payload = json.loads(RSAAlgorithm.to_jwk(public_key_obj))
    jwk_payload.update({"kid": kid, "use": "sig", "alg": "RS256"})
    return json.dumps({"keys": [jwk_payload]})


@pytest.mark.asyncio
async def test_issue_signed_token_and_validate_roundtrip(monkeypatch: pytest.MonkeyPatch):
    """Provider facade should issue and validate RS256 token for the same issuer."""
    private_pem, public_pem = _generate_rsa_keypair()

    monkeypatch.setenv("IDENTITY_SIGNING_ALGORITHM", "RS256")
    monkeypatch.setenv("IDENTITY_SIGNING_PRIVATE_KEY_PEM", private_pem)
    monkeypatch.setenv("IDENTITY_SIGNING_PUBLIC_KEY_PEM", public_pem)
    monkeypatch.setenv("IDENTITY_SIGNING_KEY_ID", "kid-main")
    monkeypatch.setenv("IDENTITY_ACTIVE_SIGNING_KID", "kid-main")

    token = await provider_facade.issue_signed_token(
        {
            "tenant_domain_id": "td-acme",
            "principal_id": "principal-1",
            "iss": "issuer-a",
        }
    )
    assert token
    headers = jwt.get_unverified_header(token)
    assert headers["alg"] == "RS256"
    assert headers["kid"] == "kid-main"

    assert await provider_facade.validate_delegated_assertion("issuer-a", token)
    assert not await provider_facade.validate_delegated_assertion("issuer-b", token)


@pytest.mark.asyncio
async def test_validate_delegated_assertion_rejects_unknown_kid(monkeypatch: pytest.MonkeyPatch):
    """Facade should fail closed when token kid is not known by verifier."""
    private_pem, public_pem = _generate_rsa_keypair()

    monkeypatch.setenv("IDENTITY_SIGNING_ALGORITHM", "RS256")
    monkeypatch.setenv("IDENTITY_SIGNING_PRIVATE_KEY_PEM", private_pem)
    monkeypatch.setenv("IDENTITY_SIGNING_PUBLIC_KEY_PEM", public_pem)
    monkeypatch.setenv("IDENTITY_SIGNING_KEY_ID", "kid-main")

    other_private_pem, _ = _generate_rsa_keypair()
    token = jwt.encode(
        {
            "iss": "issuer-a",
            "sub": "principal-1",
            "exp": 4102444800,
        },
        other_private_pem,
        algorithm="RS256",
        headers={"kid": "kid-unknown", "alg": "RS256"},
    )

    assert not await provider_facade.validate_delegated_assertion("issuer-a", token)


@pytest.mark.asyncio
async def test_validate_delegated_assertion_rejects_invalid_signature(monkeypatch: pytest.MonkeyPatch):
    """Facade should fail closed when kid is known but signature is invalid."""
    private_pem, public_pem = _generate_rsa_keypair()

    monkeypatch.setenv("IDENTITY_SIGNING_ALGORITHM", "RS256")
    monkeypatch.setenv("IDENTITY_SIGNING_PRIVATE_KEY_PEM", private_pem)
    monkeypatch.setenv("IDENTITY_SIGNING_PUBLIC_KEY_PEM", public_pem)
    monkeypatch.setenv("IDENTITY_SIGNING_KEY_ID", "kid-main")

    wrong_private_pem, _ = _generate_rsa_keypair()
    token = jwt.encode(
        {
            "iss": "issuer-a",
            "sub": "principal-1",
            "exp": 4102444800,
        },
        wrong_private_pem,
        algorithm="RS256",
        headers={"kid": "kid-main", "alg": "RS256"},
    )

    assert not await provider_facade.validate_delegated_assertion("issuer-a", token)


@pytest.mark.asyncio
async def test_validate_delegated_assertion_rejects_bad_token(monkeypatch: pytest.MonkeyPatch):
    """Facade should reject malformed delegated assertions."""
    private_pem, public_pem = _generate_rsa_keypair()

    monkeypatch.setenv("IDENTITY_SIGNING_ALGORITHM", "RS256")
    monkeypatch.setenv("IDENTITY_SIGNING_PRIVATE_KEY_PEM", private_pem)
    monkeypatch.setenv("IDENTITY_SIGNING_PUBLIC_KEY_PEM", public_pem)
    monkeypatch.setenv("IDENTITY_SIGNING_KEY_ID", "kid-main")

    assert not await provider_facade.validate_delegated_assertion("issuer-a", "bad.token.value")


@pytest.mark.asyncio
async def test_validate_delegated_assertion_uses_jwks_primary_without_fallback(
    monkeypatch: pytest.MonkeyPatch,
):
    """JWKS primary key match should succeed even when fallback key material is stale."""
    private_pem, public_pem = _generate_rsa_keypair()
    stale_private_pem, stale_public_pem = _generate_rsa_keypair()

    monkeypatch.setenv("IDENTITY_SIGNING_ALGORITHM", "RS256")
    monkeypatch.setenv("IDENTITY_SIGNING_PRIVATE_KEY_PEM", stale_private_pem)
    monkeypatch.setenv("IDENTITY_SIGNING_PUBLIC_KEY_PEM", stale_public_pem)
    monkeypatch.setenv("IDENTITY_SIGNING_KEY_ID", "kid-main")
    monkeypatch.setenv("IDENTITY_VERIFIER_JWKS_JSON", _jwks_document_for_key("kid-main", public_pem))

    token = jwt.encode(
        {
            "iss": "issuer-a",
            "sub": "principal-1",
            "exp": 4102444800,
        },
        private_pem,
        algorithm="RS256",
        headers={"kid": "kid-main", "alg": "RS256"},
    )

    assert await provider_facade.validate_delegated_assertion("issuer-a", token)


@pytest.mark.asyncio
async def test_validate_delegated_assertion_does_not_fallback_when_jwks_primary_fails(
    monkeypatch: pytest.MonkeyPatch,
):
    """If JWKS has kid but verification fails, request must fail closed without fallback."""
    valid_private_pem, valid_public_pem = _generate_rsa_keypair()
    stale_private_pem, stale_public_pem = _generate_rsa_keypair()

    monkeypatch.setenv("IDENTITY_SIGNING_ALGORITHM", "RS256")
    monkeypatch.setenv("IDENTITY_SIGNING_PRIVATE_KEY_PEM", valid_private_pem)
    monkeypatch.setenv("IDENTITY_SIGNING_PUBLIC_KEY_PEM", valid_public_pem)
    monkeypatch.setenv("IDENTITY_SIGNING_KEY_ID", "kid-main")
    monkeypatch.setenv("IDENTITY_VERIFIER_JWKS_JSON", _jwks_document_for_key("kid-main", stale_public_pem))

    token = jwt.encode(
        {
            "iss": "issuer-a",
            "sub": "principal-1",
            "exp": 4102444800,
        },
        valid_private_pem,
        algorithm="RS256",
        headers={"kid": "kid-main", "alg": "RS256"},
    )

    assert not await provider_facade.validate_delegated_assertion("issuer-a", token)
