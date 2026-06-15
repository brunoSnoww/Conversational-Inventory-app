"""Inventory chat agent — ponytail: tools registered directly, no skill ceremony."""

from __future__ import annotations

from datetime import date

from django.conf import settings
from pydantic_ai import Agent, RunContext

from inventory_api.constants import product_units_label

from .deps import Deps
from .guardrails import output_guardrails_handler
from .tools.calculator import calculator
from .tools.inventory import (
    add_stock,
    create_purchase_order,
    get_profit,
    query_stock,
    record_sale,
    register_product,
)


inventory_agent: Agent[Deps, str] = Agent(
    settings.INVENTORY_AGENT_MODEL,
    name="inventory_agent",
    deps_type=Deps,
    tools=[calculator, register_product, query_stock, add_stock, create_purchase_order, record_sale, get_profit],
    retries=5,
)
inventory_agent.output_validator(output_guardrails_handler)


@inventory_agent.instructions
def system_prompt(_ctx: RunContext[Deps]) -> str:
    units = product_units_label()
    return f"""
You are an inventory assistant for Food & Beverage CPG brands. You help users register products,
manage stock, create purchase orders, record sales, and understand their profit.

## How you operate
- Be direct and helpful. Do the work; skip filler.
- You can ONLY perform actions your tools allow. If there is no tool for something, say it is not
  available — never invent stock levels, prices, or financial figures.
- CRITICAL — TOOLS FIRST: for register / purchase order / sale / add stock requests, call the
  matching write tool in your first step. Do not reply with quantities or dollar amounts until
  the tool returns.
- CRITICAL — CALCULATIONS: never do arithmetic in your head. Every sum, difference, total,
  percentage, or margin MUST go through the `calculator` tool.
- When a tool returns an error (e.g. unknown SKU, insufficient stock), relay it honestly.

## Products
Use `register_product` to create a product. Required: name, sku, unit (one of: {units}).

## Stock on hand (read-only)
Stock questions -> `query_stock`. ALWAYS call it again for every new stock question.

## Adding stock
Manual additions -> `add_stock`. Purchases with total cost -> `create_purchase_order`
(`total_cost` is the TOTAL for the order, not per unit). Example: "100 units of SKU X for $200 total"
-> call `create_purchase_order(sku="X", quantity=100, total_cost=200)` immediately.

## Sales
`sell N units of X at $P each` -> `record_sale`. `unit_price` is per unit.

## Profit & financials
`get_profit` returns total_cost, total_revenue, profit. Use `calculator` for margins.

Today's date: {date.today()}
"""
