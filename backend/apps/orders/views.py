from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.db.models import F, Q, Sum
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import Address
from apps.accounts.permissions import IsAdmin, IsDeliveryPartner, IsSellerOrAdmin
from apps.catalog.models import Product
from apps.core.services import log_action, notify
from apps.inventory.models import StockMovement

from .models import Cart, CartItem, Coupon, Order, OrderEvent, OrderItem, Payment, ReturnRequest
from .serializers import (
    CartItemSerializer,
    CartSerializer,
    CheckoutSerializer,
    CouponSerializer,
    OrderSerializer,
    PaymentSerializer,
    ReturnRequestSerializer,
)

SHIPPING_FREE_ABOVE = Decimal("999")
SHIPPING_FEE = Decimal("49")


def get_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


class CartViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        return Response(CartSerializer(get_cart(request.user)).data)

    @action(detail=False, methods=["post"], url_path="items")
    def add_item(self, request):
        cart = get_cart(request.user)
        serializer = CartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = serializer.validated_data["product"]
        quantity = serializer.validated_data.get("quantity", 1)
        item, created = CartItem.objects.get_or_create(
            cart=cart, product=product, defaults={"quantity": quantity}
        )
        if not created:
            item.quantity = min(item.quantity + quantity, product.stock)
            item.save(update_fields=["quantity"])
        return Response(CartSerializer(cart).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["patch"], url_path=r"items/(?P<item_id>\d+)")
    def update_item(self, request, item_id=None):
        cart = get_cart(request.user)
        item = cart.items.filter(pk=item_id).first()
        if not item:
            return Response({"detail": "Item not in cart."}, status=404)
        quantity = int(request.data.get("quantity", item.quantity))
        if quantity <= 0:
            item.delete()
        elif quantity > item.product.stock:
            return Response({"detail": f"Only {item.product.stock} left."}, status=400)
        else:
            item.quantity = quantity
            item.save(update_fields=["quantity"])
        return Response(CartSerializer(cart).data)

    @action(detail=False, methods=["delete"], url_path=r"items/(?P<item_id>\d+)/remove")
    def remove_item(self, request, item_id=None):
        cart = get_cart(request.user)
        cart.items.filter(pk=item_id).delete()
        return Response(CartSerializer(cart).data)

    @action(detail=False, methods=["delete"])
    def clear(self, request):
        cart = get_cart(request.user)
        cart.items.all().delete()
        cart.coupon_code = ""
        cart.save(update_fields=["coupon_code"])
        return Response(CartSerializer(cart).data)

    @action(detail=False, methods=["post"], url_path="apply-coupon")
    def apply_coupon(self, request):
        cart = get_cart(request.user)
        code = request.data.get("code", "").strip().upper()
        coupon = Coupon.objects.filter(code=code).first()
        if not coupon:
            return Response({"detail": "Coupon not found."}, status=404)
        valid, message = coupon.is_valid_for(cart.subtotal)
        if not valid:
            return Response({"detail": message}, status=400)
        cart.coupon_code = code
        cart.save(update_fields=["coupon_code"])
        return Response(
            {
                "detail": "Coupon applied.",
                "discount": coupon.discount_for(cart.subtotal),
                "cart": CartSerializer(cart).data,
            }
        )


class CouponViewSet(viewsets.ModelViewSet):
    serializer_class = CouponSerializer
    permission_classes = [IsSellerOrAdmin]
    search_fields = ["code"]

    def get_queryset(self):
        user = self.request.user
        if user.role == "admin":
            return Coupon.objects.all()
        return Coupon.objects.filter(Q(seller=user) | Q(seller__isnull=True))

    def perform_create(self, serializer):
        seller = None if self.request.user.role == "admin" else self.request.user
        serializer.save(seller=seller, code=serializer.validated_data["code"].upper())


class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "order_number"
    filterset_fields = ["status", "payment_status"]
    search_fields = ["order_number", "user__email"]

    def get_queryset(self):
        user = self.request.user
        qs = Order.objects.prefetch_related("items", "events").select_related("user")
        if user.role == "admin":
            return qs
        if user.role == "seller":
            return qs.filter(items__seller=user).distinct()
        if user.role == "delivery":
            return qs.filter(delivery_partner=user)
        if user.role == "inventory":
            return qs
        return qs.filter(user=user)

    @action(detail=False, methods=["post"])
    def checkout(self, request):
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        cart = get_cart(request.user)
        items = list(cart.items.select_related("product"))
        if not items:
            return Response({"detail": "Your cart is empty."}, status=400)

        address = Address.objects.filter(pk=data["address_id"], user=request.user).first()
        if not address:
            return Response({"detail": "Delivery address not found."}, status=404)

        for item in items:
            if item.quantity > item.product.stock:
                return Response(
                    {"detail": f"{item.product.name} has only {item.product.stock} left."},
                    status=400,
                )

        with transaction.atomic():
            subtotal = sum((i.subtotal for i in items), Decimal("0.00"))
            discount = Decimal("0.00")
            code = (data.get("coupon_code") or cart.coupon_code or "").upper()
            coupon = Coupon.objects.filter(code=code).first() if code else None
            if coupon:
                valid, message = coupon.is_valid_for(subtotal)
                if not valid:
                    return Response({"detail": message}, status=400)
                discount = coupon.discount_for(subtotal)

            taxable = subtotal - discount
            tax = sum(
                (
                    i.subtotal * i.product.tax_percent / Decimal(100)
                    for i in items
                ),
                Decimal("0.00"),
            ).quantize(Decimal("0.01"))
            shipping = Decimal("0.00") if taxable >= SHIPPING_FREE_ABOVE else SHIPPING_FEE
            total = (taxable + tax + shipping).quantize(Decimal("0.01"))

            if data["payment_method"] == "wallet" and request.user.wallet_balance < total:
                return Response({"detail": "Insufficient wallet balance."}, status=400)

            order = Order.objects.create(
                user=request.user,
                payment_method=data["payment_method"],
                subtotal=subtotal,
                discount=discount,
                tax=tax,
                shipping_fee=shipping,
                total=total,
                coupon_code=code,
                notes=data.get("notes", ""),
                shipping_address={
                    "full_name": address.full_name,
                    "phone": address.phone,
                    "line1": address.line1,
                    "line2": address.line2,
                    "city": address.city,
                    "state": address.state,
                    "postal_code": address.postal_code,
                    "country": address.country,
                },
            )

            commission_rate = Decimal(str(settings.PLATFORM_COMMISSION_PERCENT)) / Decimal(100)
            for item in items:
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    seller=item.product.seller,
                    product_name=item.product.name,
                    thumbnail=item.product.thumbnail,
                    unit_price=item.product.price,
                    quantity=item.quantity,
                    subtotal=item.subtotal,
                    commission=(item.subtotal * commission_rate).quantize(Decimal("0.01")),
                )
                Product.objects.filter(pk=item.product_id).update(
                    stock=F("stock") - item.quantity,
                    sold_count=F("sold_count") + item.quantity,
                )
                StockMovement.objects.create(
                    product=item.product,
                    movement_type="out",
                    quantity=item.quantity,
                    reference=order.order_number,
                    note="Customer order",
                )
                notify(
                    item.product.seller,
                    "New order received",
                    f"{item.quantity} x {item.product.name} ({order.order_number})",
                    "success",
                )

            if data["payment_method"] == "wallet":
                request.user.wallet_balance -= total
                request.user.save(update_fields=["wallet_balance"])
                order.payment_status = "paid"
            elif data["payment_method"] in ("card", "upi"):
                order.payment_status = "paid"  # replace with gateway callback in production
            order.status = "confirmed"
            order.save(update_fields=["payment_status", "status"])

            Payment.objects.create(
                order=order,
                provider=data["payment_method"],
                reference=f"PAY-{order.order_number}",
                amount=total,
                status=order.payment_status,
            )
            OrderEvent.objects.create(order=order, status="pending", note="Order placed")
            OrderEvent.objects.create(
                order=order, status="confirmed", note="Payment confirmed", actor=request.user
            )
            if coupon:
                Coupon.objects.filter(pk=coupon.pk).update(used_count=F("used_count") + 1)

            request.user.loyalty_points += int(total // 100)
            request.user.save(update_fields=["loyalty_points"])

            cart.items.all().delete()
            cart.coupon_code = ""
            cart.save(update_fields=["coupon_code"])

        notify(request.user, "Order placed", f"Order {order.order_number} is confirmed.", "success")
        log_action(request.user, "order.created", order.order_number, request=request)
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="status")
    def set_status(self, request, order_number=None):
        order = self.get_object()
        new_status = request.data.get("status")
        allowed = dict(Order.STATUS)
        if new_status not in allowed:
            return Response({"detail": "Unknown status."}, status=400)
        if request.user.role not in ("admin", "seller", "inventory", "delivery"):
            return Response({"detail": "Not permitted."}, status=403)
        order.status = new_status
        if new_status == "out_for_delivery" and not order.delivery_otp:
            order.issue_delivery_otp()
        if new_status == "delivered":
            order.delivered_at = timezone.now()
            if order.payment_method == "cod":
                order.payment_status = "paid"
        order.save()
        OrderEvent.objects.create(
            order=order,
            status=new_status,
            note=request.data.get("note", ""),
            actor=request.user,
        )
        notify(
            order.user,
            "Order update",
            f"{order.order_number} is now {allowed[new_status].lower()}.",
        )
        return Response(OrderSerializer(order).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, order_number=None):
        order = self.get_object()
        if order.status in ("shipped", "out_for_delivery", "delivered", "cancelled"):
            return Response({"detail": "This order can no longer be cancelled."}, status=400)
        with transaction.atomic():
            for item in order.items.all():
                Product.objects.filter(pk=item.product_id).update(
                    stock=F("stock") + item.quantity
                )
                StockMovement.objects.create(
                    product=item.product,
                    movement_type="in",
                    quantity=item.quantity,
                    reference=order.order_number,
                    note="Order cancelled",
                )
            order.status = "cancelled"
            if order.payment_status == "paid":
                order.payment_status = "refunded"
                order.user.wallet_balance += order.total
                order.user.save(update_fields=["wallet_balance"])
            order.save()
            OrderEvent.objects.create(
                order=order, status="cancelled", note="Cancelled by user", actor=request.user
            )
        return Response(OrderSerializer(order).data)

    @action(detail=True, methods=["post"], url_path="assign-delivery", permission_classes=[IsAdmin])
    def assign_delivery(self, request, order_number=None):
        from apps.accounts.models import User

        order = self.get_object()
        partner = User.objects.filter(pk=request.data.get("partner_id"), role="delivery").first()
        if not partner:
            return Response({"detail": "Delivery partner not found."}, status=404)
        order.delivery_partner = partner
        order.status = "out_for_delivery"
        order.issue_delivery_otp()
        order.save()
        OrderEvent.objects.create(
            order=order, status="out_for_delivery", note=f"Assigned to {partner.email}"
        )
        notify(partner, "New delivery assigned", order.order_number)
        notify(order.user, "Out for delivery", f"Share OTP {order.delivery_otp} on arrival.")
        return Response(OrderSerializer(order).data)

    @action(
        detail=True,
        methods=["post"],
        url_path="confirm-delivery",
        permission_classes=[IsDeliveryPartner],
    )
    def confirm_delivery(self, request, order_number=None):
        order = self.get_object()
        if request.data.get("otp") != order.delivery_otp:
            return Response({"detail": "Incorrect OTP."}, status=400)
        order.status = "delivered"
        order.delivered_at = timezone.now()
        if order.payment_method == "cod":
            order.payment_status = "paid"
        order.delivery_otp = ""
        order.save()
        OrderEvent.objects.create(
            order=order, status="delivered", note="OTP verified", actor=request.user
        )
        notify(order.user, "Delivered", f"{order.order_number} was delivered. Enjoy!", "success")
        return Response(OrderSerializer(order).data)

    @action(detail=True, methods=["get"])
    def invoice(self, request, order_number=None):
        order = self.get_object()
        return Response(
            {
                "invoice_number": f"INV-{order.order_number}",
                "issued_at": order.created_at,
                "billed_to": order.shipping_address,
                "items": [
                    {
                        "name": i.product_name,
                        "quantity": i.quantity,
                        "unit_price": i.unit_price,
                        "subtotal": i.subtotal,
                    }
                    for i in order.items.all()
                ],
                "subtotal": order.subtotal,
                "discount": order.discount,
                "tax": order.tax,
                "shipping_fee": order.shipping_fee,
                "total": order.total,
                "payment_method": order.get_payment_method_display(),
                "payment_status": order.payment_status,
            }
        )


class ReturnRequestViewSet(viewsets.ModelViewSet):
    serializer_class = ReturnRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == "admin":
            return ReturnRequest.objects.select_related("order")
        return ReturnRequest.objects.filter(order__user=user)

    def perform_create(self, serializer):
        order = serializer.validated_data["order"]
        if order.user != self.request.user:
            raise PermissionError("Not your order.")
        serializer.save()

    @action(detail=True, methods=["post"], permission_classes=[IsAdmin])
    def approve(self, request, pk=None):
        rr = self.get_object()
        rr.status = "refunded"
        rr.refund_amount = rr.order.total
        rr.save()
        order = rr.order
        order.status = "refunded"
        order.payment_status = "refunded"
        order.save(update_fields=["status", "payment_status"])
        order.user.wallet_balance += rr.refund_amount
        order.user.save(update_fields=["wallet_balance"])
        notify(order.user, "Refund processed", f"{rr.refund_amount} added to your wallet.", "success")
        return Response(self.get_serializer(rr).data)


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Payment.objects.select_related("order")
        return qs if user.role == "admin" else qs.filter(order__user=user)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def sales_report(request):
    """Revenue grouped by day for the last 30 days."""
    user = request.user
    since = timezone.now() - timezone.timedelta(days=30)
    items = OrderItem.objects.filter(order__created_at__gte=since).exclude(
        order__status__in=["cancelled", "refunded"]
    )
    if user.role == "seller":
        items = items.filter(seller=user)
    elif user.role not in ("admin", "inventory"):
        items = items.filter(order__user=user)
    buckets = {}
    for item in items.select_related("order"):
        key = item.order.created_at.date().isoformat()
        buckets[key] = buckets.get(key, Decimal("0")) + item.subtotal
    series = [{"date": k, "revenue": v} for k, v in sorted(buckets.items())]
    return Response(
        {
            "series": series,
            "total": sum((row["revenue"] for row in series), Decimal("0")),
            "units": items.aggregate(units=Sum("quantity"))["units"] or 0,
        }
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def public_coupons(request):
    coupons = Coupon.objects.filter(is_active=True, seller__isnull=True)[:6]
    return Response(CouponSerializer(coupons, many=True).data)
