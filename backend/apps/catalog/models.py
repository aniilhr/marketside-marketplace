from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.text import slugify

from apps.core.models import TimeStampedModel


class Category(TimeStampedModel):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="children"
    )
    image = models.ImageField(upload_to="categories/", blank=True, null=True)
    icon = models.CharField(max_length=40, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Brand(TimeStampedModel):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    logo = models.ImageField(upload_to="brands/", blank=True, null=True)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(TimeStampedModel):
    STATUS = [
        ("draft", "Draft"),
        ("pending", "Pending approval"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="products"
    )
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="products"
    )
    brand = models.ForeignKey(
        Brand, null=True, blank=True, on_delete=models.SET_NULL, related_name="products"
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    sku = models.CharField(max_length=60, unique=True)
    short_description = models.CharField(max_length=300, blank=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    compare_at_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    stock = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=10)
    weight_grams = models.PositiveIntegerField(default=0)
    thumbnail = models.URLField(blank=True)
    status = models.CharField(max_length=12, choices=STATUS, default="pending")
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    review_count = models.PositiveIntegerField(default=0)
    view_count = models.PositiveIntegerField(default=0)
    sold_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "is_active"]),
            models.Index(fields=["-sold_count"]),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)[:200]
            slug, counter = base, 1
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                counter += 1
                slug = f"{base}-{counter}"
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def discount_percent(self):
        if self.compare_at_price and self.compare_at_price > self.price:
            return int(
                (self.compare_at_price - self.price) / self.compare_at_price * Decimal(100)
            )
        return 0

    @property
    def in_stock(self):
        return self.stock > 0

    def recalculate_rating(self):
        stats = self.reviews.aggregate(
            avg=models.Avg("rating"), total=models.Count("id")
        )
        self.rating = round(stats["avg"] or 0, 2)
        self.review_count = stats["total"] or 0
        self.save(update_fields=["rating", "review_count"])

    def __str__(self):
        return self.name


class ProductImage(TimeStampedModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="products/", blank=True, null=True)
    url = models.URLField(blank=True)
    alt_text = models.CharField(max_length=160, blank=True)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "id"]


class Review(TimeStampedModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews"
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    title = models.CharField(max_length=140, blank=True)
    comment = models.TextField(blank=True)
    is_verified_purchase = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("product", "user")

    def __str__(self):
        return f"{self.product} - {self.rating}star"


class Wishlist(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wishlist"
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("user", "product")
        ordering = ["-created_at"]


class RecentlyViewed(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="recently_viewed"
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("user", "product")
        ordering = ["-updated_at"]
