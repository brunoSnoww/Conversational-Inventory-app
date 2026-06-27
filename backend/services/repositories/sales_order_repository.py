from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from domain.models import SalesOrder
from services.database import Database

_INSERT = """
INSERT INTO sales_order (user_id, product_id, quantity, unit_price, guid)
VALUES (%s, %s, %s, %s, %s) RETURNING sales_order_id, quantity, unit_price;
"""
_GET_BY_GUID = """
SELECT sales_order_id, quantity, unit_price FROM sales_order WHERE user_id = %s AND guid = %s;
"""
_GET_BY_ID = """
SELECT so.sales_order_id, so.product_id, so.quantity, so.unit_price, p.sku
FROM sales_order so
JOIN product p ON p.product_id = so.product_id AND p.user_id = so.user_id
WHERE so.user_id = %s AND so.sales_order_id = %s;
"""
_UPDATE = """
UPDATE sales_order SET quantity = %s, unit_price = %s
WHERE user_id = %s AND sales_order_id = %s
RETURNING sales_order_id, quantity, unit_price;
"""
_DELETE = """
DELETE FROM sales_order WHERE user_id = %s AND sales_order_id = %s RETURNING sales_order_id;
"""


def _from_row(row: dict[str, Any], *, user_id: int) -> SalesOrder:
    return SalesOrder(
        id=int(row["sales_order_id"]),
        user_id=user_id,
        product_id=int(row["product_id"]),
        quantity=row["quantity"],
        unit_price=row["unit_price"],
        sku=row.get("sku"),
    )


class SalesOrderRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def get_by_id(self, user_id: int, sales_order_id: int) -> SalesOrder | None:
        row = self._db.fetch_one(_GET_BY_ID, [user_id, sales_order_id])
        return None if row is None else _from_row(row, user_id=user_id)

    def get_by_guid(self, user_id: int, guid: UUID) -> SalesOrder | None:
        row = self._db.fetch_one(_GET_BY_GUID, [user_id, str(guid)])
        if row is None:
            return None
        return SalesOrder(
            id=int(row["sales_order_id"]),
            user_id=user_id,
            product_id=0,
            quantity=row["quantity"],
            unit_price=row["unit_price"],
            guid=guid,
        )

    def save(self, order: SalesOrder) -> SalesOrder:
        row = self._db.fetch_one(
            _INSERT,
            [
                order.user_id,
                order.product_id,
                order.quantity,
                order.unit_price,
                str(order.guid),
            ],
        )
        assert row is not None
        return SalesOrder(
            id=int(row["sales_order_id"]),
            user_id=order.user_id,
            product_id=order.product_id,
            quantity=row["quantity"],
            unit_price=row["unit_price"],
            guid=order.guid,
            sku=order.sku,
        )

    def update(
        self, user_id: int, sales_order_id: int, *, quantity: Decimal, unit_price: Decimal
    ) -> SalesOrder | None:
        row = self._db.fetch_one(_UPDATE, [quantity, unit_price, user_id, sales_order_id])
        if row is None:
            return None
        existing = self.get_by_id(user_id, sales_order_id)
        assert existing is not None
        return SalesOrder(
            id=int(row["sales_order_id"]),
            user_id=user_id,
            product_id=existing.product_id,
            quantity=row["quantity"],
            unit_price=row["unit_price"],
            sku=existing.sku,
        )

    def delete(self, user_id: int, sales_order_id: int) -> bool:
        row = self._db.fetch_one(_DELETE, [user_id, sales_order_id])
        return row is not None

    def list_by_user(self, user_id: int) -> list[dict[str, Any]]:
        return self._db.fetch_all(
            """
            SELECT sales_order_id, user_id, product_id, quantity, unit_price, guid, created_at
            FROM sales_order
            WHERE user_id = %s
            ORDER BY sales_order_id DESC
            """,
            [user_id],
        )

    def get_row_by_id(self, user_id: int, sales_order_id: int) -> dict[str, Any] | None:
        return self._db.fetch_one(
            """
            SELECT sales_order_id, user_id, product_id, quantity, unit_price, guid, created_at
            FROM sales_order
            WHERE user_id = %s AND sales_order_id = %s
            """,
            [user_id, sales_order_id],
        )
