from django.urls import include, path
from rest_framework.routers import DefaultRouter

from inventory_api.views import (
    FinancialsViewSet,
    ProductViewSet,
    PurchaseOrderViewSet,
    SalesOrderViewSet,
    StockMovementViewSet,
    StockViewSet,
)

router = DefaultRouter()
router.register("products", ProductViewSet, basename="product")
router.register("stock", StockViewSet, basename="stock")
router.register("stock-movements", StockMovementViewSet, basename="stock-movement")
router.register("purchase-orders", PurchaseOrderViewSet, basename="purchase-order")
router.register("sales-orders", SalesOrderViewSet, basename="sales-order")
router.register("financials", FinancialsViewSet, basename="financials")

urlpatterns = [
    path("", include(router.urls)),
]
