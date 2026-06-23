"""Backward-compatible facade — delegates to Repository/Service layer."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from services.container import InventoryServices, build_inventory_services
from services.dtos.results import (
    ProductResult,
    ProfitResult,
    PurchaseOrderResult,
    SaleResult,
    StockQueryResult,
    StockResult,
)
from services.exceptions import InsufficientStock, InvalidUnit, InventoryError, OrderNotFound, UnknownProduct

__all__ = [
    "InsufficientStock",
    "InvalidUnit",
    "InventoryError",
    "OrderNotFound",
    "ProductResult",
    "ProfitResult",
    "PurchaseOrderResult",
    "SaleResult",
    "StockQueryResult",
    "StockResult",
    "UnknownProduct",
    "add_stock_sync",
    "create_manual_stock_movement_sync",
    "create_purchase_order_sync",
    "delete_manual_stock_movement_sync",
    "delete_product_sync",
    "delete_purchase_order_sync",
    "delete_sales_order_sync",
    "get_product_by_sku",
    "get_profit_sync",
    "get_stock_movement_sync",
    "list_stock_movements_sync",
    "query_stock_sync",
    "record_sale_sync",
    "register_product_sync",
    "stock_for",
    "update_manual_stock_movement_sync",
    "update_product_sync",
    "update_purchase_order_sync",
    "update_sales_order_sync",
]

_services: InventoryServices | None = None


def _svc() -> InventoryServices:
    global _services
    if _services is None:
        _services = build_inventory_services()
    return _services


def get_product_by_sku(user_id: int, sku: str) -> dict[str, Any]:
    product = _svc().products.get_by_sku(user_id, sku)
    return {
        "product_id": product.id,
        "user_id": product.user_id,
        "sku": product.sku,
        "name": product.name,
        "unit": product.unit,
        "description": product.description,
    }


def stock_for(user_id: int, product_id: int) -> Decimal:
    return _svc().stock.stock_for(user_id, product_id)


def register_product_sync(
    user_id: int, *, name: str, sku: str, unit: str, description: str = ""
) -> ProductResult:
    return _svc().products.register(user_id, name=name, sku=sku, unit=unit, description=description)


def update_product_sync(
    user_id: int,
    product_id: int,
    *,
    name: str | None = None,
    description: str | None = None,
    unit: str | None = None,
) -> ProductResult:
    return _svc().products.update(
        user_id, product_id, name=name, description=description, unit=unit
    )


def delete_product_sync(user_id: int, product_id: int) -> None:
    _svc().products.delete(user_id, product_id)


def add_stock_sync(
    user_id: int, *, sku: str, quantity: Decimal, unit_cost: Decimal | None = None
) -> StockResult:
    return _svc().stock.add_stock(user_id, sku=sku, quantity=quantity, unit_cost=unit_cost)


def query_stock_sync(user_id: int, *, sku: str | None = None) -> list[StockQueryResult]:
    return _svc().stock.query_stock(user_id, sku=sku)


def list_stock_movements_sync(user_id: int, *, product_id: int | None = None) -> list[dict]:
    return _svc().stock.list_movements(user_id, product_id=product_id)


def get_stock_movement_sync(user_id: int, stock_movement_id: int) -> dict:
    return _svc().stock.get_movement(user_id, stock_movement_id)


def create_manual_stock_movement_sync(
    user_id: int, *, sku: str, quantity: Decimal, unit_cost: Decimal | None = None
) -> dict:
    return _svc().stock.create_manual_movement(
        user_id, sku=sku, quantity=quantity, unit_cost=unit_cost
    )


def update_manual_stock_movement_sync(
    user_id: int,
    stock_movement_id: int,
    *,
    quantity: Decimal | None = None,
    unit_cost: Decimal | None = None,
) -> dict:
    return _svc().stock.update_manual_movement(
        user_id, stock_movement_id, quantity=quantity, unit_cost=unit_cost
    )


def delete_manual_stock_movement_sync(user_id: int, stock_movement_id: int) -> None:
    _svc().stock.delete_manual_movement(user_id, stock_movement_id)


def create_purchase_order_sync(
    user_id: int,
    *,
    sku: str,
    quantity: Decimal,
    total_cost: Decimal,
    guid: uuid.UUID | None = None,
) -> PurchaseOrderResult:
    return _svc().purchase_orders.create(
        user_id, sku=sku, quantity=quantity, total_cost=total_cost, guid=guid
    )


def update_purchase_order_sync(
    user_id: int,
    purchase_order_id: int,
    *,
    quantity: Decimal | None = None,
    total_cost: Decimal | None = None,
) -> PurchaseOrderResult:
    return _svc().purchase_orders.update(
        user_id, purchase_order_id, quantity=quantity, total_cost=total_cost
    )


def delete_purchase_order_sync(user_id: int, purchase_order_id: int) -> None:
    _svc().purchase_orders.delete(user_id, purchase_order_id)


def record_sale_sync(
    user_id: int,
    *,
    sku: str,
    quantity: Decimal,
    unit_price: Decimal,
    guid: uuid.UUID | None = None,
) -> SaleResult:
    return _svc().sales_orders.record_sale(
        user_id, sku=sku, quantity=quantity, unit_price=unit_price, guid=guid
    )


def update_sales_order_sync(
    user_id: int,
    sales_order_id: int,
    *,
    quantity: Decimal | None = None,
    unit_price: Decimal | None = None,
) -> SaleResult:
    return _svc().sales_orders.update(
        user_id, sales_order_id, quantity=quantity, unit_price=unit_price
    )


def delete_sales_order_sync(user_id: int, sales_order_id: int) -> None:
    _svc().sales_orders.delete(user_id, sales_order_id)


def get_profit_sync(user_id: int, *, sku: str) -> ProfitResult:
    return _svc().reporting.get_profit(user_id, sku=sku)
