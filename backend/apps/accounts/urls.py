from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from .views import (
    AddressViewSet,
    ChangePasswordView,
    LoginView,
    MeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RegisterView,
    ResendCodeView,
    SellerProfileViewSet,
    UserViewSet,
    VerifyEmailView,
)

router = DefaultRouter()
router.register("addresses", AddressViewSet, basename="address")
router.register("sellers", SellerProfileViewSet, basename="seller")
router.register("users", UserViewSet, basename="user")

urlpatterns = [
    path("register/", RegisterView.as_view()),
    path("login/", LoginView.as_view()),
    path("refresh/", TokenRefreshView.as_view()),
    path("verify-token/", TokenVerifyView.as_view()),
    path("me/", MeView.as_view()),
    path("change-password/", ChangePasswordView.as_view()),
    path("verify-email/", VerifyEmailView.as_view()),
    path("resend-code/", ResendCodeView.as_view()),
    path("password-reset/", PasswordResetRequestView.as_view()),
    path("password-reset/confirm/", PasswordResetConfirmView.as_view()),
    path("", include(router.urls)),
]
