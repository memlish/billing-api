"""billing-api — charges and invoices for an authenticated customer.

Endpoints
---------
- ``GET  /health``            liveness probe (no auth)
- ``POST /charge``            create a charge for the current customer
- ``GET  /invoices``          list the current customer's invoices
- ``GET  /invoices/{id}``     fetch one invoice the current customer owns
- ``GET  /balance``           total billed to the current customer

Authentication is handled by the :func:`current_customer` dependency, which
resolves the ``Authorization: Bearer`` header into a customer. Handlers never
touch tokens directly.
"""
import itertools
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from . import __version__
from .config import settings
from .security import Customer, current_customer

app = FastAPI(title="billing-api", version=__version__)

# ---------------------------------------------------------------------------
# In-memory data store. Swapped for a real ledger in production.
# ---------------------------------------------------------------------------
_invoice_ids = itertools.count(1001)
_INVOICES: list[dict] = []


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class ChargeRequest(BaseModel):
    """Body of a POST /charge request."""

    amount: int = Field(..., gt=0, description="amount to charge, in minor units")
    description: str = Field("", max_length=140)


class Invoice(BaseModel):
    """A single billed line item owned by one customer."""

    id: int
    customer_id: str
    customer_name: str
    amount: int
    currency: str
    description: str
    created_at: str
    status: str


class Balance(BaseModel):
    """Aggregate of everything billed to a customer."""

    customer_id: str
    currency: str
    invoices: int
    total: int


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/health")
def health() -> dict:
    """Liveness probe. Reports the service name and currency it bills in."""
    return {
        "status": "ok",
        "service": settings.service_name,
        "version": __version__,
        "currency": settings.currency,
    }


@app.post("/charge", response_model=Invoice, status_code=201)
def charge(
    req: ChargeRequest,
    customer: Customer = Depends(current_customer),
) -> Invoice:
    """Create a charge for the authenticated customer and return its invoice."""
    if req.amount > settings.max_charge_minor:
        raise HTTPException(status_code=422, detail="amount exceeds limit")

    record = {
        "id": next(_invoice_ids),
        "customer_id": customer.id,
        "customer_name": customer.name,
        "amount": req.amount,
        "currency": settings.currency,
        "description": req.description,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "paid",
    }
    _INVOICES.append(record)
    return Invoice(**record)


@app.get("/invoices", response_model=list[Invoice])
def list_invoices(
    customer: Customer = Depends(current_customer),
) -> list[Invoice]:
    """List invoices belonging to the authenticated customer, newest first."""
    mine = [i for i in _INVOICES if i["customer_id"] == customer.id]
    return [Invoice(**i) for i in reversed(mine)]


@app.get("/invoices/{invoice_id}", response_model=Invoice)
def get_invoice(
    invoice_id: int,
    customer: Customer = Depends(current_customer),
) -> Invoice:
    """Fetch a single invoice, provided it belongs to the current customer."""
    for i in _INVOICES:
        if i["id"] == invoice_id and i["customer_id"] == customer.id:
            return Invoice(**i)
    raise HTTPException(status_code=404, detail="invoice not found")


@app.get("/balance", response_model=Balance)
def balance(customer: Customer = Depends(current_customer)) -> Balance:
    """Report how much has been billed to the authenticated customer."""
    mine = [i for i in _INVOICES if i["customer_id"] == customer.id]
    return Balance(
        customer_id=customer.id,
        currency=settings.currency,
        invoices=len(mine),
        total=sum(i["amount"] for i in mine),
    )
