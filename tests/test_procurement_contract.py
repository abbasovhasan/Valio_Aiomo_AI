"""Public contract checks use actual gateway responses and isolated simulation."""

import copy
from datetime import date, timedelta

import pytest
from fastapi import FastAPI
from fastapi.exceptions import ResponseValidationError
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend import procurement
from backend.config import BUYER, CUSTOMER
from backend.procurement_contract import (
    ProcurementSessionResponse,
    ReceiptVerificationResponse,
)
from backend.store import Store


@pytest.fixture
def contract_cart(tmp_path, monkeypatch):
    # Supplier metadata is authored for this isolated test; the actual parser,
    # normalizer, quotation, public serializer and simulator remain in the path.
    product = {
        "id": "contract-spaghetti",
        "baseUnit": "ST",
        "salesUnit": "BAG",
        "allowedLotSize": 1,
        "units": [{"unitId": "BAG", "sizeInBaseUnits": 1}],
        "synkkaData": {
            "brand": "Contract Test",
            "names": [{"language": "en", "value": "Spaghetti"}],
            "classifications": [],
            "unitConversions": [{
                "synkkaPackagingType": "BASE_UNIT_OR_EACH",
                "netWeight": {"unit": "KGM", "value": 5},
            }],
        },
    }
    monkeypatch.setattr(procurement.catalog, "load_catalog", lambda: {product["id"]: product})
    app = FastAPI()
    store = Store(tmp_path / "response-contract.sqlite", postgres=False)
    store.migrate_workspace_authority()

    def buyer():
        return {
            "role": "buyer", "name": "Contract test buyer",
            "buyer_id": BUYER, "customer_id": CUSTOMER, "actor_id": "contract-buyer", "principal_id": "access_code:buyer",
        }

    def approver():
        return buyer() | {"role": "approver", "name": "Contract test manager", "actor_id": "contract-manager", "principal_id": "access_code:approver"}

    procurement.register_routes(app, store, buyer, approver, buyer, lambda *args: None)
    client = TestClient(app)
    delivery = (date.today() + timedelta(days=2)).isoformat()
    response = client.post(procurement.PREFIX, json={
        "message": f"I need 6 kg of spaghetti by {delivery}. Choose the cheapest suitable product.",
        "mode": "fixture", "use_model": False,
    })
    assert response.status_code == 200, response.text
    return client, store, response.json(), app


def test_actual_cart_and_receipt_follow_public_schema(contract_cart):
    client, store, cart, _ = contract_cart
    parsed = ProcurementSessionResponse.model_validate(cart)
    assert parsed.order_status == "READY_TO_ORDER"
    assert parsed.lines[0].quantity == "6"
    assert parsed.cart.items[0].quantity_sales_units == "2"
    assert parsed.cart.total is None and parsed.cart.unknown_charges
    assert parsed.cart.items[0].quantity_breakdown[0].surplus_quantity == "4"
    assert store.spent() == 0

    response = client.post(procurement.PREFIX + "/" + cart["id"] + "/confirm", json={
        "fingerprint": cart["offer"]["fingerprint"],
    }, headers={"Idempotency-Key": "response-contract-commit"})
    assert response.status_code == 200, response.text
    confirmed = ProcurementSessionResponse.model_validate(response.json())
    assert confirmed.order_status == "SIMULATED_ORDER_CONFIRMED"
    assert confirmed.receipt.simulated is True
    assert confirmed.receipt.items[0].id == "contract-spaghetti"
    assert confirmed.receipt.total == confirmed.cart.subtotal
    assert confirmed.receipt.requested_date == cart["constraints"]["delivery_date"]
    verified = client.get(procurement.PREFIX + "/" + cart["id"] + "/verify")
    assert verified.status_code == 200
    verification = ReceiptVerificationResponse.model_validate(verified.json())
    assert verification.integrity_valid and verification.scope_valid and verification.simulated


@pytest.mark.parametrize("location,value", [
    (("cart", "subtotal"), 10.5),
    (("cart", "subtotal"), "NaN"),
    (("cart", "subtotal"), "-1.00"),
    (("cart", "subtotal"), "10.005"),
    (("order_status",), "APPROVED_FOR_REAL_PURCHASE"),
    (("lines", 0, "quantity"), "0"),
    (("lines", 0, "quantity"), "-2"),
    (("lines", 0, "quantity"), "1e999999"),
    (("lines", 0, "quantity"), 6),
    (("lines", 0, "status"), "LOOKS_FINE"),
    (("lines", 0, "candidates", 0, "unit_price"), "Infinity"),
    (("lines", 0, "candidates", 0, "quantity_sales_units"), "-1"),
    (("constraints", "delivery_date"), "2026-13-01"),
])
def test_malformed_public_facts_are_rejected(contract_cart, location, value):
    damaged = copy.deepcopy(contract_cart[2])
    target = damaged
    for key in location[:-1]:
        target = target[key]
    target[location[-1]] = value
    with pytest.raises(ValidationError):
        ProcurementSessionResponse.model_validate(damaged)


def test_ready_status_requires_complete_resolved_basket(contract_cart):
    damaged = copy.deepcopy(contract_cart[2])
    damaged["lines"][0]["selected_product_id"] = None
    with pytest.raises(ValidationError, match="unresolved product"):
        ProcurementSessionResponse.model_validate(damaged)
    damaged = copy.deepcopy(contract_cart[2])
    damaged["cart"]["items"] = []
    with pytest.raises(ValidationError, match="all selected, priced, resolved"):
        ProcurementSessionResponse.model_validate(damaged)


def test_routes_publish_schema_and_reject_invalid_saved_response(contract_cart):
    client, store, cart, app = contract_cart
    schema = client.get("/openapi.json").json()
    for path, method in [
        (procurement.PREFIX, "post"),
        (procurement.PREFIX + "/from-meal-plan", "post"),
        (procurement.PREFIX + "/{id}", "get"),
        (procurement.PREFIX + "/{id}/actions", "post"),
        (procurement.PREFIX + "/{id}/approve", "post"),
        (procurement.PREFIX + "/{id}/confirm", "post"),
    ]:
        response_schema = schema["paths"][path][method]["responses"]["200"]["content"]["application/json"]["schema"]
        assert response_schema["$ref"].endswith("/ProcurementSessionResponse")
    verification_schema = schema["paths"][procurement.PREFIX + "/{id}/verify"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
    assert verification_schema["$ref"].endswith("/ReceiptVerificationResponse")

    saved = store.get("procurement", cart["id"], BUYER)
    saved["cart"]["subtotal"] = 123.45
    store.save("procurement", cart["id"], BUYER, saved)
    with pytest.raises(ResponseValidationError):
        client.get(procurement.PREFIX + "/" + cart["id"])


def test_receipt_verification_cannot_claim_real_order():
    with pytest.raises(ValidationError):
        ReceiptVerificationResponse.model_validate({
            "receipt_id": "fixture", "integrity_valid": True,
            "scope_valid": True, "simulated": False,
            "verification_scope": "Authored test verification",
        })


def test_historical_exact_decimal_notation_reopens_without_mutating_record(contract_cart):
    client, store, cart, app = contract_cart
    saved = store.get("procurement", cart["id"], BUYER)
    candidate = saved["lines"][0]["candidates"][0]
    original = candidate["quantity_sales_units"]
    from decimal import Decimal
    candidate["quantity_sales_units"] = f"{original}E+0"
    store.save("procurement", cart["id"], BUYER, saved)
    response = client.get(procurement.PREFIX + "/" + cart["id"])
    assert response.status_code == 200
    rendered = response.json()["lines"][0]["candidates"][0]["quantity_sales_units"]
    assert "e" not in rendered.casefold() and Decimal(rendered) == Decimal(original)
    assert store.get("procurement", cart["id"], BUYER)["lines"][0]["candidates"][0]["quantity_sales_units"] == f"{original}E+0"
