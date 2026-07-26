from rest_framework import serializers

from .models import Brand, Category, Product, ProductImage, RecentlyViewed, Review, Wishlist


class CategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    product_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Category
        fields = ["id", "name", "slug", "parent", "image", "icon", "is_active", "children", "product_count"]

    def get_children(self, obj):
        return CategorySerializer(obj.children.filter(is_active=True), many=True).data


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ["id", "name", "slug", "logo"]


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "image", "url", "alt_text", "position"]


class ReviewSerializer(serializers.ModelSerializer):
    author = serializers.CharField(source="user.full_name", read_only=True)

    class Meta:
        model = Review
        fields = [
            "id",
            "product",
            "author",
            "rating",
            "title",
            "comment",
            "is_verified_purchase",
            "created_at",
        ]
        read_only_fields = ["is_verified_purchase", "created_at"]


class ProductListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    brand_name = serializers.CharField(source="brand.name", read_only=True, default="")
    store_name = serializers.CharField(
        source="seller.seller_profile.store_name", read_only=True, default=""
    )
    discount_percent = serializers.IntegerField(read_only=True)
    in_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "slug",
            "sku",
            "price",
            "compare_at_price",
            "discount_percent",
            "thumbnail",
            "rating",
            "review_count",
            "stock",
            "in_stock",
            "is_featured",
            "category_name",
            "brand_name",
            "store_name",
            "sold_count",
            "status",
            "created_at",
        ]


class ProductDetailSerializer(ProductListSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    reviews = ReviewSerializer(many=True, read_only=True)

    class Meta(ProductListSerializer.Meta):
        fields = ProductListSerializer.Meta.fields + [
            "short_description",
            "description",
            "tax_percent",
            "category",
            "brand",
            "images",
            "reviews",
            "view_count",
            "is_active",
        ]


class ProductWriteSerializer(serializers.ModelSerializer):
    image_urls = serializers.ListField(
        child=serializers.URLField(), write_only=True, required=False
    )

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "sku",
            "category",
            "brand",
            "short_description",
            "description",
            "price",
            "compare_at_price",
            "cost_price",
            "tax_percent",
            "stock",
            "low_stock_threshold",
            "weight_grams",
            "thumbnail",
            "is_active",
            "is_featured",
            "status",
            "image_urls",
        ]
        read_only_fields = ["status"]

    def create(self, validated_data):
        urls = validated_data.pop("image_urls", [])
        product = Product.objects.create(**validated_data)
        for index, url in enumerate(urls):
            ProductImage.objects.create(product=product, url=url, position=index)
        if urls and not product.thumbnail:
            product.thumbnail = urls[0]
            product.save(update_fields=["thumbnail"])
        return product

    def update(self, instance, validated_data):
        urls = validated_data.pop("image_urls", None)
        product = super().update(instance, validated_data)
        if urls is not None:
            product.images.all().delete()
            for index, url in enumerate(urls):
                ProductImage.objects.create(product=product, url=url, position=index)
        return product


class WishlistSerializer(serializers.ModelSerializer):
    product_detail = ProductListSerializer(source="product", read_only=True)

    class Meta:
        model = Wishlist
        fields = ["id", "product", "product_detail", "created_at"]


class RecentlyViewedSerializer(serializers.ModelSerializer):
    product_detail = ProductListSerializer(source="product", read_only=True)

    class Meta:
        model = RecentlyViewed
        fields = ["id", "product_detail", "updated_at"]
