from django.db.models import Count, Sum
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import IsAdmin
from apps.catalog.models import Product
from apps.orders.models import Order

from .models import AuditLog, Notification, SupportTicket
from .serializers import AuditLogSerializer, NotificationSerializer, SupportTicketSerializer


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    return Response({"status": "ok", "time": timezone.now()})


class NotificationViewSet(
    mixins.ListModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet
):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    @action(detail=False, methods=["post"], url_path="read-all")
    def read_all(self, request):
        self.get_queryset().update(is_read=True)
        return Response({"detail": "All notifications marked as read."})

    @action(detail=True, methods=["post"])
    def read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save(update_fields=["is_read"])
        return Response(NotificationSerializer(notification).data)


class SupportTicketViewSet(viewsets.ModelViewSet):
    serializer_class = SupportTicketSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == "admin":
            return SupportTicket.objects.all()
        return SupportTicket.objects.filter(user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class AuditLogViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdmin]
    queryset = AuditLog.objects.select_related("actor").all()
    search_fields = ["action", "target"]


@api_view(["GET"])
@permission_classes([IsAdmin])
def admin_dashboard(request):
    from apps.accounts.models import User

    paid_orders = Order.objects.exclude(status__in=["cancelled", "refunded"])
    revenue = paid_orders.aggregate(total=Sum("total"))["total"] or 0
    by_status = list(paid_orders.values("status").annotate(count=Count("id")))
    top_products = list(
        Product.objects.filter(is_active=True)
        .order_by("-sold_count")[:5]
        .values("id", "name", "sold_count", "price")
    )
    return Response(
        {
            "revenue": revenue,
            "orders": Order.objects.count(),
            "customers": User.objects.filter(role="customer").count(),
            "sellers": User.objects.filter(role="seller").count(),
            "pending_sellers": User.objects.filter(role="seller", seller_profile__is_approved=False).count(),
            "products": Product.objects.count(),
            "pending_products": Product.objects.filter(status="pending").count(),
            "orders_by_status": by_status,
            "top_products": top_products,
        },
        status=status.HTTP_200_OK,
    )
