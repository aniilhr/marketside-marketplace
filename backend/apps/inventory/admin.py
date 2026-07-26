from django.contrib import admin

from .models import (
    PurchaseOrder,
    PurchaseOrderLine,
    StockItem,
    StockMovement,
    StockTransfer,
    Supplier,
    Warehouse,
)

admin.site.register(
    [Warehouse, Supplier, StockItem, StockMovement, PurchaseOrder, PurchaseOrderLine, StockTransfer]
)
