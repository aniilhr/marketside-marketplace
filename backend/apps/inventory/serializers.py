from rest_framework import serializers

from .models import (
    PurchaseOrder,
    PurchaseOrderLine,
    StockItem,
    StockMovement,
    StockTransfer,
    Supplier,
    Warehouse,
)


class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = "__all__"


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = "__all__"


class StockItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    sku = serializers.CharField(source="product.sku", read_only=True)
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True)

    class Meta:
        model = StockItem
        fields = [
            "id",
            "warehouse",
            "warehouse_name",
            "product",
            "product_name",
            "sku",
            "quantity",
            "bin_location",
            "batch_number",
            "expiry_date",
        ]


class StockMovementSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    actor_email = serializers.CharField(source="actor.email", read_only=True, default="")

    class Meta:
        model = StockMovement
        fields = [
            "id",
            "product",
            "product_name",
            "warehouse",
            "movement_type",
            "quantity",
            "reference",
            "note",
            "actor_email",
            "created_at",
        ]
        read_only_fields = ["created_at"]


class PurchaseOrderLineSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = PurchaseOrderLine
        fields = ["id", "product", "product_name", "quantity", "received_quantity", "unit_cost"]


class PurchaseOrderSerializer(serializers.ModelSerializer):
    lines = PurchaseOrderLineSerializer(many=True)
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = [
            "id",
            "po_number",
            "supplier",
            "supplier_name",
            "warehouse",
            "status",
            "expected_date",
            "total",
            "lines",
            "created_at",
        ]
        read_only_fields = ["po_number", "total", "status"]

    def create(self, validated_data):
        import secrets

        lines = validated_data.pop("lines", [])
        po = PurchaseOrder.objects.create(
            po_number=f"PO-{secrets.token_hex(3).upper()}", **validated_data
        )
        for line in lines:
            PurchaseOrderLine.objects.create(purchase_order=po, **line)
        po.recalculate_total()
        return po


class StockTransferSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = StockTransfer
        fields = [
            "id",
            "reference",
            "product",
            "product_name",
            "source",
            "destination",
            "quantity",
            "status",
            "created_at",
        ]
        read_only_fields = ["reference", "status"]
