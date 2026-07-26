from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CartViewSet,
    CouponViewSet,
    OrderViewSet,
    PaymentViewSet,
    ReturnRequestViewSet,
    public_coupons,
    sales_report,
)

router = DefaultRouter()
router.register("cart", CartViewSet, basename="cart")
router.register("coupons", CouponViewSet, basename="coupon")
router.register("orders", OrderViewSet, basename="order")
router.register("returns", ReturnRequestViewSet, basename="return")
router.register("payments", PaymentViewSet, basename="payment")

urlpatterns = [
    path("reports/sales/", sales_report),
    path("public-coupons/", public_coupons),
    path("", include(router.urls)),
]
