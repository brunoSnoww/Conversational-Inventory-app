from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Protocol
from uuid import UUID

from app.constants import VALID_PRODUCT_UNITS

from .exceptions import InsufficientStock, InvalidUnit, InventoryError


class Order(Protocol):
    """Shared shape for purchase and sales orders."""

    user_id: int
    product_id: int
    quantity: Decimal


@dataclass(frozen=True)
class ProductDependents:
    movements: int = 0
    purchases: int = 0
    sales: int = 0

    def has_history(self) -> bool:
        return bool(self.movements or self.purchases or self.sales)


@dataclass
class Product:
    user_id: int
    sku: str
    name: str
    unit: str
    id: int | None = None
    description: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @property
    def product_id(self) -> int | None:
        return self.id

    @product_id.setter
    def product_id(self, value: int | None) -> None:
        self.id = value

    def validate_unit(self) -> None:
        if self.unit not in VALID_PRODUCT_UNITS:
            raise InvalidUnit(self.unit)

    def can_be_deleted(self, dependents: ProductDependents) -> bool:
        return not dependents.has_history()

    def assert_can_be_deleted(self, dependents: ProductDependents) -> None:
        if not self.can_be_deleted(dependents):
            raise InventoryError("Cannot delete product with stock history or orders.")


@dataclass
class StockMovement:
    user_id: int
    product_id: int
    quantity_delta: Decimal
    source: str
    id: int | None = None
    source_id: int | None = None
    unit_cost: Decimal | None = None
    created_at: datetime | None = None
    sku: str | None = None

    @property
    def stock_movement_id(self) -> int | None:
        return self.id

    @stock_movement_id.setter
    def stock_movement_id(self, value: int | None) -> None:
        self.id = value

    def is_manual(self) -> bool:
        return self.source == "MANUAL"

    def validate_positive_quantity(self, quantity: Decimal | None = None) -> None:
        qty = self.quantity_delta if quantity is None else quantity
        if qty <= 0:
            raise InventoryError("Quantity must be positive.")

    def assert_manual(self) -> None:
        if not self.is_manual():
            raise InventoryError("Only manual stock movements can be updated.")

    def assert_deletable(self, *, later_movement_count: int, available: Decimal) -> None:
        self.assert_manual()
        if later_movement_count:
            raise InventoryError(
                "Cannot delete movement after subsequent ledger entries exist; append a reversing manual adjustment."
            )
        if available < self.quantity_delta:
            assert self.sku is not None
            raise InsufficientStock(self.sku, self.quantity_delta, available)

    def to_api_dict(self) -> dict[str, Any]:
        return {
            "stock_movement_id": self.id,
            "product_id": self.product_id,
            "quantity_delta": self.quantity_delta,
            "unit_cost": self.unit_cost,
            "source": self.source,
            "source_id": self.source_id,
            "created_at": self.created_at,
            "sku": self.sku,
        }


@dataclass
class PurchaseOrder:
    user_id: int
    product_id: int
    quantity: Decimal
    total_cost: Decimal
    id: int | None = None
    guid: UUID | None = None
    sku: str | None = None
    created_at: datetime | None = None

    @property
    def purchase_order_id(self) -> int | None:
        return self.id

    @purchase_order_id.setter
    def purchase_order_id(self, value: int | None) -> None:
        self.id = value

    def validate(self) -> None:
        if self.quantity <= 0:
            raise InventoryError("Quantity must be positive.")
        if self.total_cost < 0:
            raise InventoryError("Total cost cannot be negative.")

    def unit_cost(self) -> Decimal:
        return self.total_cost / self.quantity

    def quantity_change(self, new_quantity: Decimal) -> Decimal:
        return new_quantity - self.quantity

    def assert_stock_available_for_reduction(
        self, new_quantity: Decimal, available: Decimal
    ) -> None:
        delta = self.quantity_change(new_quantity)
        if delta < 0 and available + delta < 0:
            assert self.sku is not None
            raise InsufficientStock(self.sku, abs(delta), available)

    def assert_stock_available_for_delete(self, available: Decimal) -> None:
        if available < self.quantity:
            assert self.sku is not None
            raise InsufficientStock(self.sku, self.quantity, available)


@dataclass
class SalesOrder:
    user_id: int
    product_id: int
    quantity: Decimal
    unit_price: Decimal
    id: int | None = None
    guid: UUID | None = None
    sku: str | None = None
    created_at: datetime | None = None

    @property
    def sales_order_id(self) -> int | None:
        return self.id

    @sales_order_id.setter
    def sales_order_id(self, value: int | None) -> None:
        self.id = value

    def validate(self) -> None:
        if self.quantity <= 0:
            raise InventoryError("Quantity must be positive.")
        if self.unit_price < 0:
            raise InventoryError("Unit price cannot be negative.")

    def revenue(self) -> Decimal:
        return self.quantity * self.unit_price

    def extra_quantity_sold(self, new_quantity: Decimal) -> Decimal:
        return new_quantity - self.quantity

    def assert_stock_available(self, available: Decimal) -> None:
        if self.quantity > available:
            assert self.sku is not None
            raise InsufficientStock(self.sku, self.quantity, available)

    def assert_stock_available_for_increase(
        self, new_quantity: Decimal, available: Decimal
    ) -> None:
        extra = self.extra_quantity_sold(new_quantity)
        if extra > 0 and extra > available:
            assert self.sku is not None
            raise InsufficientStock(self.sku, extra, available)
