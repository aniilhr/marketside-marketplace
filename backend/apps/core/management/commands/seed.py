import random
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import Address, SellerProfile, User
from apps.catalog.models import Brand, Category, Product, ProductImage, Review
from apps.inventory.models import StockItem, Supplier, Warehouse
from apps.orders.models import Coupon

CATEGORIES = {
    "Electronics": ["Smartphones", "Laptops", "Audio", "Wearables"],
    "Home & Kitchen": ["Cookware", "Storage", "Lighting"],
    "Fashion": ["Men", "Women", "Footwear"],
    "Books": ["Fiction", "Technology"],
}

BRANDS = ["Nordwave", "Kaviro", "Lumen", "Tessel", "Aurex", "Pinemark"]

PRODUCTS = [
    ("Nordwave Pulse 7 Smartphone", "Smartphones", 28999, 34999),
    ("Nordwave Pulse Lite", "Smartphones", 15499, 18999),
    ("Kaviro UltraBook 14", "Laptops", 68999, 79999),
    ("Kaviro Studio 16 Creator Laptop", "Laptops", 112000, 125000),
    ("Lumen Drift ANC Headphones", "Audio", 7499, 9999),
    ("Lumen Pod Wireless Earbuds", "Audio", 2999, 4499),
    ("Tessel Track Fitness Watch", "Wearables", 5499, 6999),
    ("Aurex Triply Steel Wok", "Cookware", 2199, 2899),
    ("Aurex Cast Iron Skillet 26cm", "Cookware", 1899, 2499),
    ("Pinemark Airtight Jar Set of 6", "Storage", 999, 1499),
    ("Lumen Arc Desk Lamp", "Lighting", 1799, 2299),
    ("Pinemark Merino Crew Sweater", "Men", 2499, 3499),
    ("Pinemark Linen Shirt", "Men", 1699, 2199),
    ("Tessel Everyday Tote", "Women", 1299, 1899),
    ("Aurex Trail Running Shoes", "Footwear", 3499, 4999),
    ("The Salt Road", "Fiction", 449, 599),
    ("Designing Data-Intensive Systems", "Technology", 1299, 1699),
    ("Nordwave 65W GaN Charger", "Smartphones", 1999, 2599),
]

IMAGE = "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=800&q=80"


class Command(BaseCommand):
    help = "Populate the database with demo data for every role."

    def handle(self, *args, **options):
        self.stdout.write("Seeding demo data...")

        users = {
            "admin@shop.test": ("admin", "Ada Admin"),
            "seller@shop.test": ("seller", "Sam Seller"),
            "seller2@shop.test": ("seller", "Nina Vendor"),
            "customer@shop.test": ("customer", "Cara Customer"),
            "inventory@shop.test": ("inventory", "Ivan Inventory"),
            "delivery@shop.test": ("delivery", "Dev Delivery"),
        }
        created_users = {}
        for email, (role, name) in users.items():
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "role": role,
                    "full_name": name,
                    "is_verified": True,
                    "is_staff": role == "admin",
                    "is_superuser": role == "admin",
                },
            )
            if created:
                user.set_password("Password123!")
                user.save()
            created_users[email] = user

        for email in ("seller@shop.test", "seller2@shop.test"):
            user = created_users[email]
            profile, _ = SellerProfile.objects.get_or_create(
                user=user,
                defaults={
                    "store_name": "Northline Supply" if "2" not in email else "Vendor Nine",
                    "store_slug": "northline-supply" if "2" not in email else "vendor-nine",
                    "description": "Curated everyday goods shipped fast.",
                },
            )
            profile.approve()

        Address.objects.get_or_create(
            user=created_users["customer@shop.test"],
            label="Home",
            defaults={
                "full_name": "Cara Customer",
                "phone": "9876543210",
                "line1": "42 Banjara Hills Road 12",
                "city": "Hyderabad",
                "state": "Telangana",
                "postal_code": "500034",
                "is_default": True,
            },
        )

        category_map = {}
        for parent_name, children in CATEGORIES.items():
            parent, _ = Category.objects.get_or_create(name=parent_name)
            category_map[parent_name] = parent
            for child in children:
                child_obj, _ = Category.objects.get_or_create(name=child, parent=parent)
                category_map[child] = child_obj

        brand_map = {name: Brand.objects.get_or_create(name=name)[0] for name in BRANDS}

        sellers = [created_users["seller@shop.test"], created_users["seller2@shop.test"]]
        products = []
        for index, (name, category, price, compare) in enumerate(PRODUCTS):
            brand = brand_map[next((b for b in BRANDS if name.startswith(b)), BRANDS[0])]
            product, created = Product.objects.get_or_create(
                sku=f"SKU-{1000 + index}",
                defaults={
                    "name": name,
                    "seller": sellers[index % 2],
                    "category": category_map[category],
                    "brand": brand,
                    "short_description": f"{name} - built to last, backed by a 1 year warranty.",
                    "description": (
                        f"{name} is part of our current season lineup. "
                        "Ships in recyclable packaging with a 7 day return window."
                    ),
                    "price": Decimal(price),
                    "compare_at_price": Decimal(compare),
                    "cost_price": Decimal(price) * Decimal("0.7"),
                    "tax_percent": Decimal("18"),
                    "stock": random.randint(4, 90),
                    "thumbnail": IMAGE,
                    "status": "approved",
                    "is_featured": index % 4 == 0,
                    "sold_count": random.randint(0, 240),
                },
            )
            if created:
                for position in range(3):
                    ProductImage.objects.create(product=product, url=IMAGE, position=position)
            products.append(product)

        customer = created_users["customer@shop.test"]
        for product in products[:6]:
            Review.objects.get_or_create(
                product=product,
                user=customer,
                defaults={
                    "rating": random.randint(4, 5),
                    "title": "Solid buy",
                    "comment": "Arrived quickly and matches the description.",
                    "is_verified_purchase": True,
                },
            )
            product.recalculate_rating()

        Coupon.objects.get_or_create(
            code="WELCOME10",
            defaults={
                "description": "10% off your first order",
                "discount_type": "percent",
                "value": Decimal("10"),
                "min_order_value": Decimal("500"),
                "max_discount": Decimal("1500"),
                "valid_until": timezone.now() + timezone.timedelta(days=90),
            },
        )
        Coupon.objects.get_or_create(
            code="FLAT250",
            defaults={
                "description": "Flat 250 off above 2000",
                "discount_type": "fixed",
                "value": Decimal("250"),
                "min_order_value": Decimal("2000"),
                "valid_until": timezone.now() + timezone.timedelta(days=30),
            },
        )

        warehouse, _ = Warehouse.objects.get_or_create(
            code="HYD-01",
            defaults={
                "name": "Hyderabad Central",
                "city": "Hyderabad",
                "state": "Telangana",
                "manager": created_users["inventory@shop.test"],
            },
        )
        Warehouse.objects.get_or_create(
            code="BLR-01",
            defaults={"name": "Bengaluru East", "city": "Bengaluru", "state": "Karnataka"},
        )
        Supplier.objects.get_or_create(
            name="Meridian Distributors",
            defaults={
                "contact_person": "R. Kapoor",
                "email": "sales@meridian.test",
                "phone": "9000012345",
                "lead_time_days": 5,
            },
        )
        for product in products:
            StockItem.objects.get_or_create(
                warehouse=warehouse,
                product=product,
                batch_number="",
                defaults={"quantity": product.stock, "bin_location": f"A-{product.id:03d}"},
            )

        self.stdout.write(self.style.SUCCESS("Seed complete."))
        self.stdout.write("Accounts (password: Password123!)")
        for email, (role, _) in users.items():
            self.stdout.write(f"  {role:<10} {email}")
