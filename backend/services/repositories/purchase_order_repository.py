from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from services.database import Database
from domain.models import PurchaseOrder

_INSERT = """
INSERT INTO purchase_order (user_id, product_id, quantity, total_cost, guid)
VALUES (%s, %s, %s, %s, %s) RETURNING purchase_order_id, quantity, total_cost;
"""
_GET_BY_GUID = """
SELECT purchase_order_id, quantity, total_cost FROM purchase_order WHERE user_id = %s AND guid = %s;
"""
_GET_BY_ID = """
SELECT po.purchase_order_id, po.product_id, po.quantity, po.total_cost, p.sku
FROM purchase_order po
JOIN product p ON p.product_id = po.product_id AND p.user_id = po.user_id
WHERE po.user_id = %s AND po.purchase_order_id = %s;
"""
_UPDATE = """
UPDATE purchase_order SET quantity = %s, total_cost = %s
WHERE user_id = %s AND purchase_order_id = %s
RETURNING purchase_order_id, quantity, total_cost;
"""
_DELETE = """
DELETE FROM purchase_order WHERE user_id = %s AND purchase_order_id = %s RETURNING purchase_order_id;
"""


def _from_row(row: dict[str, Any], *, user_id: int) -> PurchaseOrder:
    return PurchaseOrder(
        id=int(row["purchase_order_id"]),
        user_id=user_id,
        product_id=int(row["product_id"]),
        quantity=row["quantity"],
        total_cost=row["total_cost"],
        sku=row.get("sku"),
    )


class PurchaseOrderRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def get_by_id(self, user_id: int, purchase_order_id: int) -> PurchaseOrder | None:
        row = self._db.fetch_one(_GET_BY_ID, [user_id, purchase_order_id])
        return None if row is None else _from_row(row, user_id=user_id)

    def get_by_guid(self, user_id: int, guid: UUID) -> PurchaseOrder | None:
        row = self._db.fetch_one(_GET_BY_GUID, [user_id, str(guid)])
        if row is None:
            return None
        return PurchaseOrder(
            id=int(row["purchase_order_id"]),
            user_id=user_id,
            product_id=0,
            quantity=row["quantity"],
            total_cost=row["total_cost"],
            guid=guid,
        )

    def save(self, order: PurchaseOrder) -> PurchaseOrder:
        row = self._db.fetch_one(
            _INSERT,
            [
                order.user_id,
                order.product_id,
                order.quantity,
                order.total_cost,
                str(order.guid),
            ],
        )
        assert row is not None
        return PurchaseOrder(
            id=int(row["purchase_order_id"]),
            user_id=order.user_id,
            product_id=order.product_id,
            quantity=row["quantity"],
            total_cost=row["total_cost"],
            guid=order.guid,
            sku=order.sku,
        )

    def update(self, user_id: int, purchase_order_id: int, *, quantity: Decimal, total_cost: Decimal) -> PurchaseOrder | None:
        row = self._db.fetch_one(_UPDATE, [quantity, total_cost, user_id, purchase_order_id])
        if row is None:
            return None
        existing = self.get_by_id(user_id, purchase_order_id)
        assert existing is not None
        return PurchaseOrder(
            id=int(row["purchase_order_id"]),
            user_id=user_id,
            product_id=existing.product_id,
            quantity=row["quantity"],
            total_cost=row["total_cost"],
            sku=existing.sku,
        )

    def delete(self, user_id: int, purchase_order_id: int) -> bool:
        row = self._db.fetch_one(_DELETE, [user_id, purchase_order_id])
        return row is not None

    def list_by_user(self, user_id: int) -> list[dict[str, Any]]:
        return self._db.fetch_all(
            """
            SELECT purchase_order_id, user_id, product_id, quantity, total_cost, guid, created_at
            FROM purchase_order
            WHERE user_id = %s
            ORDER BY purchase_order_id DESC
            """,
            [user_id],
        )

    def get_row_by_id(self, user_id: int, purchase_order_id: int) -> dict[str, Any] | None:
        return self._db.fetch_one(
            """
            SELECT purchase_order_id, user_id, product_id, quantity, total_cost, guid, created_at
            FROM purchase_order
            WHERE user_id = %s AND purchase_order_id = %s
            """,
            [user_id, purchase_order_id],
        )
