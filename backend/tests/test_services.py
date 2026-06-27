from __future__ import annotations

from decimal import Decimal

import pytest

from services import inventory as svc
from services.db import fetch_one

from .conftest import requires_db


def _demo_user_id() -> int:
    row = fetch_one(
        "SELECT user_id FROM app_user WHERE email = %s",
        ["demo@inventory.local"],
    )
    assert row is not None
    return int(row["user_id"])


def _other_user_id() -> int | None:
    row = fetch_one(
        "SELECT user_id FROM app_user WHERE email <> %s LIMIT 1",
        ["demo@inventory.local"],
    )
    return None if row is None else int(row["user_id"])


@requires_db
def test_demo_product_a_stock():
    user_id = _demo_user_id()
    rows = svc.query_stock_sync(user_id, sku="A")
    assert len(rows) == 1
    assert rows[0].sku == "A"
    assert rows[0].quantity_on_hand == Decimal("0")


@requires_db
def test_demo_product_a_profit():
    user_id = _demo_user_id()
    profit = svc.get_profit_sync(user_id, sku="A")
    assert profit.profit == Decimal("900.00")
    assert profit.total_cost == Decimal("100.00")
    assert profit.total_revenue == Decimal("1000.00")


@requires_db
def test_user_isolation_unknown_sku():
    other_id = _other_user_id()
    if other_id is None:
        pytest.skip("only demo user seeded")
    with pytest.raises(svc.UnknownProduct):
        svc.get_profit_sync(other_id, sku="A")


@requires_db
def test_register_and_delete_product():
    user_id = _demo_user_id()
    created = svc.register_product_sync(
        user_id,
        name="Temp",
        sku="TEMP-DELETE-ME",
        unit="unit",
    )
    svc.delete_product_sync(user_id, created.product_id)


@requires_db
def test_purchase_order_crud_with_stock_sync():
    user_id = _demo_user_id()
    product = svc.register_product_sync(
        user_id, name="CRUD PO", sku="CRUD-PO-1", unit="unit"
    )
    po = svc.create_purchase_order_sync(
        user_id, sku="CRUD-PO-1", quantity=Decimal("10"), total_cost=Decimal("50")
    )
    assert svc.query_stock_sync(user_id, sku="CRUD-PO-1")[0].quantity_on_hand == Decimal("10")

    movements_before = len(svc.list_stock_movements_sync(user_id, product_id=product.product_id))
    updated = svc.update_purchase_order_sync(
        user_id, po.purchase_order_id, quantity=Decimal("8"), total_cost=Decimal("40")
    )
    assert updated.quantity == Decimal("8")
    assert svc.query_stock_sync(user_id, sku="CRUD-PO-1")[0].quantity_on_hand == Decimal("8")
    assert len(svc.list_stock_movements_sync(user_id, product_id=product.product_id)) == movements_before + 1

    svc.delete_purchase_order_sync(user_id, po.purchase_order_id)
    assert svc.query_stock_sync(user_id, sku="CRUD-PO-1")[0].quantity_on_hand == Decimal("0")


@requires_db
def test_sales_order_crud_with_stock_sync():
    user_id = _demo_user_id()
    product = svc.register_product_sync(
        user_id, name="CRUD SO", sku="CRUD-SO-1", unit="unit"
    )
    svc.create_purchase_order_sync(
        user_id, sku="CRUD-SO-1", quantity=Decimal("20"), total_cost=Decimal("20")
    )
    so = svc.record_sale_sync(
        user_id, sku="CRUD-SO-1", quantity=Decimal("5"), unit_price=Decimal("3")
    )
    assert svc.query_stock_sync(user_id, sku="CRUD-SO-1")[0].quantity_on_hand == Decimal("15")

    updated = svc.update_sales_order_sync(
        user_id, so.sales_order_id, quantity=Decimal("4")
    )
    assert updated.quantity == Decimal("4")
    assert svc.query_stock_sync(user_id, sku="CRUD-SO-1")[0].quantity_on_hand == Decimal("16")

    svc.delete_sales_order_sync(user_id, so.sales_order_id)
    assert svc.query_stock_sync(user_id, sku="CRUD-SO-1")[0].quantity_on_hand == Decimal("20")

    po_row = fetch_one(
        """
        SELECT purchase_order_id FROM purchase_order
        WHERE user_id = %s AND product_id = %s
        ORDER BY purchase_order_id DESC LIMIT 1
        """,
        [user_id, product.product_id],
    )
    assert po_row is not None
    svc.delete_purchase_order_sync(user_id, int(po_row["purchase_order_id"]))


@requires_db
def test_manual_stock_movement_compensating_ledger():
    user_id = _demo_user_id()
    product = svc.register_product_sync(
        user_id, name="CRUD Stock", sku="CRUD-STK-1", unit="unit"
    )
    row = svc.create_manual_stock_movement_sync(
        user_id, sku="CRUD-STK-1", quantity=Decimal("12"), unit_cost=Decimal("1.50")
    )
    assert svc.query_stock_sync(user_id, sku="CRUD-STK-1")[0].quantity_on_hand == Decimal("12")

    svc.update_manual_stock_movement_sync(
        user_id, int(row["stock_movement_id"]), quantity=Decimal("10")
    )
    assert svc.query_stock_sync(user_id, sku="CRUD-STK-1")[0].quantity_on_hand == Decimal("10")
    assert len(svc.list_stock_movements_sync(user_id, product_id=product.product_id)) == 2

    with pytest.raises(svc.InventoryError):
        svc.delete_manual_stock_movement_sync(user_id, int(row["stock_movement_id"]))


@requires_db
def test_cannot_delete_product_with_history():
    user_id = _demo_user_id()
    from services.inventory import get_product_by_sku

    row = get_product_by_sku(user_id, "A")
    with pytest.raises(svc.InventoryError):
        svc.delete_product_sync(user_id, int(row["product_id"]))
