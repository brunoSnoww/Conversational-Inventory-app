from __future__ import annotations

from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from .conftest import requires_db

API = "/api"


def _register(client: APIClient, email: str, password: str = "password123") -> dict:
    resp = client.post(f"{API}/auth/register/", {"email": email, "password": password}, format="json")
    assert resp.status_code == 201, resp.content
    return resp.json()


def _auth(client: APIClient, email: str, password: str = "password123") -> APIClient:
    data = _register(client, email, password)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {data['access']}")
    return client


@requires_db
@pytest.mark.django_db
def test_auth_required():
    client = APIClient()
    resp = client.get(f"{API}/products/")
    assert resp.status_code == 401


@requires_db
@pytest.mark.django_db
def test_product_crud():
    client = _auth(APIClient(), "crud-products@inventory.local")

    created = client.post(
        f"{API}/products/",
        {"name": "API Tea", "sku": "API-TEA", "unit": "kg", "description": "bulk"},
        format="json",
    )
    assert created.status_code == 201
    product_id = created.json()["product_id"]

    listed = client.get(f"{API}/products/")
    assert listed.status_code == 200
    assert any(p["sku"] == "API-TEA" for p in listed.json())

    updated = client.patch(
        f"{API}/products/{product_id}/",
        {"description": "updated"},
        format="json",
    )
    assert updated.status_code == 200
    assert updated.json()["description"] == "updated"

    deleted = client.delete(f"{API}/products/{product_id}/")
    assert deleted.status_code == 204


@requires_db
@pytest.mark.django_db
def test_example_scenario_via_api():
    client = _auth(APIClient(), "scenario@inventory.local")

    created = client.post(
        f"{API}/products/",
        {"name": "Product A", "sku": "A", "unit": "unit", "description": "scenario"},
        format="json",
    )
    assert created.status_code == 201
    assert Decimal(created.json()["quantity_on_hand"]) == Decimal("0")

    po = client.post(
        f"{API}/purchase-orders/",
        {"sku": "A", "quantity": "100", "total_cost": "100.00"},
        format="json",
    )
    assert po.status_code == 201

    stock = client.get(f"{API}/stock/")
    assert stock.status_code == 200
    row = next(s for s in stock.json() if s["sku"] == "A")
    assert Decimal(row["quantity_on_hand"]) == Decimal("100")

    sale = client.post(
        f"{API}/sales-orders/",
        {"sku": "A", "quantity": "100", "unit_price": "10.00"},
        format="json",
    )
    assert sale.status_code == 201

    products = client.get(f"{API}/products/")
    assert products.status_code == 200
    product_row = next(p for p in products.json() if p["sku"] == "A")
    assert Decimal(product_row["quantity_on_hand"]) == Decimal("0")
    assert Decimal(product_row["total_qty_purchased"]) == Decimal("100")
    assert Decimal(product_row["total_qty_sold"]) == Decimal("100")
    assert Decimal(product_row["profit"]) == Decimal("900.00")

    fin = client.get(f"{API}/financials/A/")
    assert fin.status_code == 200
    body = fin.json()
    assert Decimal(body["quantity_on_hand"]) == Decimal("0")
    assert Decimal(body["total_qty_purchased"]) == Decimal("100")
    assert Decimal(body["total_qty_sold"]) == Decimal("100")
    assert Decimal(body["total_cost"]) == Decimal("100.00")
    assert Decimal(body["total_revenue"]) == Decimal("1000.00")
    assert Decimal(body["profit"]) == Decimal("900.00")
    assert body["margin_percent"] == "900.00"


@requires_db
@pytest.mark.django_db
def test_user_isolation_api():
    client_a = _auth(APIClient(), "user-a@inventory.local")
    client_b = _auth(APIClient(), "user-b@inventory.local")

    client_a.post(
        f"{API}/products/",
        {"name": "Secret", "sku": "SECRET", "unit": "unit"},
        format="json",
    )

    resp = client_b.get(f"{API}/products/")
    assert resp.status_code == 200
    assert not any(p["sku"] == "SECRET" for p in resp.json())


@requires_db
@pytest.mark.django_db
def test_purchase_order_update_appends_compensating_movement():
    client = _auth(APIClient(), "po-ledger@inventory.local")
    client.post(
        f"{API}/products/",
        {"name": "Ledger PO", "sku": "L-PO", "unit": "unit"},
        format="json",
    )
    po = client.post(
        f"{API}/purchase-orders/",
        {"sku": "L-PO", "quantity": "10", "total_cost": "50.00"},
        format="json",
    )
    po_id = po.json()["purchase_order_id"]
    product_id = po.json()["product_id"]

    before = client.get(f"{API}/stock-movements/?product_id={product_id}")
    count_before = len(before.json())

    updated = client.patch(
        f"{API}/purchase-orders/{po_id}/",
        {"quantity": "8"},
        format="json",
    )
    assert updated.status_code == 200

    after = client.get(f"{API}/stock-movements/")
    assert len(after.json()) == count_before + 1

    stock = client.get(f"{API}/stock/")
    row = next(s for s in stock.json() if s["sku"] == "L-PO")
    assert Decimal(row["quantity_on_hand"]) == Decimal("8")


@requires_db
@pytest.mark.django_db
def test_stock_movements_reject_invalid_product_id():
    client = _auth(APIClient(), "bad-pid@inventory.local")
    resp = client.get(f"{API}/stock-movements/?product_id=not-an-id")
    assert resp.status_code == 400
    assert resp.json()["detail"] == "product_id must be an integer."
