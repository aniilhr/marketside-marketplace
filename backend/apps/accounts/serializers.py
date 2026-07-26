from django.contrib.auth.password_validation import validate_password
from django.utils.text import slugify
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Address, OTPCode, SellerProfile, User


class UserSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(
        source="seller_profile.store_name", read_only=True, default=""
    )
    is_approved_seller = serializers.BooleanField(
        source="seller_profile.is_approved", read_only=True, default=False
    )

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "full_name",
            "phone",
            "role",
            "avatar",
            "is_verified",
            "wallet_balance",
            "loyalty_points",
            "referral_code",
            "store_name",
            "is_approved_seller",
            "date_joined",
        ]
        read_only_fields = ["role", "is_verified", "wallet_balance", "loyalty_points"]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    store_name = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ["email", "full_name", "phone", "password", "role", "store_name"]

    def validate_role(self, value):
        if value == "admin":
            raise serializers.ValidationError("Admin accounts are created by an administrator.")
        return value

    def create(self, validated_data):
        store_name = validated_data.pop("store_name", "")
        password = validated_data.pop("password")
        user = User.objects.create_user(password=password, **validated_data)
        if user.role == "seller":
            base = slugify(store_name or user.email.split("@")[0])
            slug, counter = base, 1
            while SellerProfile.objects.filter(store_slug=slug).exists():
                counter += 1
                slug = f"{base}-{counter}"
            SellerProfile.objects.create(
                user=user, store_name=store_name or f"{user.full_name}'s Store", store_slug=slug
            )
        OTPCode.issue(user, "verify")
        return user


class LoginSerializer(TokenObtainPairSerializer):
    username_field = "email"

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        token["email"] = user.email
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        return data


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField()
    new_password = serializers.CharField(validators=[validate_password])


class OTPVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6)


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6)
    new_password = serializers.CharField(validators=[validate_password])


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        exclude = ["user"]


class SellerProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    owner = serializers.CharField(source="user.full_name", read_only=True)

    class Meta:
        model = SellerProfile
        fields = [
            "id",
            "email",
            "owner",
            "store_name",
            "store_slug",
            "description",
            "logo",
            "banner",
            "gst_number",
            "is_approved",
            "approved_at",
            "rating",
        ]
        read_only_fields = ["store_slug", "is_approved", "approved_at", "rating"]
