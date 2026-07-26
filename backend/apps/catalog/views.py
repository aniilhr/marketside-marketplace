import django_filters
from django.db.models import Count, F, Q, Sum
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import IsAdmin, IsSeller, ReadOnlyOrSellerOwner
from apps.core.services import log_action, notify
from apps.orders.models import OrderItem

from .models import Brand, Category, Product, RecentlyViewed, Review, Wishlist
from .serializers import (
    BrandSerializer,
    CategorySerializer,
    ProductDetailSerializer,
    ProductListSerializer,
    ProductWriteSerializer,
    RecentlyViewedSerializer,
    ReviewSerializer,
    WishlistSerializer,
)


class ProductFilter(django_filters.FilterSet):
    min_price = django_filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = django_filters.NumberFilter(field_name="price", lookup_expr="lte")
    min_rating = django_filters.NumberFilter(field_name="rating", lookup_expr="gte")
    category = django_filters.CharFilter(method="filter_category")
    brand = django_filters.CharFilter(field_name="brand__slug")
    seller = django_filters.NumberFilter(field_name="seller_id")
    in_stock = django_filters.BooleanFilter(method="filter_in_stock")

    class Meta:
        model = Product
        fields = ["is_featured", "status"]

    def filter_category(self, queryset, name, value):
        return queryset.filter(Q(category__slug=value) | Q(category__parent__slug=value))

    def filter_in_stock(self, queryset, name, value):
        return queryset.filter(stock__gt=0) if value else queryset.filter(stock=0)


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    lookup_field = "slug"
    search_fields = ["name"]

    def get_permissions(self):
        return [AllowAny()] if self.action in ("list", "retrieve") else [IsAdmin()]

    def get_queryset(self):
        qs = Category.objects.annotate(product_count=Count("products"))
        if self.action == "list" and self.request.query_params.get("tree", "1") == "1":
            return qs.filter(parent__isnull=True, is_active=True)
        return qs


class BrandViewSet(viewsets.ModelViewSet):
    serializer_class = BrandSerializer
    queryset = Brand.objects.all()
    lookup_field = "slug"
    search_fields = ["name"]

    def get_permissions(self):
        return [AllowAny()] if self.action in ("list", "retrieve") else [IsAdmin()]


class ProductViewSet(viewsets.ModelViewSet):
    permission_classes = [ReadOnlyOrSellerOwner]
    lookup_field = "slug"
    filterset_class = ProductFilter
    search_fields = ["name", "short_description", "sku", "brand__name", "category__name"]
    ordering_fields = ["price", "rating", "created_at", "sold_count", "view_count"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = Product.objects.select_related("category", "brand", "seller__seller_profile")
        user = self.request.user
        mine = self.request.query_params.get("mine") == "1"
        if mine and user.is_authenticated:
            return qs.filter(seller=user)
        if user.is_authenticated and user.role == "admin":
            return qs
        return qs.filter(status="approved", is_active=True)

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return ProductWriteSerializer
        if self.action == "retrieve":
            return ProductDetailSerializer
        return ProductListSerializer

    def perform_create(self, serializer):
        status_value = "approved" if self.request.user.role == "admin" else "pending"
        product = serializer.save(seller=self.request.user, status=status_value)
        log_action(self.request.user, "product.created", product.name, request=self.request)

    def retrieve(self, request, *args, **kwargs):
        product = self.get_object()
        Product.objects.filter(pk=product.pk).update(view_count=F("view_count") + 1)
        if request.user.is_authenticated:
            RecentlyViewed.objects.update_or_create(user=request.user, product=product)
        return Response(self.get_serializer(product).data)

    @action(detail=True, methods=["post"], permission_classes=[IsAdmin])
    def approve(self, request, slug=None):
        product = self.get_object()
        product.status = "approved"
        product.save(update_fields=["status"])
        notify(product.seller, "Product approved", f"{product.name} is now live.", "success")
        log_action(request.user, "product.approved", product.name, request=request)
        return Response(ProductDetailSerializer(product).data)

    @action(detail=True, methods=["post"], permission_classes=[IsAdmin])
    def reject(self, request, slug=None):
        product = self.get_object()
        product.status = "rejected"
        product.save(update_fields=["status"])
        notify(
            product.seller,
            "Product rejected",
            request.data.get("reason", "Please review the listing details."),
            "warning",
        )
        return Response(ProductDetailSerializer(product).data)

    @action(detail=False, methods=["get"], permission_classes=[AllowAny])
    def featured(self, request):
        qs = self.get_queryset().filter(is_featured=True)[:12]
        return Response(ProductListSerializer(qs, many=True).data)

    @action(detail=False, methods=["get"], permission_classes=[AllowAny])
    def trending(self, request):
        qs = self.get_queryset().order_by("-sold_count", "-view_count")[:12]
        return Response(ProductListSerializer(qs, many=True).data)

    @action(detail=True, methods=["get"], permission_classes=[AllowAny])
    def related(self, request, slug=None):
        product = self.get_object()
        qs = (
            self.get_queryset()
            .filter(category=product.category)
            .exclude(pk=product.pk)
            .order_by("-rating")[:8]
        )
        return Response(ProductListSerializer(qs, many=True).data)

    @action(detail=True, methods=["get"], url_path="bought-together", permission_classes=[AllowAny])
    def bought_together(self, request, slug=None):
        product = self.get_object()
        order_ids = OrderItem.objects.filter(product=product).values_list("order_id", flat=True)
        product_ids = (
            OrderItem.objects.filter(order_id__in=order_ids)
            .exclude(product=product)
            .values("product_id")
            .annotate(times=Count("id"))
            .order_by("-times")[:6]
        )
        qs = self.get_queryset().filter(id__in=[p["product_id"] for p in product_ids])
        return Response(ProductListSerializer(qs, many=True).data)

    @action(detail=False, methods=["post"], permission_classes=[IsSeller], url_path="bulk-upload")
    def bulk_upload(self, request):
        """Accepts a JSON array of product rows (parsed client-side from CSV/Excel)."""
        rows = request.data.get("products", [])
        created, errors = [], []
        for index, row in enumerate(rows):
            serializer = ProductWriteSerializer(data=row)
            if serializer.is_valid():
                product = serializer.save(seller=request.user, status="pending")
                created.append(product.id)
            else:
                errors.append({"row": index + 1, "errors": serializer.errors})
        return Response(
            {"created": len(created), "errors": errors},
            status=status.HTTP_201_CREATED if created else status.HTTP_400_BAD_REQUEST,
        )


class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewSerializer
    filterset_fields = ["product", "rating"]

    def get_permissions(self):
        return [AllowAny()] if self.action in ("list", "retrieve") else [IsAuthenticated()]

    def get_queryset(self):
        return Review.objects.select_related("user", "product")

    def perform_create(self, serializer):
        product = serializer.validated_data["product"]
        purchased = OrderItem.objects.filter(
            order__user=self.request.user, product=product, order__status="delivered"
        ).exists()
        review = serializer.save(user=self.request.user, is_verified_purchase=purchased)
        review.product.recalculate_rating()

    def perform_destroy(self, instance):
        product = instance.product
        instance.delete()
        product.recalculate_rating()


class WishlistViewSet(viewsets.ModelViewSet):
    serializer_class = WishlistSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "delete"]

    def get_queryset(self):
        return Wishlist.objects.filter(user=self.request.user).select_related("product")

    def create(self, request, *args, **kwargs):
        product_id = request.data.get("product")
        item, created = Wishlist.objects.get_or_create(
            user=request.user, product_id=product_id
        )
        if not created:
            item.delete()
            return Response({"detail": "Removed from wishlist.", "active": False})
        return Response(
            {"detail": "Added to wishlist.", "active": True}, status=status.HTTP_201_CREATED
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def recently_viewed(request):
    qs = RecentlyViewed.objects.filter(user=request.user).select_related("product")[:10]
    return Response(RecentlyViewedSerializer(qs, many=True).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def recommendations(request):
    """Content-based recommendations from browsing and purchase history."""
    viewed_categories = (
        RecentlyViewed.objects.filter(user=request.user)
        .values_list("product__category_id", flat=True)
        .distinct()
    )
    bought_categories = (
        OrderItem.objects.filter(order__user=request.user)
        .values_list("product__category_id", flat=True)
        .distinct()
    )
    category_ids = set(viewed_categories) | set(bought_categories)
    qs = Product.objects.filter(status="approved", is_active=True)
    if category_ids:
        qs = qs.filter(category_id__in=category_ids)
    qs = qs.exclude(
        id__in=OrderItem.objects.filter(order__user=request.user).values_list(
            "product_id", flat=True
        )
    ).order_by("-rating", "-sold_count")[:12]
    return Response(ProductListSerializer(qs, many=True).data)


@api_view(["GET"])
@permission_classes([AllowAny])
def search_suggestions(request):
    query = request.query_params.get("q", "").strip()
    if len(query) < 2:
        return Response({"products": [], "categories": []})
    products = Product.objects.filter(
        Q(name__icontains=query) | Q(sku__icontains=query),
        status="approved",
        is_active=True,
    ).values("name", "slug", "thumbnail")[:6]
    categories = Category.objects.filter(name__icontains=query).values("name", "slug")[:4]
    return Response({"products": list(products), "categories": list(categories)})


@api_view(["GET"])
@permission_classes([IsSeller])
def seller_dashboard(request):
    products = Product.objects.filter(seller=request.user)
    items = OrderItem.objects.filter(seller=request.user).exclude(
        order__status__in=["cancelled", "refunded"]
    )
    revenue = items.aggregate(total=Sum("subtotal"))["total"] or 0
    return Response(
        {
            "revenue": revenue,
            "orders": items.values("order_id").distinct().count(),
            "products": products.count(),
            "pending_products": products.filter(status="pending").count(),
            "low_stock": products.filter(stock__lte=F("low_stock_threshold")).count(),
            "top_products": list(
                products.order_by("-sold_count")[:5].values("id", "name", "sold_count", "stock")
            ),
        }
    )
