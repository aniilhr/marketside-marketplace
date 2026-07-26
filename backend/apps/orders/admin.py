from django.contrib import admin

from .models import Cart, CartItem, Coupon, Order, OrderEvent, OrderItem, Payment, ReturnRequest


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["order_number", "user", "status", "payment_status", "total", "created_at"]
    list_filter = ["status", "payment_status", "payment_method"]
    search_fields = ["order_number", "user__email"]


admin.site.register([Cart, CartItem, Coupon, OrderItem, OrderEvent, Payment, ReturnRequest])
