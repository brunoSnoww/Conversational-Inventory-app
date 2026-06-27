from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field

from app.constants import ProductUnit


class ProductWrite(BaseModel):
    name: str = Field(max_length=200)
    sku: str = Field(max_length=64)
    unit: ProductUnit
    description: str = Field(default="", max_length=2000)


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    unit: ProductUnit | None = None


class StockAdd(BaseModel):
    sku: str
    quantity: Decimal
    unit_cost: Decimal | None = None


class PurchaseOrderWrite(BaseModel):
    sku: str
    quantity: Decimal
    total_cost: Decimal


class PurchaseOrderUpdate(BaseModel):
    quantity: Decimal | None = None
    total_cost: Decimal | None = None


class SalesOrderWrite(BaseModel):
    sku: str
    quantity: Decimal
    unit_price: Decimal


class SalesOrderUpdate(BaseModel):
    quantity: Decimal | None = None
    unit_price: Decimal | None = None


class StockMovementWrite(BaseModel):
    sku: str
    quantity: Decimal
    unit_cost: Decimal | None = None


class StockMovementUpdate(BaseModel):
    quantity: Decimal | None = None
    unit_cost: Decimal | None = None
