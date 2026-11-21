"""Runtime configuration, read from the environment with development defaults.

Every setting has a default that is safe to run locally. Anything that looks
like a secret (the token signing key) MUST be overridden in production via the
matching environment variable.
"""
import os


class Settings:
    """Process-wide settings loaded once at import time."""

    def __init__(self) -> None:
        # Shared key used to verify the HMAC signature on bearer tokens.
        # The default is an obvious placeholder; set BILLING_SIGNING_KEY in prod.
        self.signing_key: bytes = os.environ.get(
            "BILLING_SIGNING_KEY", "dev-only-change-me"
        ).encode()

        # ISO 4217 currency used for charges and invoices.
        self.currency: str = os.environ.get("BILLING_CURRENCY", "GBP")

        # Reject charges above this many minor units (pennies) as a guardrail.
        self.max_charge_minor: int = int(
            os.environ.get("BILLING_MAX_CHARGE_MINOR", "1000000")
        )

        # Human-readable name shown on the health endpoint.
        self.service_name: str = os.environ.get("BILLING_SERVICE_NAME", "billing-api")


settings = Settings()
