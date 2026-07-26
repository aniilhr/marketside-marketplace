# Database schema

## Entity relationships

```
User (accounts)
 ├─1:1─ SellerProfile          store name, slug, approval state
 ├─1:N─ Address                shipping addresses
 ├─1:N─ OTPCode                email verification / password reset
 ├─1:N─ Product                listings owned by a seller
 ├─1:1─ Cart ──1:N── CartItem ──N:1── Product
 ├─1:N─ Order ──1:N── OrderItem ──N:1── Product
 │              └─1:N── OrderEvent      status timeline
 │              └─1:N── Payment
 │              └─1:N── ReturnRequest
 ├─1:N─ Review, Wishlist, RecentlyViewed
 ├─1:N─ Notification, SupportTicket, AuditLog
 └─1:N─ Order (as delivery_partner)

Category ──self FK──▶ Category (parent/children)
Category ──1:N──▶ Product ◀──N:1── Brand
Product ──1:N──▶ ProductImage, Review, StockItem, StockMovement

Warehouse ──1:N──▶ StockItem ◀──N:1── Product
Warehouse ──1:N──▶ PurchaseOrder ──1:N──▶ PurchaseOrderLine ──N:1──▶ Product
Supplier  ──1:N──▶ PurchaseOrder
Warehouse ──1:N──▶ StockTransfer (source and destination)
```

## Key tables

**accounts_user** — email is the login field (no username). `role` is one of customer, seller,
admin, inventory, delivery, and drives every permission check. Carries `wallet_balance`,
`loyalty_points`, `referral_code`, `is_verified`.

**catalog_product** — `seller_id`, `category_id`, `brand_id`, unique `sku` and `slug`, `price`,
`compare_at_price`, `cost_price`, `tax_percent`, `stock`, `low_stock_threshold`, `status`
(draft/pending/approved/rejected), denormalised `rating`, `review_count`, `sold_count`,
`view_count`. Indexed on `(status, is_active)` and `-sold_count`.

**orders_order** — unique `order_number` (`ORD-YYYYMMDD-XXXXXX`), `status`, `payment_method`,
`payment_status`, money columns (`subtotal`, `discount`, `tax`, `shipping_fee`, `total`),
`shipping_address` snapshotted as JSON so later address edits don't rewrite history,
`delivery_partner_id`, `delivery_otp`, `delivered_at`.

**orders_orderitem** — snapshots `product_name`, `thumbnail`, `unit_price` at purchase time and
stores the platform `commission` per line, so seller payouts stay correct if prices change.

**inventory_stockmovement** — the audit trail for stock. Every checkout, cancellation, goods
receipt and manual adjustment writes a row, and product stock is updated in the same transaction.

## Migrations

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py showmigrations
```

Switching from SQLite to PostgreSQL: set `USE_SQLITE=0` plus the `POSTGRES_*` variables and run
`migrate` again — the models are database-agnostic.
