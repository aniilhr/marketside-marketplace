# API reference

Base URL: `http://localhost:8000/api`
Interactive docs: `/api/docs/` (Swagger) and `/api/redoc/`
Machine-readable schema: `/api/schema/`

All protected endpoints expect `Authorization: Bearer <access_token>`.

## Auth — `/api/auth/`

| Method | Path | Access | Purpose |
|---|---|---|---|
| POST | `register/` | public | Create a customer or seller account |
| POST | `login/` | public | Returns `access`, `refresh` and the user object |
| POST | `refresh/` | public | Exchange a refresh token for a new access token |
| GET/PATCH | `me/` | any | Read or update the signed-in profile |
| POST | `change-password/` | any | Change password with the current one |
| POST | `verify-email/` | public | Confirm the 6-digit code |
| POST | `resend-code/` | public | Reissue a verification code |
| POST | `password-reset/` | public | Send a reset code |
| POST | `password-reset/confirm/` | public | Set a new password using the code |
| GET/POST/PATCH/DELETE | `addresses/` | any | Address book |
| GET | `sellers/` | public | Approved stores (admins see all) |
| POST | `sellers/{id}/approve/` | admin | Approve a store |
| GET | `users/` | admin | User management, filter by `role`, `is_active` |
| POST | `users/{id}/set-role/` | admin | Change a user's role |

## Catalog — `/api/catalog/`

| Method | Path | Access | Purpose |
|---|---|---|---|
| GET | `products/` | public | List with filters and pagination |
| GET | `products/{slug}/` | public | Detail with images and reviews |
| POST | `products/` | seller, admin | Create a listing (pending approval) |
| PATCH | `products/{slug}/` | owner, admin | Update a listing |
| POST | `products/{slug}/approve/` | admin | Publish a listing |
| POST | `products/{slug}/reject/` | admin | Reject with an optional `reason` |
| GET | `products/featured/` | public | Featured selection |
| GET | `products/trending/` | public | Best sellers |
| GET | `products/{slug}/related/` | public | Same-category products |
| GET | `products/{slug}/bought-together/` | public | Co-purchase suggestions |
| POST | `products/bulk-upload/` | seller | Array of rows under `products` |
| GET/POST | `categories/`, `brands/` | public read, admin write | Taxonomy |
| GET/POST/DELETE | `reviews/` | public read, auth write | Product reviews |
| GET/POST | `wishlist/` | auth | POST toggles an item |
| GET | `recently-viewed/` | auth | Last 10 viewed |
| GET | `recommendations/` | auth | Based on views and purchases |
| GET | `search-suggestions/?q=` | public | Autocomplete |
| GET | `seller/dashboard/` | seller | Revenue, orders, low stock |

### Product filters

`search`, `category` (slug), `brand` (slug), `seller` (id), `min_price`, `max_price`,
`min_rating`, `in_stock` (true/false), `is_featured`, `ordering`
(`price`, `-price`, `-rating`, `-created_at`, `-sold_count`), `page`, `page_size`, `mine=1`.

## Cart and orders

| Method | Path | Access | Purpose |
|---|---|---|---|
| GET | `/api/cart/` | auth | Current cart with totals |
| POST | `/api/cart/items/` | auth | `{product, quantity}` |
| PATCH | `/api/cart/items/{id}/` | auth | Change quantity (0 removes) |
| DELETE | `/api/cart/items/{id}/remove/` | auth | Remove a line |
| DELETE | `/api/cart/clear/` | auth | Empty the cart |
| POST | `/api/cart/apply-coupon/` | auth | `{code}` |
| POST | `/api/orders/checkout/` | auth | `{address_id, payment_method, coupon_code?}` |
| GET | `/api/orders/` | auth | Scoped by role |
| GET | `/api/orders/{order_number}/` | auth | Detail with timeline |
| POST | `/api/orders/{order_number}/status/` | seller, admin, inventory, delivery | `{status, note?}` |
| POST | `/api/orders/{order_number}/cancel/` | owner | Restores stock, refunds to wallet |
| POST | `/api/orders/{order_number}/assign-delivery/` | admin | `{partner_id}`, issues OTP |
| POST | `/api/orders/{order_number}/confirm-delivery/` | delivery | `{otp}` |
| GET | `/api/orders/{order_number}/invoice/` | auth | Invoice payload |
| GET/POST | `/api/returns/` | auth | Return requests |
| POST | `/api/returns/{id}/approve/` | admin | Refund to wallet |
| GET/POST | `/api/coupons/` | seller, admin | Coupon management |
| GET | `/api/payments/` | auth | Payment history |
| GET | `/api/reports/sales/` | auth | 30-day revenue series, scoped by role |

Order statuses: `pending → confirmed → packed → ready_to_ship → shipped → out_for_delivery →
delivered`, plus `cancelled`, `returned`, `refunded`.

## Inventory — `/api/inventory/`

| Method | Path | Access | Purpose |
|---|---|---|---|
| GET | `dashboard/` | inventory, admin | Units, low stock, open POs, recent movements |
| GET | `low-stock/` | inventory, admin | Products at or below threshold |
| POST | `auto-reorder/` | inventory, admin | Draft a PO covering every low item |
| CRUD | `warehouses/`, `suppliers/`, `stock-items/` | inventory, admin | Master data |
| GET/POST | `movements/` | inventory, admin | Movement keeps product stock in sync |
| CRUD | `purchase-orders/` | inventory, admin | With nested `lines` |
| POST | `purchase-orders/{id}/receive/` | inventory, admin | `{lines: [{line_id, quantity}]}` |
| CRUD | `transfers/` + `{id}/complete/` | inventory, admin | Inter-warehouse moves |

## Platform

| Method | Path | Access | Purpose |
|---|---|---|---|
| GET | `/api/health/` | public | Liveness probe |
| GET | `/api/admin/dashboard/` | admin | Platform metrics |
| GET | `/api/notifications/` | auth | In-app notifications |
| POST | `/api/notifications/read-all/` | auth | Mark all read |
| GET/POST | `/api/support-tickets/` | auth | Support tickets |
| GET | `/api/audit-logs/` | admin | Audit trail |

## Errors

Errors return `{"detail": "..."}` or `{"field": ["message"]}` with the usual status codes:
400 validation, 401 missing or expired token, 403 wrong role, 404 not found, 429 throttled.
