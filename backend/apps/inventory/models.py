from django.conf import settings
from django.db import models

from apps.catalog.models import Product
from apps.core.models import TimeStampedModel


class Warehouse(TimeStampedModel):
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=20, unique=True)
    city = models.CharField(max_length=80)
    state = models.CharField(max_length=80, blank=True)
    address = models.CharField(max_length=255, blank=True)
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="warehouses",
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.code})"


class Supplier(TimeStampedModel):
    name = models.CharField(max_length=150)
    contact_person = models.CharField(max_length=120, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=255, blank=True)
    lead_time_days = models.PositiveIntegerField(default=7)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class StockItem(TimeStampedModel):
    """Quantity of a product held at a specific warehouse."""

    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name="stock_items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="stock_items")
    quantity = models.IntegerField(default=0)
    bin_location = models.CharField(max_length=40, blank=True)
    batch_number = models.CharField(max_length=40, blank=True)
    expiry_date = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = ("warehouse", "product", "batch_number")

    def __str__(self):
        return f"{self.product} @ {self.warehouse}: {self.quantity}"


class StockMovement(TimeStampedModel):
    TYPES = [
        ("in", "Stock in"),
        ("out", "Stock out"),
        ("adjust", "Adjustment"),
        ("transfer", "Transfer"),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="movements")
    warehouse = models.ForeignKey(
        Warehouse, null=True, blank=True, on_delete=models.SET_NULL, related_name="movements"
    )
    movement_type = models.CharField(max_length=10, choices=TYPES)
    quantity = models.IntegerField()
    reference = models.CharField(max_length=60, blank=True)
    note = models.CharField(max_length=240, blank=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.movement_type} {self.quantity} - {self.product}"


class PurchaseOrder(TimeStampedModel):
    STATUS = [
        ("draft", "Draft"),
        ("sent", "Sent"),
        ("partial", "Partially received"),
        ("received", "Received"),
        ("cancelled", "Cancelled"),
    ]

    po_number = models.CharField(max_length=24, unique=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="purchase_orders")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="purchase_orders")
    status = models.CharField(max_length=12, choices=STATUS, default="draft")
    expected_date = models.DateField(null=True, blank=True)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )

    class Meta:
        ordering = ["-created_at"]

    def recalculate_total(self):
        self.total = sum((line.quantity * line.unit_cost for line in self.lines.all()), 0)
        self.save(update_fields=["total"])

    def __str__(self):
        return self.po_number


class PurchaseOrderLine(TimeStampedModel):
    purchase_order = models.ForeignKey(
        PurchaseOrder, on_delete=models.CASCADE, related_name="lines"
    )
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    received_quantity = models.PositiveIntegerField(default=0)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)


class StockTransfer(TimeStampedModel):
    STATUS = [("pending", "Pending"), ("in_transit", "In transit"), ("completed", "Completed")]

    reference = models.CharField(max_length=24, unique=True)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    source = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="transfers_out")
    destination = models.ForeignKey(
        Warehouse, on_delete=models.PROTECT, related_name="transfers_in"
    )
    quantity = models.PositiveIntegerField()
    status = models.CharField(max_length=12, choices=STATUS, default="pending")

    class Meta:
        ordering = ["-created_at"]
