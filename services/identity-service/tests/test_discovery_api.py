"""Discovery and JWKS endpoint tests."""

import json

import pytest
from httpx import ASGITransport, AsyncClient
from jwt.algorithms import RSAAlgorithm

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from identity_service.main import app


def _generate_rsa_keypair() -> tuple[str, str]:
    """Generate PEM keypair for RS256 discovery tests."""
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


@pytest.mark.asyncio
async def test_jwks_endpoint_publishes_rs256_key(monkeypatch: pytest.MonkeyPatch):
    """JWKS endpoint should publish configured RS256 public key with kid metadata."""
    private_pem, public_pem = _generate_rsa_keypair()

    monkeypatch.setenv("IDENTITY_SIGNING_ALGORITHM", "RS256")
    monkeypatch.setenv("IDENTITY_SIGNING_PRIVATE_KEY_PEM", private_pem)
    monkeypatch.setenv("IDENTITY_SIGNING_PUBLIC_KEY_PEM", public_pem)
    monkeypatch.setenv("IDENTITY_SIGNING_KEY_ID", "kid-discovery")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        response = await async_client.get("/v1/identity/.well-known/jwks.json")

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload["keys"], list)
    assert len(payload["keys"]) == 1

    key_payload = payload["keys"][0]
    assert key_payload["kid"] == "kid-discovery"
    assert key_payload["kty"] == "RSA"
    assert key_payload["alg"] == "RS256"
    assert key_payload["use"] == "sig"

    # Ensure published key can be parsed by JWT consumers.
    RSAAlgorithm.from_jwk(json.dumps(key_payload))


@pytest.mark.asyncio
async def test_openid_configuration_exposes_jwks_uri(monkeypatch: pytest.MonkeyPatch):
    """Discovery metadata should include issuer and JWKS URI for verifier clients."""
    private_pem, public_pem = _generate_rsa_keypair()

    monkeypatch.setenv("IDENTITY_SIGNING_ALGORITHM", "RS256")
    monkeypatch.setenv("IDENTITY_SIGNING_PRIVATE_KEY_PEM", private_pem)
    monkeypatch.setenv("IDENTITY_SIGNING_PUBLIC_KEY_PEM", public_pem)
    monkeypatch.setenv("IDENTITY_SIGNING_KEY_ID", "kid-discovery")
    monkeypatch.setenv("IDENTITY_ISSUER", "http://identity.local")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        response = await async_client.get("/v1/identity/.well-known/openid-configuration")

    assert response.status_code == 200
    payload = response.json()
    assert payload["issuer"] == "http://identity.local"
    assert payload["jwks_uri"] == "http://identity.local/v1/identity/.well-known/jwks.json"
    assert payload["token_endpoint"] == "http://identity.local/v1/identity/tokens/issue"
    assert payload["id_token_signing_alg_values_supported"] == ["RS256"]
