import secrets
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.catalog.models import Product
from apps.core.models import TimeStampedModel


class Cart(TimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart"
    )
    coupon_code = models.CharField(max_length=30, blank=True)

    @property
    def subtotal(self):
        return sum((item.subtotal for item in self.items.all()), Decimal("0.00"))

    def __str__(self):
        return f"Cart of {self.user}"


class CartItem(TimeStampedModel):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("cart", "product")

    @property
    def subtotal(self):
        return self.product.price * self.quantity


class Coupon(TimeStampedModel):
    TYPES = [("percent", "Percentage"), ("fixed", "Fixed amount")]

    code = models.CharField(max_length=30, unique=True)
    description = models.CharField(max_length=200, blank=True)
    discount_type = models.CharField(max_length=10, choices=TYPES, default="percent")
    value = models.DecimalField(max_digits=10, decimal_places=2)
    min_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_discount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    usage_limit = models.PositiveIntegerField(default=0, help_text="0 = unlimited")
    used_count = models.PositiveIntegerField(default=0)
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="coupons",
    )
    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def is_valid_for(self, amount):
        now = timezone.now()
        if not self.is_active or self.valid_from > now:
            return False, "Coupon is not active yet."
        if self.valid_until and self.valid_until < now:
            return False, "Coupon has expired."
        if self.usage_limit and self.used_count >= self.usage_limit:
            return False, "Coupon usage limit reached."
        if amount < self.min_order_value:
            return False, f"Minimum order value is {self.min_order_value}."
        return True, ""

    def discount_for(self, amount):
        if self.discount_type == "percent":
            discount = amount * self.value / Decimal(100)
        else:
            discount = self.value
        if self.max_discount:
            discount = min(discount, self.max_discount)
        return min(discount.quantize(Decimal("0.01")), amount)

    def __str__(self):
        return self.code


class Order(TimeStampedModel):
    STATUS = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("packed", "Packed"),
        ("ready_to_ship", "Ready to ship"),
        ("shipped", "Shipped"),
        ("out_for_delivery", "Out for delivery"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
        ("returned", "Returned"),
        ("refunded", "Refunded"),
    ]
    PAYMENT_METHODS = [
        ("cod", "Cash on delivery"),
        ("card", "Card"),
        ("upi", "UPI"),
        ("wallet", "Wallet"),
    ]
    PAYMENT_STATUS = [
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
    ]

    order_number = models.CharField(max_length=24, unique=True, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders"
    )
    status = models.CharField(max_length=20, choices=STATUS, default="pending")
    payment_method = models.CharField(max_length=12, choices=PAYMENT_METHODS, default="cod")
    payment_status = models.CharField(max_length=12, choices=PAYMENT_STATUS, default="pending")
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    shipping_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    coupon_code = models.CharField(max_length=30, blank=True)
    shipping_address = models.JSONField(default=dict)
    delivery_partner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="deliveries",
    )
    delivery_otp = models.CharField(max_length=6, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = f"ORD-{timezone.now():%Y%m%d}-{secrets.token_hex(3).upper()}"
        super().save(*args, **kwargs)

    def issue_delivery_otp(self):
        self.delivery_otp = f"{secrets.randbelow(1000000):06d}"
        self.save(update_fields=["delivery_otp"])
        return self.delivery_otp

    def __str__(self):
        return self.order_number


class OrderItem(TimeStampedModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="sold_items"
    )
    product_name = models.CharField(max_length=200)
    thumbnail = models.URLField(blank=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    commission = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.product_name} x{self.quantity}"


class OrderEvent(TimeStampedModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="events")
    status = models.CharField(max_length=20)
    note = models.CharField(max_length=240, blank=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )

    class Meta:
        ordering = ["created_at"]


class Payment(TimeStampedModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="payments")
    provider = models.CharField(max_length=30, default="mock")
    reference = models.CharField(max_length=80, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, default="pending")
    raw_response = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]


class ReturnRequest(TimeStampedModel):
    STATUS = [
        ("requested", "Requested"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("refunded", "Refunded"),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="returns")
    reason = models.TextField()
    status = models.CharField(max_length=12, choices=STATUS, default="requested")
    refund_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        ordering = ["-created_at"]
