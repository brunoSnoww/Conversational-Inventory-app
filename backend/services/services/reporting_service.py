from __future__ import annotations

from services.dtos.results import ProfitResult
from services.exceptions import UnknownProduct
from services.repositories.reporting_repository import ReportingRepository
from services.services.product_service import ProductService


class ReportingService:
    def __init__(
        self,
        product_service: ProductService,
        reporting_repo: ReportingRepository,
    ) -> None:
        self._products = product_service
        self._reporting = reporting_repo

    def get_profit(self, user_id: int, *, sku: str) -> ProfitResult:
        self._products.get_by_sku(user_id, sku)
        result = self._reporting.get_financials_by_sku(user_id, sku)
        if result is None:
            raise UnknownProduct(sku)
        return result
