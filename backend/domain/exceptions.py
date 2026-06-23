from __future__ import annotations

from decimal import Decimal


class InventoryError(Exception):
    pass


class UnknownProduct(InventoryError):
    def __init__(self, sku: str) -> None:
        self.sku = sku
        super().__init__(f"No product found with SKU '{sku}'.")


class InvalidUnit(InventoryError):
    def __init__(self, unit: str) -> None:
        from inventory_api.constants import product_units_label

        self.unit = unit
        super().__init__(f"Invalid unit '{unit}'. Must be one of: {product_units_label()}.")


class InsufficientStock(InventoryError):
    def __init__(self, sku: str, requested: Decimal, available: Decimal) -> None:
        self.sku = sku
        self.requested = requested
        self.available = available
        super().__init__(f"Insufficient stock for '{sku}': requested {requested}, available {available}.")


class OrderNotFound(InventoryError):
    def __init__(self, order_type: str, order_id: int) -> None:
        self.order_id = order_id
        super().__init__(f"{order_type} {order_id} not found.")
