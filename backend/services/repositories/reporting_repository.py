from __future__ import annotations

from decimal import Decimal

from services.database import Database
from services.dtos.results import ProfitResult


class ReportingRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def get_financials_by_sku(self, user_id: int, sku: str) -> ProfitResult | None:
        from inventory_api.models import ProductFinancialsView

        row = ProductFinancialsView.objects.filter(user_id=user_id, sku__iexact=sku).first()
        if row is None:
            return None
        return ProfitResult(
            sku=row.sku,
            name=row.name,
            total_cost=row.total_cost,
            total_revenue=row.total_revenue,
            profit=row.profit,
        )

    def get_financials_map(self, user_id: int, product_ids: list[int] | None = None) -> dict[int, object]:
        from inventory_api.models import ProductFinancialsView

        qs = ProductFinancialsView.objects.filter(user_id=user_id)
        if product_ids is not None:
            qs = qs.filter(product_id__in=product_ids)
        return {int(row.product_id): row for row in qs}

    def get_financials_by_id_or_sku(self, user_id: int, pk: str | int) -> object | None:
        from django.db.models import Q
        from inventory_api.models import ProductFinancialsView

        return (
            ProductFinancialsView.objects.filter(user_id=user_id)
            .filter(Q(product_id=pk) | Q(sku__iexact=pk))
            .first()
        )
