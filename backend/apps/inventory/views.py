import secrets

from django.db import transaction
from django.db.models import F, Sum
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response

from apps.accounts.permissions import IsStaffRole
from apps.catalog.models import Product
from apps.catalog.serializers import ProductListSerializer
from apps.core.services import notify

from .models import (
    PurchaseOrder,
    PurchaseOrderLine,
    StockItem,
    StockMovement,
    StockTransfer,
    Supplier,
    Warehouse,
)
from .serializers import (
    PurchaseOrderSerializer,
    StockItemSerializer,
    StockMovementSerializer,
    StockTransferSerializer,
    SupplierSerializer,
    WarehouseSerializer,
)


class WarehouseViewSet(viewsets.ModelViewSet):
    serializer_class = WarehouseSerializer
    permission_classes = [IsStaffRole]
    queryset = Warehouse.objects.all()
    search_fields = ["name", "code", "city"]


class SupplierViewSet(viewsets.ModelViewSet):
    serializer_class = SupplierSerializer
    permission_classes = [IsStaffRole]
    queryset = Supplier.objects.all()
    search_fields = ["name", "email"]


class StockItemViewSet(viewsets.ModelViewSet):
    serializer_class = StockItemSerializer
    permission_classes = [IsStaffRole]
    queryset = StockItem.objects.select_related("product", "warehouse")
    filterset_fields = ["warehouse", "product"]
    search_fields = ["product__name", "product__sku", "bin_location"]


class StockMovementViewSet(viewsets.ModelViewSet):
    serializer_class = StockMovementSerializer
    permission_classes = [IsStaffRole]
    queryset = StockMovement.objects.select_related("product", "actor")
    filterset_fields = ["movement_type", "product", "warehouse"]

    def perform_create(self, serializer):
        movement = serializer.save(actor=self.request.user)
        delta = movement.quantity
        if movement.movement_type == "out":
            delta = -abs(movement.quantity)
        elif movement.movement_type == "in":
            delta = abs(movement.quantity)
        Product.objects.filter(pk=movement.product_id).update(stock=F("stock") + delta)
        if movement.warehouse_id:
            item, _ = StockItem.objects.get_or_create(
                warehouse=movement.warehouse, product=movement.product, batch_number=""
            )
            item.quantity += delta
            item.save(update_fields=["quantity"])


class PurchaseOrderViewSet(viewsets.ModelViewSet):
    serializer_class = PurchaseOrderSerializer
    permission_classes = [IsStaffRole]
    queryset = PurchaseOrder.objects.select_related("supplier", "warehouse").prefetch_related("lines")
    filterset_fields = ["status", "supplier", "warehouse"]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"])
    def send(self, request, pk=None):
        po = self.get_object()
        po.status = "sent"
        po.save(update_fields=["status"])
        return Response(self.get_serializer(po).data)

    @action(detail=True, methods=["post"], url_path="receive")
    def receive(self, request, pk=None):
        """Goods received note: {"lines": [{"line_id": 1, "quantity": 5}]}"""
        po = self.get_object()
        received = request.data.get("lines", [])
        with transaction.atomic():
            for row in received:
                line = PurchaseOrderLine.objects.filter(
                    pk=row.get("line_id"), purchase_order=po
                ).first()
                if not line:
                    continue
                quantity = int(row.get("quantity", 0))
                line.received_quantity += quantity
                line.save(update_fields=["received_quantity"])
                Product.objects.filter(pk=line.product_id).update(stock=F("stock") + quantity)
                item, _ = StockItem.objects.get_or_create(
                    warehouse=po.warehouse, product=line.product, batch_number=""
                )
                item.quantity += quantity
                item.save(update_fields=["quantity"])
                StockMovement.objects.create(
                    product=line.product,
                    warehouse=po.warehouse,
                    movement_type="in",
                    quantity=quantity,
                    reference=po.po_number,
                    note="Goods received",
                    actor=request.user,
                )
            fully = all(line.received_quantity >= line.quantity for line in po.lines.all())
            po.status = "received" if fully else "partial"
            po.save(update_fields=["status"])
        return Response(self.get_serializer(po).data)


class StockTransferViewSet(viewsets.ModelViewSet):
    serializer_class = StockTransferSerializer
    permission_classes = [IsStaffRole]
    queryset = StockTransfer.objects.select_related("product", "source", "destination")

    def perform_create(self, serializer):
        serializer.save(reference=f"TRF-{secrets.token_hex(3).upper()}")

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        transfer = self.get_object()
        if transfer.status == "completed":
            return Response({"detail": "Transfer already completed."}, status=400)
        with transaction.atomic():
            source_item, _ = StockItem.objects.get_or_create(
                warehouse=transfer.source, product=transfer.product, batch_number=""
            )
            dest_item, _ = StockItem.objects.get_or_create(
                warehouse=transfer.destination, product=transfer.product, batch_number=""
            )
            source_item.quantity -= transfer.quantity
            dest_item.quantity += transfer.quantity
            source_item.save(update_fields=["quantity"])
            dest_item.save(update_fields=["quantity"])
            transfer.status = "completed"
            transfer.save(update_fields=["status"])
            StockMovement.objects.create(
                product=transfer.product,
                warehouse=transfer.destination,
                movement_type="transfer",
                quantity=transfer.quantity,
                reference=transfer.reference,
                actor=request.user,
            )
        return Response(self.get_serializer(transfer).data)


@api_view(["GET"])
@permission_classes([IsStaffRole])
def low_stock(request):
    products = Product.objects.filter(stock__lte=F("low_stock_threshold"), is_active=True)
    return Response(ProductListSerializer(products, many=True).data)


@api_view(["GET"])
@permission_classes([IsStaffRole])
def inventory_dashboard(request):
    products = Product.objects.filter(is_active=True)
    low = products.filter(stock__lte=F("low_stock_threshold"))
    return Response(
        {
            "warehouses": Warehouse.objects.filter(is_active=True).count(),
            "suppliers": Supplier.objects.filter(is_active=True).count(),
            "tracked_products": products.count(),
            "total_units": products.aggregate(total=Sum("stock"))["total"] or 0,
            "out_of_stock": products.filter(stock=0).count(),
            "low_stock": low.count(),
            "open_purchase_orders": PurchaseOrder.objects.exclude(
                status__in=["received", "cancelled"]
            ).count(),
            "low_stock_items": list(low[:10].values("id", "name", "sku", "stock", "low_stock_threshold")),
            "recent_movements": StockMovementSerializer(
                StockMovement.objects.select_related("product")[:10], many=True
            ).data,
        }
    )


@api_view(["POST"])
@permission_classes([IsStaffRole])
def auto_reorder(request):
    """Draft purchase orders for every product below its threshold."""
    supplier = Supplier.objects.filter(is_active=True).first()
    warehouse = Warehouse.objects.filter(is_active=True).first()
    if not supplier or not warehouse:
        return Response({"detail": "Add a supplier and a warehouse first."}, status=400)
    low = Product.objects.filter(stock__lte=F("low_stock_threshold"), is_active=True)
    if not low.exists():
        return Response({"detail": "Nothing to reorder.", "created": 0})
    po = PurchaseOrder.objects.create(
        po_number=f"PO-{secrets.token_hex(3).upper()}",
        supplier=supplier,
        warehouse=warehouse,
        expected_date=timezone.now().date() + timezone.timedelta(days=supplier.lead_time_days),
        created_by=request.user,
    )
    for product in low:
        PurchaseOrderLine.objects.create(
            purchase_order=po,
            product=product,
            quantity=max(product.low_stock_threshold * 3 - product.stock, 1),
            unit_cost=product.cost_price or product.price,
        )
    po.recalculate_total()
    notify(request.user, "Reorder draft created", po.po_number, "info")
    return Response(
        {"detail": "Draft purchase order created.", "purchase_order": PurchaseOrderSerializer(po).data},
        status=status.HTTP_201_CREATED,
    )
