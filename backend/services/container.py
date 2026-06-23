"""Wire repositories and services for dependency injection."""

from __future__ import annotations

from dataclasses import dataclass

from services.database import Database
from services.repositories.product_repository import ProductRepository
from services.repositories.purchase_order_repository import PurchaseOrderRepository
from services.repositories.reporting_repository import ReportingRepository
from services.repositories.sales_order_repository import SalesOrderRepository
from services.repositories.stock_movement_repository import StockMovementRepository
from services.services.product_service import ProductService
from services.services.purchase_order_service import PurchaseOrderService
from services.services.reporting_service import ReportingService
from services.services.sales_order_service import SalesOrderService
from services.services.stock_service import StockService


@dataclass(frozen=True)
class InventoryServices:
    products: ProductService
    stock: StockService
    purchase_orders: PurchaseOrderService
    sales_orders: SalesOrderService
    reporting: ReportingService
    product_repo: ProductRepository
    stock_repo: StockMovementRepository
    reporting_repo: ReportingRepository


def build_inventory_services(db: Database | None = None) -> InventoryServices:
    db = db or Database()
    product_repo = ProductRepository(db)
    stock_repo = StockMovementRepository(db)
    purchase_repo = PurchaseOrderRepository(db)
    sales_repo = SalesOrderRepository(db)
    reporting_repo = ReportingRepository(db)

    product_service = ProductService(product_repo)
    stock_service = StockService(product_service, product_repo, stock_repo)
    purchase_service = PurchaseOrderService(product_service, purchase_repo, stock_service)
    sales_service = SalesOrderService(product_service, sales_repo, stock_service)
    reporting_service = ReportingService(product_service, reporting_repo)

    return InventoryServices(
        products=product_service,
        stock=stock_service,
        purchase_orders=purchase_service,
        sales_orders=sales_service,
        reporting=reporting_service,
        product_repo=product_repo,
        stock_repo=stock_repo,
        reporting_repo=reporting_repo,
    )
