from django.contrib import admin

from .models import Brand, Category, Product, ProductImage, RecentlyViewed, Review, Wishlist


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "seller", "price", "stock", "status", "is_active"]
    list_filter = ["status", "is_active", "category"]
    search_fields = ["name", "sku"]


admin.site.register([Category, Brand, ProductImage, Review, Wishlist, RecentlyViewed])
