"""Server-only configuration. Never serialize settings or credentials."""

import json
import os
import secrets
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
LOCAL = ROOT / ".local"
LOCAL.mkdir(mode=0o700, exist_ok=True)
ACCESS = LOCAL / "access.json"
if not ACCESS.exists():
    ACCESS.write_text(
        json.dumps(
            {"buyer": secrets.token_urlsafe(24), "approver": secrets.token_urlsafe(24)},
            indent=2,
        )
    )
    ACCESS.chmod(0o600)


def access_codes():
    codes = json.loads(ACCESS.read_text())
    return {
        "buyer": os.getenv("AIMO_BUYER_CODE", codes["buyer"]),
        "approver": os.getenv("AIMO_APPROVER_CODE", codes["approver"]),
    }


MODEL = os.getenv("NVIDIA_MODEL", "nvidia/nemotron-3.5-super-vl-120b-a12b")
BUYER = "buyer-hotel-aurora"
CUSTOMER = "hotel-aurora-demo"
APPROVER = "Leena Koski · procurement manager"
MANDATE = {
    "id": "mandate-aurora-v1",
    "buyer_id": BUYER,
    "customer_id": CUSTOMER,
    "name": "Aurora Hotel · breakfast service",
    "approver": APPROVER,
    "autonomous_limit": "1400.00",
    "exception_limit": "2500.00",
    "cumulative_limit": "6000.00",
    "diet": "lactose_free",
    "allowed_products": ["464306", "464398", "465039"],
    "currency": "EUR",
    "tax_basis": "tax inclusive",
    "quantity_rule": "at least",
    "expires_at": "2026-11-30T21:59:59+00:00",
    "authored_example": True,
    "note": "Synthetic hotel mandate. Milk allergy safety is not established; lactose-free milk contains milk.",
}


def spend_limits(environ):
    """Operator-owned per-customer demo policy, fixed for the server lifetime."""
    from decimal import Decimal, InvalidOperation

    defaults = {
        "autonomous_limit": "1400.00",
        "exception_limit": "2500.00",
        "cumulative_limit": "6000.00",
    }
    values = {}
    for key, fallback in defaults.items():
        name = "AIMO_" + key.upper()
        try:
            amount = Decimal(environ.get(name, fallback))
            if (
                not amount.is_finite()
                or amount < 0
                or amount > 1000000
                or amount != amount.quantize(Decimal(".01"))
            ):
                raise ValueError()
        except (InvalidOperation, ValueError):
            raise ValueError(
                f"{name} must be a nonnegative EUR amount with at most two decimals, up to 1000000"
            ) from None
        values[key] = format(amount, ".2f")
    if (
        not Decimal(values["autonomous_limit"])
        <= Decimal(values["exception_limit"])
        <= Decimal(values["cumulative_limit"])
    ):
        raise ValueError(
            "Spend limits must satisfy autonomous <= exception <= cumulative"
        )
    return values


MANDATE.update(spend_limits(os.environ))
MANDATE["policy_configuration"] = (
    "Operator-configured server environment; fixed until restart. Buyer text cannot change authority."
)
MANDATE["commercial_journey"] = {
    "channel": "webshop",
    "account": "Synthetic contracted B2B customer; no real contract or credit check performed.",
    "payment": "Usually invoiced after delivery, according to the worker interview; actual contract terms govern.",
    "simulation": "This app issues a simulated receipt only. It never issues an invoice or takes payment.",
}
