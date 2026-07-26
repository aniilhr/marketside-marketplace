from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Address, OTPCode, SellerProfile, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ["email"]
    list_display = ["email", "full_name", "role", "is_verified", "is_active"]
    list_filter = ["role", "is_active", "is_verified"]
    search_fields = ["email", "full_name"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profile", {"fields": ("full_name", "phone", "avatar", "role", "is_verified")}),
        ("Rewards", {"fields": ("wallet_balance", "loyalty_points", "referral_code")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups")}),
    )
    add_fieldsets = (
        (None, {"fields": ("email", "password1", "password2", "role")}),
    )


admin.site.register([SellerProfile, Address, OTPCode])
