import secrets

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("role", "admin")
        extra.setdefault("is_verified", True)
        return self._create_user(email, password, **extra)


class User(AbstractUser):
    ROLES = [
        ("customer", "Customer"),
        ("seller", "Seller"),
        ("admin", "Admin"),
        ("inventory", "Inventory Manager"),
        ("delivery", "Delivery Partner"),
    ]

    username = None
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    role = models.CharField(max_length=20, choices=ROLES, default="customer")
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    wallet_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    loyalty_points = models.IntegerField(default=0)
    referral_code = models.CharField(max_length=12, unique=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.referral_code = secrets.token_hex(4).upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email


class SellerProfile(TimeStampedModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="seller_profile")
    store_name = models.CharField(max_length=150)
    store_slug = models.SlugField(max_length=170, unique=True)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to="stores/", blank=True, null=True)
    banner = models.ImageField(upload_to="stores/", blank=True, null=True)
    gst_number = models.CharField(max_length=40, blank=True)
    is_approved = models.BooleanField(default=False)
    approved_at = models.DateTimeField(null=True, blank=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)

    def approve(self):
        self.is_approved = True
        self.approved_at = timezone.now()
        self.save(update_fields=["is_approved", "approved_at"])

    def __str__(self):
        return self.store_name


class Address(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="addresses")
    label = models.CharField(max_length=40, default="Home")
    full_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=20)
    line1 = models.CharField(max_length=200)
    line2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=80)
    state = models.CharField(max_length=80)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=80, default="India")
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ["-is_default", "-created_at"]
        verbose_name_plural = "addresses"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_default:
            Address.objects.filter(user=self.user).exclude(pk=self.pk).update(is_default=False)

    def __str__(self):
        return f"{self.label} - {self.city}"


class OTPCode(TimeStampedModel):
    PURPOSES = [("verify", "Email verification"), ("reset", "Password reset")]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="otp_codes")
    code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=12, choices=PURPOSES)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)

    @classmethod
    def issue(cls, user, purpose, minutes=15):
        cls.objects.filter(user=user, purpose=purpose, used=False).update(used=True)
        return cls.objects.create(
            user=user,
            code=f"{secrets.randbelow(1000000):06d}",
            purpose=purpose,
            expires_at=timezone.now() + timezone.timedelta(minutes=minutes),
        )

    @property
    def is_valid(self):
        return not self.used and self.expires_at > timezone.now()
