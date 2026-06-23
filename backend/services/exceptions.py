"""Re-export domain exceptions for backward compatibility."""

from domain.exceptions import (
    InsufficientStock,
    InvalidUnit,
    InventoryError,
    OrderNotFound,
    UnknownProduct,
)

__all__ = [
    "InsufficientStock",
    "InvalidUnit",
    "InventoryError",
    "OrderNotFound",
    "UnknownProduct",
]
