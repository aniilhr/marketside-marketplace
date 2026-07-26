# ER diagram

Paste into any Mermaid renderer (GitHub renders it natively, or use mermaid.live).

```mermaid
erDiagram
    USER ||--o| SELLER_PROFILE : "owns store"
    USER ||--o{ ADDRESS : "ships to"
    USER ||--o{ OTP_CODE : "verifies with"
    USER ||--o| CART : "has"
    USER ||--o{ ORDER : "places"
    USER ||--o{ PRODUCT : "sells"
    USER ||--o{ REVIEW : "writes"
    USER ||--o{ WISHLIST : "saves"
    USER ||--o{ NOTIFICATION : "receives"
    USER ||--o{ ORDER : "delivers"

    CATEGORY ||--o{ CATEGORY : "parent of"
    CATEGORY ||--o{ PRODUCT : "classifies"
    BRAND ||--o{ PRODUCT : "brands"

    PRODUCT ||--o{ PRODUCT_IMAGE : "shows"
    PRODUCT ||--o{ REVIEW : "receives"
    PRODUCT ||--o{ CART_ITEM : "sits in"
    PRODUCT ||--o{ ORDER_ITEM : "sold as"
    PRODUCT ||--o{ STOCK_ITEM : "stored as"
    PRODUCT ||--o{ STOCK_MOVEMENT : "tracked by"

    CART ||--o{ CART_ITEM : "contains"

    ORDER ||--|{ ORDER_ITEM : "contains"
    ORDER ||--o{ ORDER_EVENT : "logs"
    ORDER ||--o{ PAYMENT : "settled by"
    ORDER ||--o{ RETURN_REQUEST : "may have"
    COUPON ||--o{ ORDER : "discounts"

    WAREHOUSE ||--o{ STOCK_ITEM : "holds"
    WAREHOUSE ||--o{ PURCHASE_ORDER : "receives into"
    WAREHOUSE ||--o{ STOCK_TRANSFER : "sends and receives"
    SUPPLIER ||--o{ PURCHASE_ORDER : "fulfils"
    PURCHASE_ORDER ||--|{ PURCHASE_ORDER_LINE : "itemises"

    USER {
        int id PK
        string email UK
        string full_name
        string role
        decimal wallet_balance
        int loyalty_points
        bool is_verified
    }
    PRODUCT {
        int id PK
        int seller_id FK
        int category_id FK
        int brand_id FK
        string sku UK
        string slug UK
        decimal price
        decimal compare_at_price
        decimal tax_percent
        int stock
        int low_stock_threshold
        string status
        decimal rating
        int sold_count
    }
    ORDER {
        int id PK
        string order_number UK
        int user_id FK
        string status
        string payment_method
        string payment_status
        decimal subtotal
        decimal discount
        decimal tax
        decimal shipping_fee
        decimal total
        json shipping_address
        string delivery_otp
    }
    ORDER_ITEM {
        int id PK
        int order_id FK
        int product_id FK
        int seller_id FK
        string product_name
        decimal unit_price
        int quantity
        decimal subtotal
        decimal commission
    }
    STOCK_MOVEMENT {
        int id PK
        int product_id FK
        int warehouse_id FK
        string movement_type
        int quantity
        string reference
    }
```

## Reading the diagram

The three relationships worth noting:

1. **A user is one row, not five tables.** `role` decides whether the same person sees a
   storefront, a seller dashboard, or a warehouse console. That keeps auth simple and lets an
   admin promote an account without migrating data.
2. **Order items snapshot the product.** `product_name`, `unit_price` and `commission` are copied
   at checkout, so editing a listing later never rewrites financial history.
3. **Stock has two sources of truth, kept in sync.** `PRODUCT.stock` is the fast number the
   storefront reads; `STOCK_ITEM` (per warehouse) plus `STOCK_MOVEMENT` (the ledger) are what the
   warehouse team works from. Every checkout, cancellation and goods receipt writes both in one
   transaction.
