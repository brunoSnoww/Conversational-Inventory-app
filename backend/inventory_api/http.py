from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from rest_framework import status
from rest_framework.response import Response

from services import inventory as svc

T = TypeVar("T")


def run_inventory(action: Callable[[], T]) -> T | Response:
    """Map domain inventory exceptions to DRF responses."""
    try:
        return action()
    except svc.OrderNotFound:
        return Response(status=status.HTTP_404_NOT_FOUND)
    except svc.UnknownProduct as e:
        return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)
    except (svc.InvalidUnit, svc.InsufficientStock, svc.InventoryError) as e:
        return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


def stock_movement_from_row(user_id: int, row: dict):
    from inventory_api.models import StockMovement

    return StockMovement(
        stock_movement_id=int(row["stock_movement_id"]),
        user_id=user_id,
        product_id=int(row["product_id"]),
        quantity_delta=row["quantity_delta"],
        unit_cost=row.get("unit_cost"),
        source=row["source"],
        source_id=row.get("source_id"),
        created_at=row["created_at"],
    )
