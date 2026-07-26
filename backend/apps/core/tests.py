from decimal import Decimal

from django.urls import reverse
from rest_framework.test import APITestCase

from apps.accounts.models import Address, SellerProfile, User
from apps.catalog.models import Brand, Category, Product
from apps.orders.models import Coupon, Order


class BaseAPITest(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin@test.com", password="Passw0rd!123", role="admin", is_verified=True
        )
        self.seller = User.objects.create_user(
            email="seller@test.com", password="Passw0rd!123", role="seller", is_verified=True
        )
        SellerProfile.objects.create(
            user=self.seller, store_name="Test Store", store_slug="test-store", is_approved=True
        )
        self.customer = User.objects.create_user(
            email="buyer@test.com", password="Passw0rd!123", role="customer", is_verified=True
        )
        self.category = Category.objects.create(name="Gadgets")
        self.brand = Brand.objects.create(name="Testco")
        self.product = Product.objects.create(
            seller=self.seller,
            category=self.category,
            brand=self.brand,
            name="Test Widget",
            sku="SKU-TEST-1",
            price=Decimal("1000.00"),
            stock=25,
            status="approved",
        )
        self.address = Address.objects.create(
            user=self.customer,
            full_name="Buyer",
            phone="9999999999",
            line1="1 Test Lane",
            city="Hyderabad",
            state="Telangana",
            postal_code="500001",
            is_default=True,
        )

    def auth(self, user, password="Passw0rd!123"):
        response = self.client.post(
            "/api/auth/login/", {"email": user.email, "password": password}, format="json"
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        return response.data


class AuthTests(BaseAPITest):
    def test_register_creates_customer(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "email": "new@test.com",
                "password": "Str0ngPass!99",
                "full_name": "New User",
                "role": "customer",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(User.objects.filter(email="new@test.com").exists())

    def test_register_seller_creates_store(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "email": "store@test.com",
                "password": "Str0ngPass!99",
                "role": "seller",
                "store_name": "Store X",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(SellerProfile.objects.filter(store_name="Store X").exists())

    def test_login_returns_tokens_and_role(self):
        data = self.auth(self.customer)
        self.assertIn("access", data)
        self.assertEqual(data["user"]["role"], "customer")

    def test_me_requires_auth(self):
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 401)


class CatalogTests(BaseAPITest):
    def test_public_product_list(self):
        response = self.client.get("/api/catalog/products/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_pending_products_hidden_from_public(self):
        Product.objects.create(
            seller=self.seller,
            category=self.category,
            name="Hidden",
            sku="SKU-HIDDEN",
            price=Decimal("10"),
            status="pending",
        )
        response = self.client.get("/api/catalog/products/")
        self.assertEqual(response.data["count"], 1)

    def test_seller_creates_product_as_pending(self):
        self.auth(self.seller)
        response = self.client.post(
            "/api/catalog/products/",
            {
                "name": "Second Widget",
                "sku": "SKU-TEST-2",
                "category": self.category.id,
                "price": "500.00",
                "stock": 5,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Product.objects.get(sku="SKU-TEST-2").status, "pending")

    def test_customer_cannot_create_product(self):
        self.auth(self.customer)
        response = self.client.post(
            "/api/catalog/products/",
            {"name": "Nope", "sku": "X", "category": self.category.id, "price": "1"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_approves_product(self):
        product = Product.objects.create(
            seller=self.seller,
            category=self.category,
            name="Awaiting",
            sku="SKU-WAIT",
            price=Decimal("99"),
            status="pending",
        )
        self.auth(self.admin)
        response = self.client.post(f"/api/catalog/products/{product.slug}/approve/")
        self.assertEqual(response.status_code, 200)
        product.refresh_from_db()
        self.assertEqual(product.status, "approved")

    def test_price_filter(self):
        response = self.client.get("/api/catalog/products/?min_price=2000")
        self.assertEqual(response.data["count"], 0)


class CartCheckoutTests(BaseAPITest):
    def add_to_cart(self, quantity=2):
        return self.client.post(
            "/api/cart/items/", {"product": self.product.id, "quantity": quantity}, format="json"
        )

    def test_add_and_total(self):
        self.auth(self.customer)
        response = self.add_to_cart()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Decimal(response.data["subtotal"]), Decimal("2000.00"))

    def test_cannot_exceed_stock(self):
        self.auth(self.customer)
        response = self.add_to_cart(quantity=999)
        self.assertEqual(response.status_code, 400)

    def test_checkout_creates_order_and_reduces_stock(self):
        self.auth(self.customer)
        self.add_to_cart(quantity=3)
        response = self.client.post(
            "/api/orders/checkout/",
            {"address_id": self.address.id, "payment_method": "cod"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        order = Order.objects.get(order_number=response.data["order_number"])
        self.assertEqual(order.status, "confirmed")
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 22)

    def test_checkout_with_coupon(self):
        Coupon.objects.create(code="SAVE10", discount_type="percent", value=Decimal("10"))
        self.auth(self.customer)
        self.add_to_cart(quantity=1)
        response = self.client.post(
            "/api/orders/checkout/",
            {"address_id": self.address.id, "payment_method": "cod", "coupon_code": "SAVE10"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Decimal(response.data["discount"]), Decimal("100.00"))

    def test_empty_cart_rejected(self):
        self.auth(self.customer)
        response = self.client.post(
            "/api/orders/checkout/",
            {"address_id": self.address.id, "payment_method": "cod"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_cancel_restores_stock(self):
        self.auth(self.customer)
        self.add_to_cart(quantity=2)
        order_number = self.client.post(
            "/api/orders/checkout/",
            {"address_id": self.address.id, "payment_method": "cod"},
            format="json",
        ).data["order_number"]
        self.client.post(f"/api/orders/{order_number}/cancel/")
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 25)

    def test_customer_sees_only_own_orders(self):
        self.auth(self.customer)
        self.add_to_cart(quantity=1)
        self.client.post(
            "/api/orders/checkout/",
            {"address_id": self.address.id, "payment_method": "cod"},
            format="json",
        )
        other = User.objects.create_user(
            email="other@test.com", password="Passw0rd!123", role="customer"
        )
        self.auth(other)
        self.assertEqual(self.client.get("/api/orders/").data["count"], 0)


class InventoryTests(BaseAPITest):
    def test_inventory_dashboard_requires_staff_role(self):
        self.auth(self.customer)
        self.assertEqual(self.client.get("/api/inventory/dashboard/").status_code, 403)

    def test_stock_movement_updates_product(self):
        manager = User.objects.create_user(
            email="inv@test.com", password="Passw0rd!123", role="inventory"
        )
        self.auth(manager)
        response = self.client.post(
            "/api/inventory/movements/",
            {"product": self.product.id, "movement_type": "in", "quantity": 10},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 35)


class HealthTests(BaseAPITest):
    def test_health_is_public(self):
        self.assertEqual(self.client.get("/api/health/").status_code, 200)
