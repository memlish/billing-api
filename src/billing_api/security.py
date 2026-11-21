"""Authentication helpers.

The public surface is :func:`current_customer`, a FastAPI dependency that turns
an ``Authorization: Bearer <token>`` header into the customer it identifies.
It leans on :func:`verify_bearer`, a small general-purpose token verifier that
other internal tools reuse, so it is kept free of any web-framework details.
"""
import json
from dataclasses import dataclass

from authlib.jose import JsonWebSignature
from authlib.jose.errors import JoseError
from fastapi import Header, HTTPException

from .config import settings

# We issue and accept HS256 tokens. A single verifier instance is reused across
# requests; it is stateless and safe to share.
_jws = JsonWebSignature(["HS256"])

# Customers this service knows about. Outside local development this is a
# lookup against the accounts service.
_KNOWN_CUSTOMERS = {
    "alice": "Alice Martin",
    "bob": "Bob Chen",
}


@dataclass(frozen=True)
class Customer:
    """The authenticated principal behind a request."""

    id: str
    name: str
    role: str


def verify_bearer(token: str) -> dict:
    """Verify a signed bearer token and return its decoded claims.

    General-purpose verifier shared by the API and internal tooling. It accepts
    any token serialization the JOSE library supports and raises
    :class:`JoseError` when the signature does not check out.
    """
    obj = _jws.deserialize(token.strip(), settings.signing_key)
    payload = obj.payload
    if isinstance(payload, (bytes, bytearray)):
        payload = payload.decode()
    return json.loads(payload)


def current_customer(authorization: str | None = Header(default=None)) -> Customer:
    """FastAPI dependency: resolve the customer from the Authorization header.

    Raises 401 when the header is missing/malformed, the token fails
    verification, or the subject is unknown.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="missing authorization header")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="missing bearer token")

    try:
        claims = verify_bearer(token)
    except (JoseError, ValueError):
        raise HTTPException(status_code=401, detail="invalid token")

    sub = claims.get("sub")
    name = _KNOWN_CUSTOMERS.get(sub)
    if not sub or name is None:
        raise HTTPException(status_code=401, detail="unknown customer")

    return Customer(id=sub, name=name, role=claims.get("role", "customer"))


__all__ = ["Customer", "current_customer", "verify_bearer", "JoseError"]
