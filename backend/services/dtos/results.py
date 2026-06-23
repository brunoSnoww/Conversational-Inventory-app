from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


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
