"""Inventory agent tools — ponytail: sync_to_async here (only async consumer)."""

from __future__ import annotations

import uuid
from decimal import Decimal, InvalidOperation
from typing import Literal

from asgiref.sync import sync_to_async
from pydantic_ai import ModelRetry, RunContext

from inventory_api.constants import ProductUnit
from services import inventory as svc

from ..deps import Deps
from ..guardrails import sanitize_user_text
from ..idempotency import tool_guid

ProductUnitLiteral = Literal[
    ProductUnit.KG, ProductUnit.G, ProductUnit.L, ProductUnit.ML, ProductUnit.UNIT,
]

_UNIT_ALIASES: dict[str, str] = {
    "ml": ProductUnit.ML,
    "ML": ProductUnit.ML,
    "l": ProductUnit.L,
    "units": ProductUnit.UNIT,
    "unit": ProductUnit.UNIT,
}


def _normalize_unit(unit: str) -> str:
    stripped = unit.strip()
    return _UNIT_ALIASES.get(stripped, stripped)


def _dec(value: float | str, field: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as e:
        raise ModelRetry(f"'{field}' must be a number, got {value!r}.") from e


async def register_product(
    ctx: RunContext[Deps], name: str, sku: str, unit: ProductUnitLiteral, description: str = ""
) -> str:
    """Register a new product (or update name/description if the SKU exists)."""
    try:
        p = await sync_to_async(svc.register_product_sync)(
            ctx.deps.user_id,
            name=name,
            sku=sku,
            unit=_normalize_unit(unit),
            description=description,
        )
    except svc.InvalidUnit as e:
        return str(e)
    return f"Registered product '{p.name}' (SKU {p.sku}, unit {p.unit})."


async def add_stock(ctx: RunContext[Deps], sku: str, quantity: float, unit_cost: float | None = None) -> str:
    """Manually add stock for a product (not via a purchase order)."""
    try:
        r = await sync_to_async(svc.add_stock_sync)(
            ctx.deps.user_id, sku=sku, quantity=_dec(quantity, "quantity"),
            unit_cost=_dec(unit_cost, "unit_cost") if unit_cost is not None else None,
        )
    except (svc.UnknownProduct, svc.InventoryError) as e:
        return str(e)
    return f"Added {quantity} to {r.sku}. Stock is now {r.remaining}."


async def create_purchase_order(ctx: RunContext[Deps], sku: str, quantity: float, total_cost: float) -> str:
    """Create a purchase order. Increments stock. total_cost is for the whole order."""
    qty = _dec(quantity, "quantity")
    cost = _dec(total_cost, "total_cost")
    order_guid = tool_guid(
        ctx.deps.chat_message_id, "create_purchase_order", sku=sku, quantity=qty, total_cost=cost,
    ) or uuid.uuid4()
    try:
        r = await sync_to_async(svc.create_purchase_order_sync)(
            ctx.deps.user_id, sku=sku, quantity=qty, total_cost=cost, guid=order_guid,
        )
    except (svc.UnknownProduct, svc.InventoryError) as e:
        return str(e)
    return (
        f"Purchase order created: {r.quantity} units of {r.sku} for a total of {r.total_cost} "
        f"(unit cost {r.unit_cost}). Stock is now {r.remaining}."
    )


async def record_sale(ctx: RunContext[Deps], sku: str, quantity: float, unit_price: float) -> str:
    """Record a sale. Decrements stock. unit_price is per unit."""
    qty = _dec(quantity, "quantity")
    price = _dec(unit_price, "unit_price")
    order_guid = tool_guid(
        ctx.deps.chat_message_id, "record_sale", sku=sku, quantity=qty, unit_price=price,
    ) or uuid.uuid4()
    try:
        r = await sync_to_async(svc.record_sale_sync)(
            ctx.deps.user_id, sku=sku, quantity=qty, unit_price=price, guid=order_guid,
        )
    except (svc.UnknownProduct, svc.InsufficientStock, svc.InventoryError) as e:
        return str(e)
    return f"Sale recorded: {r.quantity} units of {r.sku} at {r.unit_price} each. Revenue {r.revenue}. Stock left {r.remaining}."


async def query_stock(ctx: RunContext[Deps], sku: str | None = None) -> str:
    """Query current on-hand stock. Read-only."""
    try:
        rows = await sync_to_async(svc.query_stock_sync)(ctx.deps.user_id, sku=sku)
    except svc.UnknownProduct as e:
        return str(e)
    if not rows:
        return "No products registered yet."
    lines = [
        f"{sanitize_user_text(r.name)} (SKU {r.sku}): {r.quantity_on_hand} {r.unit} on hand"
        for r in rows
    ]
    return "Current stock:\n" + "\n".join(lines)


async def get_profit(ctx: RunContext[Deps], sku: str) -> str:
    """Get revenue, cost, and profit for a product."""
    try:
        r = await sync_to_async(svc.get_profit_sync)(ctx.deps.user_id, sku=sku)
    except svc.UnknownProduct as e:
        return str(e)
    return (
        f"Financials for {r.name} (SKU {r.sku}): "
        f"total_cost={r.total_cost}, total_revenue={r.total_revenue}, profit={r.profit}. "
        f"To report a margin, compute profit/total_cost*100 with the calculator tool."
    )
