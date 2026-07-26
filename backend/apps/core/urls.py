from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AuditLogViewSet,
    NotificationViewSet,
    SupportTicketViewSet,
    admin_dashboard,
    health,
)

router = DefaultRouter()
router.register("notifications", NotificationViewSet, basename="notification")
router.register("support-tickets", SupportTicketViewSet, basename="ticket")
router.register("audit-logs", AuditLogViewSet, basename="audit-log")

urlpatterns = [
    path("health/", health),
    path("admin/dashboard/", admin_dashboard),
    path("", include(router.urls)),
]
