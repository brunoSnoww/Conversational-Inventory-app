from __future__ import annotations

from decimal import Decimal
from typing import Any

from services.database import Database
from domain.models import StockMovement

_APPEND = """
INSERT INTO stock_movement (user_id, product_id, quantity_delta, unit_cost, source, source_id)
VALUES (%s, %s, %s, %s, %s::stock_movement_source, %s)
RETURNING stock_movement_id, product_id, quantity_delta, unit_cost, source, source_id, created_at;
"""
_GET_BY_ID = """
SELECT sm.stock_movement_id, sm.product_id, sm.quantity_delta, sm.unit_cost, sm.source, sm.source_id, sm.created_at, p.sku
FROM stock_movement sm
JOIN product p ON p.product_id = sm.product_id AND p.user_id = sm.user_id
WHERE sm.user_id = %s AND sm.stock_movement_id = %s;
"""
_LIST_ALL = """
SELECT sm.stock_movement_id, sm.product_id, p.sku, sm.quantity_delta,
       sm.unit_cost, sm.source, sm.source_id, sm.created_at
FROM stock_movement sm
JOIN product p ON p.product_id = sm.product_id AND p.user_id = sm.user_id
WHERE sm.user_id = %s ORDER BY sm.stock_movement_id DESC;
"""
_LIST_FOR_PRODUCT = """
SELECT sm.stock_movement_id, sm.product_id, p.sku, sm.quantity_delta,
       sm.unit_cost, sm.source, sm.source_id, sm.created_at
FROM stock_movement sm
JOIN product p ON p.product_id = sm.product_id AND p.user_id = sm.user_id
WHERE sm.user_id = %s AND sm.product_id = %s ORDER BY sm.stock_movement_id DESC;
"""
_COUNT_LATER_THAN = """
SELECT COUNT(*) AS cnt FROM stock_movement
WHERE user_id = %s AND product_id = %s AND stock_movement_id > %s;
"""


def _from_row(row: dict[str, Any], *, user_id: int | None = None) -> StockMovement:
    return StockMovement(
        id=int(row["stock_movement_id"]),
        user_id=user_id if user_id is not None else 0,
        product_id=int(row["product_id"]),
        quantity_delta=row["quantity_delta"],
        unit_cost=row.get("unit_cost"),
        source=row["source"],
        source_id=row.get("source_id"),
        created_at=row.get("created_at"),
        sku=row.get("sku"),
    )


class StockMovementRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def append(
        self,
        user_id: int,
        product_id: int,
        *,
        quantity_delta: Decimal,
        source: str,
        source_id: int | None = None,
        unit_cost: Decimal | None = None,
    ) -> StockMovement:
        row = self._db.fetch_one(
            _APPEND,
            [user_id, product_id, quantity_delta, unit_cost, source, source_id],
        )
        assert row is not None
        return _from_row(row, user_id=user_id)

    def get_by_id(self, user_id: int, stock_movement_id: int) -> StockMovement | None:
        row = self._db.fetch_one(_GET_BY_ID, [user_id, stock_movement_id])
        return None if row is None else _from_row(row, user_id=user_id)

    def list_by_user(self, user_id: int, *, product_id: int | None = None) -> list[StockMovement]:
        if product_id is not None:
            rows = self._db.fetch_all(_LIST_FOR_PRODUCT, [user_id, product_id])
        else:
            rows = self._db.fetch_all(_LIST_ALL, [user_id])
        return [_from_row(r, user_id=user_id) for r in rows]

    def count_later_than(self, user_id: int, product_id: int, stock_movement_id: int) -> int:
        row = self._db.fetch_one(_COUNT_LATER_THAN, [user_id, product_id, stock_movement_id])
        assert row is not None
        return int(row["cnt"])

    def stock_for(self, user_id: int, product_id: int) -> Decimal:
        from inventory_api.models import ProductStockView

        row = ProductStockView.objects.filter(user_id=user_id, product_id=product_id).first()
        return Decimal("0") if row is None else row.quantity_on_hand

    def list_stock_levels(self, user_id: int):
        from inventory_api.models import ProductStockView

        return ProductStockView.objects.filter(user_id=user_id).order_by("sku")
