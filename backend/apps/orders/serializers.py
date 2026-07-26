from rest_framework import serializers

from apps.catalog.serializers import ProductListSerializer

from .models import (
    Cart,
    CartItem,
    Coupon,
    Order,
    OrderEvent,
    OrderItem,
    Payment,
    ReturnRequest,
)


class CartItemSerializer(serializers.ModelSerializer):
    product_detail = ProductListSerializer(source="product", read_only=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = CartItem
        fields = ["id", "product", "product_detail", "quantity", "subtotal"]

    def validate(self, attrs):
        product = attrs.get("product")
        quantity = attrs.get("quantity", 1)
        if product and quantity > product.stock:
            raise serializers.ValidationError(
                {"quantity": f"Only {product.stock} left in stock."}
            )
        return attrs


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ["id", "items", "subtotal", "coupon_code", "item_count"]

    def get_item_count(self, obj):
        return sum(item.quantity for item in obj.items.all())


class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = "__all__"
        read_only_fields = ["used_count", "seller"]


class OrderItemSerializer(serializers.ModelSerializer):
    product_slug = serializers.CharField(source="product.slug", read_only=True)
    store_name = serializers.CharField(
        source="seller.seller_profile.store_name", read_only=True, default=""
    )

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product",
            "product_slug",
            "product_name",
            "thumbnail",
            "unit_price",
            "quantity",
            "subtotal",
            "store_name",
        ]


class OrderEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderEvent
        fields = ["id", "status", "note", "created_at"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    events = OrderEventSerializer(many=True, read_only=True)
    customer_email = serializers.CharField(source="user.email", read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "order_number",
            "customer_email",
            "status",
            "payment_method",
            "payment_status",
            "subtotal",
            "discount",
            "tax",
            "shipping_fee",
            "total",
            "coupon_code",
            "shipping_address",
            "items",
            "events",
            "delivered_at",
            "created_at",
        ]


class CheckoutSerializer(serializers.Serializer):
    address_id = serializers.IntegerField()
    payment_method = serializers.ChoiceField(choices=[c[0] for c in Order.PAYMENT_METHODS])
    coupon_code = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)


class PaymentSerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(source="order.order_number", read_only=True)

    class Meta:
        model = Payment
        fields = ["id", "order_number", "provider", "reference", "amount", "status", "created_at"]


class ReturnRequestSerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(source="order.order_number", read_only=True)

    class Meta:
        model = ReturnRequest
        fields = ["id", "order", "order_number", "reason", "status", "refund_amount", "created_at"]
        read_only_fields = ["status", "refund_amount"]
