from __future__ import annotations

import uuid
from decimal import Decimal

from django.db import transaction

from domain.models import SalesOrder
from services.dtos.results import SaleResult
from services.exceptions import OrderNotFound
from services.repositories.sales_order_repository import SalesOrderRepository
from services.services.product_service import ProductService
from services.services.stock_service import StockService


class SalesOrderService:
    def __init__(
        self,
        product_service: ProductService,
        sales_repo: SalesOrderRepository,
        stock_service: StockService,
    ) -> None:
        self._products = product_service
        self._orders = sales_repo
        self._stock = stock_service

    def _get_order(self, user_id: int, sales_order_id: int) -> SalesOrder:
        order = self._orders.get_by_id(user_id, sales_order_id)
        if order is None:
            raise OrderNotFound("Sales order", sales_order_id)
        return order

    @transaction.atomic
    def record_sale(
        self,
        user_id: int,
        *,
        sku: str,
        quantity: Decimal,
        unit_price: Decimal,
        guid: uuid.UUID | None = None,
    ) -> SaleResult:
        order = SalesOrder(
            user_id=user_id,
            product_id=0,
            quantity=quantity,
            unit_price=unit_price,
            guid=guid or uuid.uuid4(),
            sku=sku,
        )
        order.validate()

        product = self._products.get_by_sku(user_id, sku)
        assert product.id is not None
        product_id = product.id

        available = self._stock.stock_for(user_id, product_id)
        order.assert_stock_available(available)

        existing = self._orders.get_by_guid(user_id, order.guid)
        if existing:
            return self._to_result(existing, product.sku, product_id)

        order.product_id = product_id
        saved = self._orders.save(order)
        assert saved.id is not None
        self._stock.compensate_sales_order(
            user_id, product_id, saved.id, quantity_delta=-quantity
        )
        return self._to_result(saved, product.sku, product_id)

    @transaction.atomic
    def update(
        self,
        user_id: int,
        sales_order_id: int,
        *,
        quantity: Decimal | None = None,
        unit_price: Decimal | None = None,
    ) -> SaleResult:
        so = self._get_order(user_id, sales_order_id)
        assert so.id is not None and so.sku is not None
        product_id = so.product_id

        new_qty = quantity if quantity is not None else so.quantity
        new_price = unit_price if unit_price is not None else so.unit_price
        updated_order = SalesOrder(
            user_id=user_id,
            product_id=product_id,
            quantity=new_qty,
            unit_price=new_unit_price,
            sku=so.sku,
        )
        updated_order.validate()

        available = self._stock.stock_for(user_id, product_id)
        so.assert_stock_available_for_increase(new_qty, available)

        extra_sold = so.extra_quantity_sold(new_qty)
        if extra_sold != 0:
            self._stock.compensate_sales_order(
                user_id, product_id, sales_order_id, quantity_delta=-extra_sold
            )

        saved = self._orders.update(user_id, sales_order_id, quantity=new_qty, unit_price=new_unit_price)
        assert saved is not None
        return self._to_result(saved, so.sku, product_id)

    @transaction.atomic
    def delete(self, user_id: int, sales_order_id: int) -> None:
        so = self._get_order(user_id, sales_order_id)
        assert so.id is not None
        self._stock.compensate_sales_order(
            user_id, so.product_id, sales_order_id, quantity_delta=so.quantity
        )
        self._orders.delete(user_id, sales_order_id)

    def _to_result(self, order: SalesOrder, sku: str, product_id: int) -> SaleResult:
        assert order.id is not None
        return SaleResult(
            sales_order_id=order.id,
            sku=sku,
            quantity=order.quantity,
            unit_price=order.unit_price,
            revenue=order.revenue(),
            remaining=self._stock.stock_for(order.user_id, product_id),
        )
