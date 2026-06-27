from __future__ import annotations

import uuid
from decimal import Decimal

from services.txn import atomic

from domain.models import PurchaseOrder
from services.dtos.results import PurchaseOrderResult
from services.exceptions import OrderNotFound
from services.repositories.purchase_order_repository import PurchaseOrderRepository
from services.services.product_service import ProductService
from services.services.stock_service import StockService


class PurchaseOrderService:
    def __init__(
        self,
        product_service: ProductService,
        purchase_repo: PurchaseOrderRepository,
        stock_service: StockService,
    ) -> None:
        self._products = product_service
        self._orders = purchase_repo
        self._stock = stock_service

    def _get_order(self, user_id: int, purchase_order_id: int) -> PurchaseOrder:
        order = self._orders.get_by_id(user_id, purchase_order_id)
        if order is None:
            raise OrderNotFound("Purchase order", purchase_order_id)
        return order

    @atomic
    def create(
        self,
        user_id: int,
        *,
        sku: str,
        quantity: Decimal,
        total_cost: Decimal,
        guid: uuid.UUID | None = None,
    ) -> PurchaseOrderResult:
        order = PurchaseOrder(
            user_id=user_id,
            product_id=0,
            quantity=quantity,
            total_cost=total_cost,
            guid=guid or uuid.uuid4(),
            sku=sku,
        )
        order.validate()

        product = self._products.get_by_sku(user_id, sku)
        assert product.id is not None
        product_id = product.id

        existing = self._orders.get_by_guid(user_id, order.guid)
        if existing:
            return self._to_result(existing, product.sku, product_id)

        order.product_id = product_id
        saved = self._orders.save(order)
        assert saved.id is not None
        self._stock.compensate_purchase_order(
            user_id,
            product_id,
            saved.id,
            quantity_delta=quantity,
            unit_cost=order.unit_cost(),
        )
        return self._to_result(saved, product.sku, product_id)

    @atomic
    def update(
        self,
        user_id: int,
        purchase_order_id: int,
        *,
        quantity: Decimal | None = None,
        total_cost: Decimal | None = None,
    ) -> PurchaseOrderResult:
        po = self._get_order(user_id, purchase_order_id)
        assert po.id is not None and po.sku is not None
        product_id = po.product_id

        new_qty = quantity if quantity is not None else po.quantity
        new_cost = total_cost if total_cost is not None else po.total_cost
        updated_order = PurchaseOrder(
            user_id=user_id,
            product_id=product_id,
            quantity=new_qty,
            total_cost=new_cost,
            sku=po.sku,
        )
        updated_order.validate()

        available = self._stock.stock_for(user_id, product_id)
        po.assert_stock_available_for_reduction(new_qty, available)

        qty_delta_change = po.quantity_change(new_qty)
        unit_cost = updated_order.unit_cost()
        if qty_delta_change != 0:
            self._stock.compensate_purchase_order(
                user_id,
                product_id,
                purchase_order_id,
                quantity_delta=qty_delta_change,
                unit_cost=unit_cost,
            )

        saved = self._orders.update(user_id, purchase_order_id, quantity=new_qty, total_cost=new_cost)
        assert saved is not None
        return self._to_result(saved, po.sku, product_id)

    @atomic
    def delete(self, user_id: int, purchase_order_id: int) -> None:
        po = self._get_order(user_id, purchase_order_id)
        assert po.sku is not None and po.id is not None
        product_id = po.product_id

        available = self._stock.stock_for(user_id, product_id)
        po.assert_stock_available_for_delete(available)

        self._stock.compensate_purchase_order(
            user_id,
            product_id,
            purchase_order_id,
            quantity_delta=-po.quantity,
            unit_cost=po.unit_cost(),
        )
        self._orders.delete(user_id, purchase_order_id)

    def _to_result(self, order: PurchaseOrder, sku: str, product_id: int) -> PurchaseOrderResult:
        assert order.id is not None
        return PurchaseOrderResult(
            purchase_order_id=order.id,
            sku=sku,
            quantity=order.quantity,
            total_cost=order.total_cost,
            unit_cost=order.unit_cost(),
            remaining=self._stock.stock_for(order.user_id, product_id),
        )
