"""Tests for billing-api, driven through FastAPI's TestClient (no server)."""
import json

from authlib.jose import JsonWebSignature
from fastapi.testclient import TestClient

from billing_api.app import app
from billing_api.config import settings

client = TestClient(app)
_jws = JsonWebSignature(["HS256"])


def bearer(sub: str, role: str = "customer") -> str:
    """Build a properly signed compact bearer token for ``sub``."""
    token = _jws.serialize_compact(
        {"alg": "HS256", "typ": "JWT"},
        json.dumps({"sub": sub, "role": role}),
        settings.signing_key,
    )
    return token.decode()


def auth(sub: str, role: str = "customer") -> dict:
    return {"Authorization": f"Bearer {bearer(sub, role)}"}


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["currency"] == settings.currency


def test_charge_creates_invoice():
    r = client.post("/charge", json={"amount": 500, "description": "api usage"},
                    headers=auth("alice"))
    assert r.status_code == 201
    body = r.json()
    assert body["customer_id"] == "alice"
    assert body["customer_name"] == "Alice Martin"
    assert body["amount"] == 500
    assert body["status"] == "paid"


def test_charge_requires_auth():
    r = client.post("/charge", json={"amount": 100})
    assert r.status_code == 401


def test_charge_rejects_garbage_token():
    r = client.post("/charge", json={"amount": 100},
                    headers={"Authorization": "Bearer not-a-real-token"})
    assert r.status_code == 401


def test_charge_rejects_unknown_customer():
    r = client.post("/charge", json={"amount": 100}, headers=auth("nobody"))
    assert r.status_code == 401


def test_charge_validates_amount():
    r = client.post("/charge", json={"amount": 0}, headers=auth("bob"))
    assert r.status_code == 422


def test_invoices_are_scoped_to_customer():
    client.post("/charge", json={"amount": 10}, headers=auth("alice"))
    client.post("/charge", json={"amount": 20}, headers=auth("bob"))

    alice = client.get("/invoices", headers=auth("alice"))
    assert alice.status_code == 200
    assert all(i["customer_id"] == "alice" for i in alice.json())
    assert len(alice.json()) >= 1


def test_get_other_customers_invoice_is_404():
    created = client.post("/charge", json={"amount": 42}, headers=auth("alice")).json()
    r = client.get(f"/invoices/{created['id']}", headers=auth("bob"))
    assert r.status_code == 404


def test_balance_totals_charges():
    sub = "bob"
    before = client.get("/balance", headers=auth(sub)).json()["total"]
    client.post("/charge", json={"amount": 70}, headers=auth(sub))
    after = client.get("/balance", headers=auth(sub)).json()
    assert after["total"] == before + 70
    assert after["currency"] == settings.currency
