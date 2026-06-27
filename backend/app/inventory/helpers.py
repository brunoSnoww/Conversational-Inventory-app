from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from decimal import Decimal
from typing import Any, TypeVar

from fastapi import HTTPException, status

from app.constants import ProductUnit
from services import inventory as svc

T = TypeVar("T")


def format_margin_percent(profit: Decimal, total_cost: Decimal) -> str | None:
    if total_cost == 0:
        return None
    return f"{(profit / total_cost) * 100:.2f}"


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.isoformat() + "Z"
    return value.isoformat().replace("+00:00", "Z")


def serialize_financial_row(row: Any) -> dict[str, Any]:
    profit = Decimal(str(row.profit))
    total_cost = Decimal(str(row.total_cost))
    return {
        "product_id": int(row.product_id),
        "sku": row.sku,
        "name": row.name,
        "unit": row.unit,
        "quantity_on_hand": str(row.quantity_on_hand),
        "total_qty_purchased": str(row.total_qty_purchased),
        "total_qty_sold": str(row.total_qty_sold),
        "total_cost": str(row.total_cost),
        "total_revenue": str(row.total_revenue),
        "profit": str(row.profit),
        "margin_percent": format_margin_percent(profit, total_cost),
    }


def serialize_product(row: dict[str, Any], aggregate: Any | None) -> dict[str, Any]:
    return {
        "product_id": int(row["product_id"]),
        "name": row["name"],
        "description": row.get("description") or "",
        "sku": row["sku"],
        "unit": row["unit"],
        "created_at": _iso(row.get("created_at")),
        "updated_at": _iso(row.get("updated_at")),
        "quantity_on_hand": str(aggregate.quantity_on_hand) if aggregate else "0",
        "total_qty_purchased": str(aggregate.total_qty_purchased) if aggregate else "0",
        "total_qty_sold": str(aggregate.total_qty_sold) if aggregate else "0",
        "total_cost": str(aggregate.total_cost) if aggregate else "0.00",
        "total_revenue": str(aggregate.total_revenue) if aggregate else "0.00",
        "profit": str(aggregate.profit) if aggregate else "0.00",
        "margin_percent": (
            format_margin_percent(
                Decimal(str(aggregate.profit)),
                Decimal(str(aggregate.total_cost)),
            )
            if aggregate
            else None
        ),
    }


def serialize_purchase_order(row: dict[str, Any], *, remaining_stock: str | None = None) -> dict[str, Any]:
    body = {
        "purchase_order_id": int(row["purchase_order_id"]),
        "product_id": int(row["product_id"]),
        "quantity": str(row["quantity"]),
        "total_cost": str(row["total_cost"]),
        "guid": str(row["guid"]),
        "created_at": _iso(row.get("created_at")),
    }
    if remaining_stock is not None:
        body["remaining_stock"] = remaining_stock
    return body


def serialize_sales_order(row: dict[str, Any], *, revenue: str | None = None, remaining_stock: str | None = None) -> dict[str, Any]:
    body = {
        "sales_order_id": int(row["sales_order_id"]),
        "product_id": int(row["product_id"]),
        "quantity": str(row["quantity"]),
        "unit_price": str(row["unit_price"]),
        "guid": str(row["guid"]),
        "created_at": _iso(row.get("created_at")),
    }
    if revenue is not None:
        body["revenue"] = revenue
    if remaining_stock is not None:
        body["remaining_stock"] = remaining_stock
    return body


def serialize_stock(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "product_id": int(row["product_id"]),
        "sku": row["sku"],
        "name": row["name"],
        "unit": row["unit"],
        "quantity_on_hand": str(row["quantity_on_hand"]),
    }


def serialize_stock_movement(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "stock_movement_id": int(row["stock_movement_id"]),
        "product_id": int(row["product_id"]),
        "sku": row.get("sku", ""),
        "quantity_delta": str(row["quantity_delta"]),
        "unit_cost": None if row.get("unit_cost") is None else str(row["unit_cost"]),
        "source": row["source"],
        "source_id": row.get("source_id"),
        "created_at": _iso(row.get("created_at")),
    }


def empty_patch_response() -> None:
    raise HTTPException(status_code=400, detail="At least one field required.")


def run_inventory(action: Callable[[], T]) -> T:
    try:
        return action()
    except svc.OrderNotFound as exc:
        raise HTTPException(status_code=404) from exc
    except svc.UnknownProduct as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (svc.InvalidUnit, svc.InsufficientStock, svc.InventoryError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
