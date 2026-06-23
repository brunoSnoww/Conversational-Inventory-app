from __future__ import annotations

from typing import Any

from services.database import Database
from domain.models import Product, ProductDependents

_UPSQL = """
INSERT INTO product (user_id, name, description, sku, unit)
VALUES (%s, %s, %s, %s, %s::product_unit)
ON CONFLICT (user_id, lower(sku))
DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description,
    unit = EXCLUDED.unit, updated_at = now()
RETURNING product_id, sku, name, unit, description;
"""
_GET_BY_SKU = """
SELECT product_id, user_id, sku, name, unit, description
FROM product WHERE user_id = %s AND lower(sku) = lower(%s);
"""
_GET_BY_ID = """
SELECT product_id, user_id, sku, name, unit, description
FROM product WHERE user_id = %s AND product_id = %s;
"""
_COUNT_DEPENDENTS = """
WITH ctx AS (SELECT %s::bigint AS user_id, %s::bigint AS product_id)
SELECT
    (SELECT COUNT(*) FROM stock_movement sm JOIN ctx c ON sm.user_id = c.user_id AND sm.product_id = c.product_id) AS movements,
    (SELECT COUNT(*) FROM purchase_order po JOIN ctx c ON po.user_id = c.user_id AND po.product_id = c.product_id) AS purchases,
    (SELECT COUNT(*) FROM sales_order so JOIN ctx c ON so.user_id = c.user_id AND so.product_id = c.product_id) AS sales;
"""
_DELETE = "DELETE FROM product WHERE user_id = %s AND product_id = %s RETURNING product_id;"


def _from_row(row: dict[str, Any]) -> Product:
    return Product(
        id=int(row["product_id"]),
        user_id=int(row["user_id"]),
        sku=row["sku"],
        name=row["name"],
        unit=row["unit"],
        description=row["description"],
    )


class ProductRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def get_by_sku(self, user_id: int, sku: str) -> Product | None:
        row = self._db.fetch_one(_GET_BY_SKU, [user_id, sku])
        return None if row is None else _from_row(row)

    def get_by_id(self, user_id: int, product_id: int) -> Product | None:
        row = self._db.fetch_one(_GET_BY_ID, [user_id, product_id])
        return None if row is None else _from_row(row)

    def save(self, product: Product) -> Product:
        row = self._db.fetch_one(
            _UPSQL,
            [product.user_id, product.name, product.description, product.sku, product.unit],
        )
        assert row is not None
        return Product(
            id=int(row["product_id"]),
            user_id=product.user_id,
            sku=row["sku"],
            name=row["name"],
            unit=row["unit"],
            description=row["description"],
        )

    def update_fields(
        self,
        user_id: int,
        product_id: int,
        *,
        name: str | None = None,
        description: str | None = None,
        unit: str | None = None,
    ) -> Product | None:
        sets: list[str] = []
        params: list[Any] = []
        if name is not None:
            sets.append("name = %s")
            params.append(name)
        if description is not None:
            sets.append("description = %s")
            params.append(description)
        if unit is not None:
            sets.append("unit = %s::product_unit")
            params.append(unit)
        if not sets:
            return self.get_by_id(user_id, product_id)
        params.extend([user_id, product_id])
        row = self._db.fetch_one(
            f"UPDATE product SET {', '.join(sets)} WHERE user_id = %s AND product_id = %s "
            "RETURNING product_id, user_id, sku, name, unit, description",
            params,
        )
        return None if row is None else _from_row(row)

    def count_dependents(self, user_id: int, product_id: int) -> ProductDependents:
        row = self._db.fetch_one(_COUNT_DEPENDENTS, [user_id, product_id])
        assert row is not None
        return ProductDependents(
            movements=int(row["movements"]),
            purchases=int(row["purchases"]),
            sales=int(row["sales"]),
        )

    def delete(self, user_id: int, product_id: int) -> bool:
        row = self._db.fetch_one(_DELETE, [user_id, product_id])
        return row is not None

    def list_by_user(self, user_id: int) -> list[Product]:
        from inventory_api.models import Product as ProductModel

        return [
            Product(
                id=int(p.product_id),
                user_id=int(p.user_id),
                sku=p.sku,
                name=p.name,
                unit=p.unit,
                description=p.description or "",
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
            for p in ProductModel.objects.filter(user_id=user_id).order_by("sku")
        ]
