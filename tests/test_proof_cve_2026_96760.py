"""Proof for CVE-2026-96760: POST /charge must reject a token that carries no signature."""
from fastapi.testclient import TestClient

from billing_api.app import app

# A JWS in JSON serialization whose signatures array is empty.
FORGED = '{"payload": "eyJzdWIiOiJhbGljZSIsInJvbGUiOiJhZG1pbiJ9", "signatures": []}'


def test_forged_token_is_rejected():
    response = TestClient(app).request('POST', '/charge', headers={'Authorization': 'Bearer ' + FORGED}, json={'amount': 1, 'description': 'proof'})
    assert response.status_code == 401, "the token was accepted: " + response.text[:200]
