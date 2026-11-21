# billing-api

A small billing service. It creates charges and lists invoices for an
authenticated customer. State is kept in memory, so a restart clears all
invoices — it is meant as a self-contained reference service, not a ledger of
record.

## Authentication

Every endpoint except `/health` expects an HS256 bearer token:

```
Authorization: Bearer <token>
```

The token's `sub` claim identifies the customer. Tokens are verified with the
shared signing key (see **Settings**). The `current_customer` dependency turns a
valid token into the customer for the request; an unknown subject, a missing
header, or a token that fails verification returns `401`.

## Endpoints

| Method | Path               | Description                                   |
|--------|--------------------|-----------------------------------------------|
| GET    | `/health`          | Liveness probe (no auth).                     |
| POST   | `/charge`          | Create a charge for the current customer.     |
| GET    | `/invoices`        | List the current customer's invoices.         |
| GET    | `/invoices/{id}`   | Fetch one invoice the current customer owns.  |
| GET    | `/balance`         | Total billed to the current customer.         |

`POST /charge` takes a JSON body `{"amount": <minor units>, "description": "..."}`
and returns the created invoice.

## Settings

Configuration is read from environment variables at startup, each with a
development default (see `config.py`):

| Variable                  | Default            | Meaning                              |
|---------------------------|--------------------|--------------------------------------|
| `BILLING_SIGNING_KEY`     | `dev-only-change-me` | Key used to verify bearer tokens.  |
| `BILLING_CURRENCY`        | `GBP`              | Currency for charges and invoices.    |
| `BILLING_MAX_CHARGE_MINOR`| `1000000`         | Upper bound on a single charge.       |
| `BILLING_SERVICE_NAME`    | `billing-api`     | Name reported by `/health`.           |

Set `BILLING_SIGNING_KEY` to a real secret before deploying.

## Running

```sh
pip install -r requirements.txt
uvicorn billing_api.app:app --reload   # from the src/ directory, or set PYTHONPATH=src
```

## Tests

```sh
python -m pytest tests/ -q
```

The test suite uses FastAPI's `TestClient`, so it needs no running server and no
network access.
