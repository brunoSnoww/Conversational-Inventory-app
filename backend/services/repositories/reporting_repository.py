from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from services.database import Database
from services.dtos.results import ProfitResult

_FINANCIALS_SELECT = """
SELECT product_id, user_id, sku, name, unit::text AS unit,
       quantity_on_hand, total_qty_purchased, total_qty_sold,
       total_cost, total_revenue, profit
FROM product_financials_view
WHERE user_id = %s
"""
_FINANCIALS_BY_PK = """
SELECT product_id, user_id, sku, name, unit::text AS unit,
       quantity_on_hand, total_qty_purchased, total_qty_sold,
       total_cost, total_revenue, profit
FROM product_financials_view
WHERE user_id = %s
  AND (product_id::text = %s OR lower(sku) = lower(%s))
LIMIT 1
"""


@dataclass(frozen=True)
class FinancialRow:
    product_id: int
    user_id: int
    sku: str
    name: str
    unit: str
    quantity_on_hand: Decimal
    total_qty_purchased: Decimal
    total_qty_sold: Decimal
    total_cost: Decimal
    total_revenue: Decimal
    profit: Decimal


def _from_row(row: dict[str, Any]) -> FinancialRow:
    return FinancialRow(
        product_id=int(row["product_id"]),
        user_id=int(row["user_id"]),
        sku=row["sku"],
        name=row["name"],
        unit=row["unit"],
        quantity_on_hand=row["quantity_on_hand"],
        total_qty_purchased=row["total_qty_purchased"],
        total_qty_sold=row["total_qty_sold"],
        total_cost=row["total_cost"],
        total_revenue=row["total_revenue"],
        profit=row["profit"],
    )


class ReportingRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def get_financials_by_sku(self, user_id: int, sku: str) -> ProfitResult | None:
        row = self.get_financials_by_id_or_sku(user_id, sku)
        if row is None:
            return None
        return ProfitResult(
            sku=row.sku,
            name=row.name,
            total_cost=row.total_cost,
            total_revenue=row.total_revenue,
            profit=row.profit,
        )

    def get_financials_map(
        self, user_id: int, product_ids: list[int] | None = None
    ) -> dict[int, FinancialRow]:
        if product_ids is not None and not product_ids:
            return {}
        if product_ids is None:
            rows = self._db.fetch_all(_FINANCIALS_SELECT, [user_id])
        else:
            rows = self._db.fetch_all(
                f"{_FINANCIALS_SELECT} AND product_id = ANY(%s)",
                [user_id, product_ids],
            )
        return {int(row["product_id"]): _from_row(row) for row in rows}

    def get_financials_by_id_or_sku(self, user_id: int, pk: str | int) -> FinancialRow | None:
        pk_str = str(pk)
        row = self._db.fetch_one(_FINANCIALS_BY_PK, [user_id, pk_str, pk_str])
        return None if row is None else _from_row(row)
