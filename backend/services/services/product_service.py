from __future__ import annotations

from django.db import transaction

from domain.models import Product
from services.dtos.results import ProductResult
from services.exceptions import UnknownProduct
from services.repositories.product_repository import ProductRepository


class ProductService:
    def __init__(self, product_repo: ProductRepository) -> None:
        self._products = product_repo

    def get_by_sku(self, user_id: int, sku: str) -> Product:
        product = self._products.get_by_sku(user_id, sku)
        if product is None:
            raise UnknownProduct(sku)
        return product

    def register(
        self, user_id: int, *, name: str, sku: str, unit: str, description: str = ""
    ) -> ProductResult:
        product = Product(user_id=user_id, sku=sku, name=name, unit=unit, description=description)
        product.validate_unit()
        saved = self._products.save(product)
        return self._to_result(saved)

    def update(
        self,
        user_id: int,
        product_id: int,
        *,
        name: str | None = None,
        description: str | None = None,
        unit: str | None = None,
    ) -> ProductResult:
        if unit is not None:
            Product(user_id=user_id, sku="", name="", unit=unit).validate_unit()
        existing = self._products.get_by_id(user_id, product_id)
        if existing is None:
            raise UnknownProduct(str(product_id))
        updated = self._products.update_fields(
            user_id, product_id, name=name, description=description, unit=unit
        )
        assert updated is not None
        return self._to_result(updated)

    @transaction.atomic
    def delete(self, user_id: int, product_id: int) -> None:
        existing = self._products.get_by_id(user_id, product_id)
        if existing is None:
            raise UnknownProduct(str(product_id))
        dependents = self._products.count_dependents(user_id, product_id)
        existing.assert_can_be_deleted(dependents)
        self._products.delete(user_id, product_id)

    @staticmethod
    def _to_result(product: Product) -> ProductResult:
        assert product.id is not None
        return ProductResult(
            product_id=product.id,
            sku=product.sku,
            name=product.name,
            unit=product.unit,
            description=product.description,
        )
