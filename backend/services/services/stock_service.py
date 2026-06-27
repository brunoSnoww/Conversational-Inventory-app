from __future__ import annotations

from decimal import Decimal

from services.txn import atomic

from domain.models import StockMovement
from services.dtos.results import StockQueryResult, StockResult
from services.exceptions import InsufficientStock, InventoryError
from services.repositories.product_repository import ProductRepository
from services.repositories.stock_movement_repository import StockMovementRepository
from services.services.product_service import ProductService


class StockService:
    def __init__(
        self,
        product_service: ProductService,
        product_repo: ProductRepository,
        stock_repo: StockMovementRepository,
    ) -> None:
        self._products = product_service
        self._product_repo = product_repo
        self._stock = stock_repo

    def stock_for(self, user_id: int, product_id: int) -> Decimal:
        return self._stock.stock_for(user_id, product_id)

    def add_stock(
        self, user_id: int, *, sku: str, quantity: Decimal, unit_cost: Decimal | None = None
    ) -> StockResult:
        movement = self.create_manual_movement(
            user_id, sku=sku, quantity=quantity, unit_cost=unit_cost
        )
        return StockResult(
            sku=movement["sku"],
            remaining=self.stock_for(user_id, int(movement["product_id"])),
        )

    def query_stock(self, user_id: int, *, sku: str | None = None) -> list[StockQueryResult]:
        if sku is not None:
            product = self._products.get_by_sku(user_id, sku)
            assert product.id is not None
            return [
                StockQueryResult(
                    sku=product.sku,
                    name=product.name,
                    unit=product.unit,
                    quantity_on_hand=self.stock_for(user_id, product.id),
                )
            ]
        return [
            StockQueryResult(
                sku=p.sku,
                name=p.name,
                unit=p.unit,
                quantity_on_hand=self.stock_for(user_id, p.id),
            )
            for p in self._product_repo.list_by_user(user_id)
            if p.id is not None
        ]

    def list_movements(self, user_id: int, *, product_id: int | None = None) -> list[dict]:
        return [m.to_api_dict() for m in self._stock.list_by_user(user_id, product_id=product_id)]

    def _get_movement_model(self, user_id: int, stock_movement_id: int) -> StockMovement:
        movement = self._stock.get_by_id(user_id, stock_movement_id)
        if movement is None:
            raise InventoryError(f"Stock movement {stock_movement_id} not found.")
        return movement

    def get_movement(self, user_id: int, stock_movement_id: int) -> dict:
        return self._get_movement_model(user_id, stock_movement_id).to_api_dict()

    @atomic
    def create_manual_movement(
        self, user_id: int, *, sku: str, quantity: Decimal, unit_cost: Decimal | None = None
    ) -> dict:
        StockMovement(
            user_id=user_id, product_id=0, quantity_delta=quantity, source="MANUAL"
        ).validate_positive_quantity(quantity)
        product = self._products.get_by_sku(user_id, sku)
        assert product.id is not None
        movement = self._stock.append(
            user_id,
            product.id,
            quantity_delta=quantity,
            source="MANUAL",
            source_id=None,
            unit_cost=unit_cost,
        )
        movement.sku = product.sku
        return movement.to_api_dict()

    @atomic
    def update_manual_movement(
        self,
        user_id: int,
        stock_movement_id: int,
        *,
        quantity: Decimal | None = None,
        unit_cost: Decimal | None = None,
    ) -> dict:
        existing = self._get_movement_model(user_id, stock_movement_id)
        existing.assert_manual()

        old_qty = existing.quantity_delta
        new_qty = quantity if quantity is not None else old_qty
        StockMovement(
            user_id=user_id,
            product_id=existing.product_id,
            quantity_delta=new_qty,
            source="MANUAL",
            sku=existing.sku,
        ).validate_positive_quantity(new_qty)

        qty_delta_change = new_qty - old_qty
        if qty_delta_change < 0:
            available = self.stock_for(user_id, existing.product_id)
            assert existing.sku is not None
            if available + qty_delta_change < 0:
                raise InsufficientStock(existing.sku, abs(qty_delta_change), available)

        if qty_delta_change != 0:
            movement = self._stock.append(
                user_id,
                existing.product_id,
                quantity_delta=qty_delta_change,
                source="MANUAL",
                source_id=None,
                unit_cost=unit_cost,
            )
            movement.sku = existing.sku
            return movement.to_api_dict()
        return existing.to_api_dict()

    @atomic
    def delete_manual_movement(self, user_id: int, stock_movement_id: int) -> None:
        existing = self._get_movement_model(user_id, stock_movement_id)
        later = self._stock.count_later_than(user_id, existing.product_id, stock_movement_id)
        available = self.stock_for(user_id, existing.product_id)
        existing.assert_deletable(later_movement_count=later, available=available)

        self._stock.append(
            user_id,
            existing.product_id,
            quantity_delta=-existing.quantity_delta,
            source="MANUAL",
            source_id=None,
            unit_cost=existing.unit_cost,
        )

    def compensate_purchase_order(
        self,
        user_id: int,
        product_id: int,
        purchase_order_id: int,
        *,
        quantity_delta: Decimal,
        unit_cost: Decimal | None,
    ) -> None:
        if quantity_delta == 0:
            return
        self._stock.append(
            user_id,
            product_id,
            quantity_delta=quantity_delta,
            source="PURCHASE_ORDER",
            source_id=purchase_order_id,
            unit_cost=unit_cost,
        )

    def compensate_sales_order(
        self,
        user_id: int,
        product_id: int,
        sales_order_id: int,
        *,
        quantity_delta: Decimal,
    ) -> None:
        if quantity_delta == 0:
            return
        self._stock.append(
            user_id,
            product_id,
            quantity_delta=quantity_delta,
            source="SALES_ORDER",
            source_id=sales_order_id,
        )
