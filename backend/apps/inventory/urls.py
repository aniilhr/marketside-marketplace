from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    PurchaseOrderViewSet,
    StockItemViewSet,
    StockMovementViewSet,
    StockTransferViewSet,
    SupplierViewSet,
    WarehouseViewSet,
    auto_reorder,
    inventory_dashboard,
    low_stock,
)

router = DefaultRouter()
router.register("warehouses", WarehouseViewSet, basename="warehouse")
router.register("suppliers", SupplierViewSet, basename="supplier")
router.register("stock-items", StockItemViewSet, basename="stock-item")
router.register("movements", StockMovementViewSet, basename="movement")
router.register("purchase-orders", PurchaseOrderViewSet, basename="purchase-order")
router.register("transfers", StockTransferViewSet, basename="transfer")

urlpatterns = [
    path("dashboard/", inventory_dashboard),
    path("low-stock/", low_stock),
    path("auto-reorder/", auto_reorder),
    path("", include(router.urls)),
]
