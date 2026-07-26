from django.core.mail import send_mail
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.core.services import log_action, notify

from .models import Address, OTPCode, SellerProfile, User
from .permissions import IsAdmin
from .serializers import (
    AddressSerializer,
    ChangePasswordSerializer,
    LoginSerializer,
    OTPVerifySerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    SellerProfileSerializer,
    UserSerializer,
)


def send_code(user, otp, subject):
    send_mail(
        subject,
        f"Your verification code is {otp.code}. It expires in 15 minutes.",
        None,
        [user.email],
        fail_silently=True,
    )


class RegisterView(GenericAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        otp = user.otp_codes.filter(purpose="verify", used=False).first()
        if otp:
            send_code(user, otp, "Verify your marketplace account")
        notify(user, "Welcome aboard", "Verify your email to unlock every feature.", "success")
        log_action(user, "user.registered", user.email, request=request)
        return Response(
            {"user": UserSerializer(user).data, "detail": "Account created. Check email for the code."},
            status=status.HTTP_201_CREATED,
        )


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]


class MeView(GenericAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(self.get_serializer(request.user).data)

    def patch(self, request):
        serializer = self.get_serializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ChangePasswordView(GenericAPIView):
    serializer_class = ChangePasswordSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not user.check_password(serializer.validated_data["old_password"]):
            return Response({"detail": "Current password is incorrect."}, status=400)
        user.set_password(serializer.validated_data["new_password"])
        user.save()
        log_action(user, "user.password_changed", user.email, request=request)
        return Response({"detail": "Password updated."})


class VerifyEmailView(GenericAPIView):
    serializer_class = OTPVerifySerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(email=serializer.validated_data["email"]).first()
        otp = (
            OTPCode.objects.filter(
                user=user, purpose="verify", code=serializer.validated_data["code"]
            ).first()
            if user
            else None
        )
        if not otp or not otp.is_valid:
            return Response({"detail": "Invalid or expired code."}, status=400)
        otp.used = True
        otp.save(update_fields=["used"])
        user.is_verified = True
        user.save(update_fields=["is_verified"])
        return Response({"detail": "Email verified."})


class ResendCodeView(GenericAPIView):
    serializer_class = PasswordResetRequestSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(email=serializer.validated_data["email"]).first()
        if user:
            send_code(user, OTPCode.issue(user, "verify"), "Your new verification code")
        return Response({"detail": "If the account exists, a code has been sent."})


class PasswordResetRequestView(GenericAPIView):
    serializer_class = PasswordResetRequestSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(email=serializer.validated_data["email"]).first()
        if user:
            send_code(user, OTPCode.issue(user, "reset"), "Reset your password")
        return Response({"detail": "If the account exists, a reset code has been sent."})


class PasswordResetConfirmView(GenericAPIView):
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = User.objects.filter(email=data["email"]).first()
        otp = (
            OTPCode.objects.filter(user=user, purpose="reset", code=data["code"]).first()
            if user
            else None
        )
        if not otp or not otp.is_valid:
            return Response({"detail": "Invalid or expired code."}, status=400)
        otp.used = True
        otp.save(update_fields=["used"])
        user.set_password(data["new_password"])
        user.save()
        log_action(user, "user.password_reset", user.email, request=request)
        return Response({"detail": "Password reset. You can sign in now."})


class AddressViewSet(viewsets.ModelViewSet):
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class SellerProfileViewSet(viewsets.ModelViewSet):
    serializer_class = SellerProfileSerializer
    queryset = SellerProfile.objects.select_related("user").all()
    search_fields = ["store_name", "user__email"]
    filterset_fields = ["is_approved"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [AllowAny()]
        if self.action in ("approve", "reject"):
            return [IsAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if self.action in ("list", "retrieve") and not (
            user.is_authenticated and user.role == "admin"
        ):
            return qs.filter(is_approved=True)
        return qs

    def get_object(self):
        if self.kwargs.get("pk") == "me":
            return self.request.user.seller_profile
        return super().get_object()

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        profile = self.get_object()
        profile.approve()
        notify(profile.user, "Store approved", "Your store is live. Start listing products.", "success")
        log_action(request.user, "seller.approved", profile.store_name, request=request)
        return Response(self.get_serializer(profile).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        profile = self.get_object()
        profile.is_approved = False
        profile.save(update_fields=["is_approved"])
        notify(profile.user, "Store needs changes", request.data.get("reason", ""), "warning")
        return Response(self.get_serializer(profile).data)


class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    permission_classes = [IsAdmin]
    queryset = User.objects.all().order_by("-date_joined")
    search_fields = ["email", "full_name", "phone"]
    filterset_fields = ["role", "is_active", "is_verified"]

    @action(detail=True, methods=["post"], url_path="set-role")
    def set_role(self, request, pk=None):
        user = self.get_object()
        role = request.data.get("role")
        if role not in dict(User.ROLES):
            return Response({"detail": "Unknown role."}, status=400)
        user.role = role
        user.save(update_fields=["role"])
        log_action(request.user, "user.role_changed", user.email, {"role": role}, request)
        return Response(self.get_serializer(user).data)

    @action(detail=True, methods=["post"], url_path="toggle-active")
    def toggle_active(self, request, pk=None):
        user = self.get_object()
        user.is_active = not user.is_active
        user.save(update_fields=["is_active"])
        return Response(self.get_serializer(user).data)
