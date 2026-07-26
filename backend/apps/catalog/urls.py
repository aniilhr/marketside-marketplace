from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    BrandViewSet,
    CategoryViewSet,
    ProductViewSet,
    ReviewViewSet,
    WishlistViewSet,
    recently_viewed,
    recommendations,
    search_suggestions,
    seller_dashboard,
)

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("brands", BrandViewSet, basename="brand")
router.register("products", ProductViewSet, basename="product")
router.register("reviews", ReviewViewSet, basename="review")
router.register("wishlist", WishlistViewSet, basename="wishlist")

urlpatterns = [
    path("recently-viewed/", recently_viewed),
    path("recommendations/", recommendations),
    path("search-suggestions/", search_suggestions),
    path("seller/dashboard/", seller_dashboard),
    path("", include(router.urls)),
]
