"""Smoke tests for identity-service app."""


def test_health_check(client):
    """Health endpoint should return basic service metadata."""
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["service"] == "identity-service"
