"""Inventory business logic — ponytail: one module, SQL inlined next to callers."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from django.db import transaction

from inventory_api.constants import VALID_PRODUCT_UNITS
from inventory_api.models import Product, ProductFinancialsView, ProductStockView

from .db import fetch_all, fetch_one
from .exceptions import InsufficientStock, InvalidUnit, InventoryError, OrderNotFound, UnknownProduct

# ponytail: SQL lives here instead of 19 external files + a loader.
_UPSERT_PRODUCT = """
INSERT INTO product (user_id, name, description, sku, unit)
VALUES (%s, %s, %s, %s, %s::product_unit)
ON CONFLICT (user_id, lower(sku))
DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description,
    unit = EXCLUDED.unit, updated_at = now()
RETURNING product_id, sku, name, unit, description;
"""
_GET_PRODUCT_BY_SKU = """
SELECT product_id, user_id, sku, name, unit, description
FROM product WHERE user_id = %s AND lower(sku) = lower(%s);
"""
_GET_PRODUCT_BY_ID = """
SELECT product_id, user_id, sku, name, unit, description
FROM product WHERE user_id = %s AND product_id = %s;
"""
_COUNT_PRODUCT_DEPENDENTS = """
WITH ctx AS (SELECT %s::bigint AS user_id, %s::bigint AS product_id)
SELECT
    (SELECT COUNT(*) FROM stock_movement sm JOIN ctx c ON sm.user_id = c.user_id AND sm.product_id = c.product_id) AS movements,
    (SELECT COUNT(*) FROM purchase_order po JOIN ctx c ON po.user_id = c.user_id AND po.product_id = c.product_id) AS purchases,
    (SELECT COUNT(*) FROM sales_order so JOIN ctx c ON so.user_id = c.user_id AND so.product_id = c.product_id) AS sales;
"""
_DELETE_PRODUCT = "DELETE FROM product WHERE user_id = %s AND product_id = %s RETURNING product_id;"
_APPEND_STOCK_MOVEMENT = """
INSERT INTO stock_movement (user_id, product_id, quantity_delta, unit_cost, source, source_id)
VALUES (%s, %s, %s, %s, %s::stock_movement_source, %s)
RETURNING stock_movement_id, product_id, quantity_delta, unit_cost, source, source_id, created_at;
"""
_GET_STOCK_MOVEMENT_BY_ID = """
SELECT sm.stock_movement_id, sm.product_id, sm.quantity_delta, sm.unit_cost, sm.source, sm.source_id, sm.created_at, p.sku
FROM stock_movement sm
JOIN product p ON p.product_id = sm.product_id AND p.user_id = sm.user_id
WHERE sm.user_id = %s AND sm.stock_movement_id = %s;
"""
_LIST_STOCK_MOVEMENTS_ALL = """
SELECT sm.stock_movement_id, sm.product_id, p.sku, sm.quantity_delta,
       sm.unit_cost, sm.source, sm.source_id, sm.created_at
FROM stock_movement sm
JOIN product p ON p.product_id = sm.product_id AND p.user_id = sm.user_id
WHERE sm.user_id = %s ORDER BY sm.stock_movement_id DESC;
"""
_LIST_STOCK_MOVEMENTS_FOR_PRODUCT = """
SELECT sm.stock_movement_id, sm.product_id, p.sku, sm.quantity_delta,
       sm.unit_cost, sm.source, sm.source_id, sm.created_at
FROM stock_movement sm
JOIN product p ON p.product_id = sm.product_id AND p.user_id = sm.user_id
WHERE sm.user_id = %s AND sm.product_id = %s ORDER BY sm.stock_movement_id DESC;
"""
_INSERT_PURCHASE_ORDER = """
INSERT INTO purchase_order (user_id, product_id, quantity, total_cost, guid)
VALUES (%s, %s, %s, %s, %s) RETURNING purchase_order_id, quantity, total_cost;
"""
_GET_PURCHASE_ORDER_BY_GUID = """
SELECT purchase_order_id, quantity, total_cost FROM purchase_order WHERE user_id = %s AND guid = %s;
"""
_GET_PURCHASE_ORDER_BY_ID = """
SELECT po.purchase_order_id, po.product_id, po.quantity, po.total_cost, p.sku
FROM purchase_order po
JOIN product p ON p.product_id = po.product_id AND p.user_id = po.user_id
WHERE po.user_id = %s AND po.purchase_order_id = %s;
"""
_UPDATE_PURCHASE_ORDER = """
UPDATE purchase_order SET quantity = %s, total_cost = %s
WHERE user_id = %s AND purchase_order_id = %s
RETURNING purchase_order_id, quantity, total_cost;
"""
_DELETE_PURCHASE_ORDER = """
DELETE FROM purchase_order WHERE user_id = %s AND purchase_order_id = %s RETURNING purchase_order_id;
"""
_INSERT_SALES_ORDER = """
INSERT INTO sales_order (user_id, product_id, quantity, unit_price, guid)
VALUES (%s, %s, %s, %s, %s) RETURNING sales_order_id, quantity, unit_price;
"""
_GET_SALES_ORDER_BY_GUID = """
SELECT sales_order_id, quantity, unit_price FROM sales_order WHERE user_id = %s AND guid = %s;
"""
_GET_SALES_ORDER_BY_ID = """
SELECT so.sales_order_id, so.product_id, so.quantity, so.unit_price, p.sku
FROM sales_order so
JOIN product p ON p.product_id = so.product_id AND p.user_id = so.user_id
WHERE so.user_id = %s AND so.sales_order_id = %s;
"""
_UPDATE_SALES_ORDER = """
UPDATE sales_order SET quantity = %s, unit_price = %s
WHERE user_id = %s AND sales_order_id = %s
RETURNING sales_order_id, quantity, unit_price;
"""
_DELETE_SALES_ORDER = """
DELETE FROM sales_order WHERE user_id = %s AND sales_order_id = %s RETURNING sales_order_id;
"""


@dataclass
class ProductResult:
    product_id: int
    sku: str
    name: str
    unit: str
    description: str


@dataclass
class StockResult:
    sku: str
    remaining: Decimal


@dataclass
class StockQueryResult:
    sku: str
    name: str
    unit: str
    quantity_on_hand: Decimal


@dataclass
class PurchaseOrderResult:
    purchase_order_id: int
    sku: str
    quantity: Decimal
    total_cost: Decimal
    unit_cost: Decimal
    remaining: Decimal


@dataclass
class SaleResult:
    sales_order_id: int
    sku: str
    quantity: Decimal
    unit_price: Decimal
    revenue: Decimal
    remaining: Decimal


@dataclass
class ProfitResult:
    sku: str
    name: str
    total_cost: Decimal
    total_revenue: Decimal
    profit: Decimal


def _validate_unit(unit: str) -> None:
    if unit not in VALID_PRODUCT_UNITS:
        raise InvalidUnit(unit)


def get_product_by_sku(user_id: int, sku: str) -> dict:
    row = fetch_one(_GET_PRODUCT_BY_SKU, [user_id, sku])
    if row is None:
        raise UnknownProduct(sku)
    return row


def stock_for(user_id: int, product_id: int) -> Decimal:
    row = ProductStockView.objects.filter(user_id=user_id, product_id=product_id).first()
    return Decimal("0") if row is None else row.quantity_on_hand


def _append_movement(
    user_id: int,
    product_id: int,
    *,
    quantity_delta: Decimal,
    source: str,
    source_id: int | None = None,
    unit_cost: Decimal | None = None,
) -> dict:
    row = fetch_one(
        _APPEND_STOCK_MOVEMENT,
        [user_id, product_id, quantity_delta, unit_cost, source, source_id],
    )
    assert row is not None
    return row


def _compensate_purchase_order(
    user_id: int, product_id: int, purchase_order_id: int, *, quantity_delta: Decimal, unit_cost: Decimal | None
) -> None:
    if quantity_delta == 0:
        return
    _append_movement(
        user_id, product_id, quantity_delta=quantity_delta, source="PURCHASE_ORDER",
        source_id=purchase_order_id, unit_cost=unit_cost,
    )


def _compensate_sales_order(
    user_id: int, product_id: int, sales_order_id: int, *, quantity_delta: Decimal
) -> None:
    if quantity_delta == 0:
        return
    _append_movement(
        user_id, product_id, quantity_delta=quantity_delta, source="SALES_ORDER", source_id=sales_order_id,
    )


def register_product_sync(
    user_id: int, *, name: str, sku: str, unit: str, description: str = ""
) -> ProductResult:
    _validate_unit(unit)
    row = fetch_one(_UPSERT_PRODUCT, [user_id, name, description, sku, unit])
    assert row is not None
    return ProductResult(
        product_id=int(row["product_id"]), sku=row["sku"], name=row["name"],
        unit=row["unit"], description=row["description"],
    )


def update_product_sync(
    user_id: int, product_id: int, *, name: str | None = None, description: str | None = None, unit: str | None = None
) -> ProductResult:
    if unit is not None:
        _validate_unit(unit)
    existing = fetch_one(_GET_PRODUCT_BY_ID, [user_id, product_id])
    if existing is None:
        raise UnknownProduct(str(product_id))

    sets: list[str] = []
    params: list[Any] = []
    if name is not None:
        sets.append("name = %s")
        params.append(name)
    if description is not None:
        sets.append("description = %s")
        params.append(description)
    if unit is not None:
        sets.append("unit = %s::product_unit")
        params.append(unit)

    if not sets:
        return ProductResult(
            product_id=int(existing["product_id"]), sku=existing["sku"], name=existing["name"],
            unit=existing["unit"], description=existing["description"],
        )

    params.extend([user_id, product_id])
    row = fetch_one(
        f"UPDATE product SET {', '.join(sets)} WHERE user_id = %s AND product_id = %s "
        "RETURNING product_id, sku, name, unit, description",
        params,
    )
    assert row is not None
    return ProductResult(
        product_id=int(row["product_id"]), sku=row["sku"], name=row["name"],
        unit=row["unit"], description=row["description"],
    )


@transaction.atomic
def delete_product_sync(user_id: int, product_id: int) -> None:
    existing = fetch_one(_GET_PRODUCT_BY_ID, [user_id, product_id])
    if existing is None:
        raise UnknownProduct(str(product_id))
    dependents = fetch_one(_COUNT_PRODUCT_DEPENDENTS, [user_id, product_id])
    assert dependents is not None
    if dependents["movements"] or dependents["purchases"] or dependents["sales"]:
        raise InventoryError("Cannot delete product with stock history or orders.")
    fetch_one(_DELETE_PRODUCT, [user_id, product_id])


def add_stock_sync(user_id: int, *, sku: str, quantity: Decimal, unit_cost: Decimal | None = None) -> StockResult:
    row = create_manual_stock_movement_sync(user_id, sku=sku, quantity=quantity, unit_cost=unit_cost)
    return StockResult(sku=row["sku"], remaining=stock_for(user_id, int(row["product_id"])))


def query_stock_sync(user_id: int, *, sku: str | None = None) -> list[StockQueryResult]:
    if sku is not None:
        product = get_product_by_sku(user_id, sku)
        pid = int(product["product_id"])
        return [StockQueryResult(
            sku=product["sku"], name=product["name"], unit=product["unit"],
            quantity_on_hand=stock_for(user_id, pid),
        )]
    return [
        StockQueryResult(sku=p.sku, name=p.name, unit=p.unit, quantity_on_hand=stock_for(user_id, int(p.product_id)))
        for p in Product.objects.filter(user_id=user_id).order_by("sku")
    ]


def list_stock_movements_sync(user_id: int, *, product_id: int | None = None) -> list[dict]:
    if product_id is not None:
        return fetch_all(_LIST_STOCK_MOVEMENTS_FOR_PRODUCT, [user_id, product_id])
    return fetch_all(_LIST_STOCK_MOVEMENTS_ALL, [user_id])


def get_stock_movement_sync(user_id: int, stock_movement_id: int) -> dict:
    row = fetch_one(_GET_STOCK_MOVEMENT_BY_ID, [user_id, stock_movement_id])
    if row is None:
        raise InventoryError(f"Stock movement {stock_movement_id} not found.")
    return row


@transaction.atomic
def create_manual_stock_movement_sync(
    user_id: int, *, sku: str, quantity: Decimal, unit_cost: Decimal | None = None
) -> dict:
    if quantity <= 0:
        raise InventoryError("Quantity must be positive.")
    product = get_product_by_sku(user_id, sku)
    row = _append_movement(
        user_id, int(product["product_id"]), quantity_delta=quantity,
        source="MANUAL", source_id=None, unit_cost=unit_cost,
    )
    row["sku"] = product["sku"]
    return row


@transaction.atomic
def update_manual_stock_movement_sync(
    user_id: int, stock_movement_id: int, *, quantity: Decimal | None = None, unit_cost: Decimal | None = None
) -> dict:
    row = get_stock_movement_sync(user_id, stock_movement_id)
    if row["source"] != "MANUAL":
        raise InventoryError("Only manual stock movements can be updated.")

    old_qty = row["quantity_delta"]
    new_qty = quantity if quantity is not None else old_qty
    if new_qty <= 0:
        raise InventoryError("Quantity must be positive.")

    qty_delta_change = new_qty - old_qty
    if qty_delta_change < 0:
        available = stock_for(user_id, int(row["product_id"]))
        if available + qty_delta_change < 0:
            raise InsufficientStock(row["sku"], abs(qty_delta_change), available)

    if qty_delta_change != 0:
        new_row = _append_movement(
            user_id, int(row["product_id"]), quantity_delta=qty_delta_change,
            source="MANUAL", source_id=None, unit_cost=unit_cost,
        )
        new_row["sku"] = row["sku"]
        return new_row
    return row


@transaction.atomic
def delete_manual_stock_movement_sync(user_id: int, stock_movement_id: int) -> None:
    row = get_stock_movement_sync(user_id, stock_movement_id)
    if row["source"] != "MANUAL":
        raise InventoryError("Only manual stock movements can be deleted.")

    later = fetch_one(
        "SELECT COUNT(*) AS cnt FROM stock_movement WHERE user_id = %s AND product_id = %s AND stock_movement_id > %s",
        [user_id, row["product_id"], stock_movement_id],
    )
    assert later is not None
    if later["cnt"]:
        raise InventoryError(
            "Cannot delete movement after subsequent ledger entries exist; append a reversing manual adjustment."
        )

    available = stock_for(user_id, int(row["product_id"]))
    if available < row["quantity_delta"]:
        raise InsufficientStock(row["sku"], row["quantity_delta"], available)

    _append_movement(
        user_id, int(row["product_id"]), quantity_delta=-row["quantity_delta"],
        source="MANUAL", source_id=None, unit_cost=row.get("unit_cost"),
    )


def _purchase_order_row(user_id: int, purchase_order_id: int) -> dict:
    row = fetch_one(_GET_PURCHASE_ORDER_BY_ID, [user_id, purchase_order_id])
    if row is None:
        raise OrderNotFound("Purchase order", purchase_order_id)
    return row


def _sales_order_row(user_id: int, sales_order_id: int) -> dict:
    row = fetch_one(_GET_SALES_ORDER_BY_ID, [user_id, sales_order_id])
    if row is None:
        raise OrderNotFound("Sales order", sales_order_id)
    return row


@transaction.atomic
def create_purchase_order_sync(
    user_id: int, *, sku: str, quantity: Decimal, total_cost: Decimal, guid: uuid.UUID | None = None
) -> PurchaseOrderResult:
    if quantity <= 0:
        raise InventoryError("Quantity must be positive.")
    if total_cost < 0:
        raise InventoryError("Total cost cannot be negative.")

    product = get_product_by_sku(user_id, sku)
    product_id = int(product["product_id"])
    order_guid = guid or uuid.uuid4()
    unit_cost = total_cost / quantity

    existing = fetch_one(_GET_PURCHASE_ORDER_BY_GUID, [user_id, str(order_guid)])
    if existing:
        return PurchaseOrderResult(
            purchase_order_id=int(existing["purchase_order_id"]), sku=product["sku"],
            quantity=existing["quantity"], total_cost=existing["total_cost"],
            unit_cost=existing["total_cost"] / existing["quantity"], remaining=stock_for(user_id, product_id),
        )

    po = fetch_one(_INSERT_PURCHASE_ORDER, [user_id, product_id, quantity, total_cost, str(order_guid)])
    assert po is not None
    _compensate_purchase_order(user_id, product_id, int(po["purchase_order_id"]), quantity_delta=quantity, unit_cost=unit_cost)

    return PurchaseOrderResult(
        purchase_order_id=int(po["purchase_order_id"]), sku=product["sku"], quantity=po["quantity"],
        total_cost=po["total_cost"], unit_cost=unit_cost, remaining=stock_for(user_id, product_id),
    )


@transaction.atomic
def update_purchase_order_sync(
    user_id: int, purchase_order_id: int, *, quantity: Decimal | None = None, total_cost: Decimal | None = None
) -> PurchaseOrderResult:
    po = _purchase_order_row(user_id, purchase_order_id)
    product_id = int(po["product_id"])
    old_qty = po["quantity"]
    new_qty = quantity if quantity is not None else old_qty
    new_cost = total_cost if total_cost is not None else po["total_cost"]

    if new_qty <= 0:
        raise InventoryError("Quantity must be positive.")
    if new_cost < 0:
        raise InventoryError("Total cost cannot be negative.")

    qty_delta_change = new_qty - old_qty
    if qty_delta_change < 0:
        available = stock_for(user_id, product_id)
        if available + qty_delta_change < 0:
            raise InsufficientStock(po["sku"], abs(qty_delta_change), available)

    unit_cost = new_cost / new_qty
    if qty_delta_change != 0:
        _compensate_purchase_order(
            user_id, product_id, purchase_order_id, quantity_delta=qty_delta_change, unit_cost=unit_cost,
        )

    updated = fetch_one(_UPDATE_PURCHASE_ORDER, [new_qty, new_cost, user_id, purchase_order_id])
    assert updated is not None
    return PurchaseOrderResult(
        purchase_order_id=int(updated["purchase_order_id"]), sku=po["sku"], quantity=updated["quantity"],
        total_cost=updated["total_cost"], unit_cost=unit_cost, remaining=stock_for(user_id, product_id),
    )


@transaction.atomic
def delete_purchase_order_sync(user_id: int, purchase_order_id: int) -> None:
    po = _purchase_order_row(user_id, purchase_order_id)
    product_id = int(po["product_id"])
    available = stock_for(user_id, product_id)
    if available < po["quantity"]:
        raise InsufficientStock(po["sku"], po["quantity"], available)
    _compensate_purchase_order(
        user_id, product_id, purchase_order_id,
        quantity_delta=-po["quantity"], unit_cost=po["total_cost"] / po["quantity"],
    )
    fetch_one(_DELETE_PURCHASE_ORDER, [user_id, purchase_order_id])


@transaction.atomic
def record_sale_sync(
    user_id: int, *, sku: str, quantity: Decimal, unit_price: Decimal, guid: uuid.UUID | None = None
) -> SaleResult:
    if quantity <= 0:
        raise InventoryError("Quantity must be positive.")
    if unit_price < 0:
        raise InventoryError("Unit price cannot be negative.")

    product = get_product_by_sku(user_id, sku)
    product_id = int(product["product_id"])
    available = stock_for(user_id, product_id)
    if quantity > available:
        raise InsufficientStock(product["sku"], quantity, available)

    order_guid = guid or uuid.uuid4()
    existing = fetch_one(_GET_SALES_ORDER_BY_GUID, [user_id, str(order_guid)])
    if existing:
        revenue = existing["quantity"] * existing["unit_price"]
        return SaleResult(
            sales_order_id=int(existing["sales_order_id"]), sku=product["sku"], quantity=existing["quantity"],
            unit_price=existing["unit_price"], revenue=revenue, remaining=stock_for(user_id, product_id),
        )

    so = fetch_one(_INSERT_SALES_ORDER, [user_id, product_id, quantity, unit_price, str(order_guid)])
    assert so is not None
    _compensate_sales_order(user_id, product_id, int(so["sales_order_id"]), quantity_delta=-quantity)

    revenue = so["quantity"] * so["unit_price"]
    return SaleResult(
        sales_order_id=int(so["sales_order_id"]), sku=product["sku"], quantity=so["quantity"],
        unit_price=so["unit_price"], revenue=revenue, remaining=stock_for(user_id, product_id),
    )


@transaction.atomic
def update_sales_order_sync(
    user_id: int, sales_order_id: int, *, quantity: Decimal | None = None, unit_price: Decimal | None = None
) -> SaleResult:
    so = _sales_order_row(user_id, sales_order_id)
    product_id = int(so["product_id"])
    old_qty = so["quantity"]
    new_qty = quantity if quantity is not None else old_qty
    new_price = unit_price if unit_price is not None else so["unit_price"]

    if new_qty <= 0:
        raise InventoryError("Quantity must be positive.")
    if new_price < 0:
        raise InventoryError("Unit price cannot be negative.")

    extra_sold = new_qty - old_qty
    if extra_sold > 0:
        available = stock_for(user_id, product_id)
        if extra_sold > available:
            raise InsufficientStock(so["sku"], extra_sold, available)

    if extra_sold != 0:
        _compensate_sales_order(user_id, product_id, sales_order_id, quantity_delta=-extra_sold)

    updated = fetch_one(_UPDATE_SALES_ORDER, [new_qty, new_price, user_id, sales_order_id])
    assert updated is not None
    revenue = updated["quantity"] * updated["unit_price"]
    return SaleResult(
        sales_order_id=int(updated["sales_order_id"]), sku=so["sku"], quantity=updated["quantity"],
        unit_price=updated["unit_price"], revenue=revenue, remaining=stock_for(user_id, product_id),
    )


@transaction.atomic
def delete_sales_order_sync(user_id: int, sales_order_id: int) -> None:
    so = _sales_order_row(user_id, sales_order_id)
    product_id = int(so["product_id"])
    _compensate_sales_order(user_id, product_id, sales_order_id, quantity_delta=so["quantity"])
    fetch_one(_DELETE_SALES_ORDER, [user_id, sales_order_id])


def get_profit_sync(user_id: int, *, sku: str) -> ProfitResult:
    get_product_by_sku(user_id, sku)
    row = ProductFinancialsView.objects.filter(user_id=user_id, sku__iexact=sku).first()
    if row is None:
        raise UnknownProduct(sku)
    return ProfitResult(
        sku=row.sku, name=row.name, total_cost=row.total_cost,
        total_revenue=row.total_revenue, profit=row.profit,
    )
