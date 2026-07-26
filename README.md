# Marketside — multi-vendor marketplace

A working Django REST Framework + React (Vite, TypeScript) marketplace with five roles, JWT auth,
a real cart-to-delivery order lifecycle, warehouse stock control, seller and admin dashboards,
Swagger docs, Docker, and CI.

This is a functioning foundation you can build on and deploy, not a mockup: every screen calls a
real endpoint, and orders move stock in the database.

---

## Quick start (fastest path — SQLite, no Docker)

Two terminals. Terminal 1, backend:

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py seed
python manage.py runserver 8000
```

Terminal 2, frontend:

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Open **http://localhost:5173**. API docs at **http://localhost:8000/api/docs/**.

### Demo accounts

Password for all of them: `Password123!`

| Role | Email | What you can see |
|---|---|---|
| Customer | customer@shop.test | Browse, cart, checkout, orders, reviews |
| Seller | seller@shop.test | Store dashboard, listings, revenue chart, order status |
| Admin | admin@shop.test | Platform revenue, product/seller approvals, users |
| Inventory manager | inventory@shop.test | Stock on hand, movements, reorder drafts |
| Delivery partner | delivery@shop.test | Assigned runs, OTP delivery confirmation |

---

## Windows notes (and the two errors you may hit)

### Use Python 3.12, not 3.13 or 3.14

The pinned versions are tested on **Python 3.12**. Newer Pythons don't yet have prebuilt wheels
for some of these packages, so pip falls back to compiling from source and fails.

```powershell
winget install Python.Python.3.12
py -0p                      # confirm 3.12 is listed
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python --version            # should print 3.12.x
pip install -r requirements.txt
```

### "pg_config executable not found"

You're installing the PostgreSQL driver without PostgreSQL present. You don't need it for local
development — `requirements.txt` no longer includes it. Local runs use SQLite.

Install the driver only when you're pointing at a real PostgreSQL server:

```powershell
pip install -r requirements-postgres.txt
```

Docker already does this for you, so `docker compose up --build` needs none of the above.

### "Unable to copy venvlauncher.exe to python.exe"

The virtual environment was created without a working `python.exe`, so every later command falls
back to a Python that has nothing installed. This is almost always antivirus or a syncing folder
(OneDrive-backed Desktop) locking the file mid-copy.

```powershell
deactivate                          # if the broken venv is active
Remove-Item -Recurse -Force .venv
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
Get-Command python | Select-Object Source   # must point inside .venv\Scripts
```

If it fails again, one of these clears it:

- Add your project folder to Windows Security → Virus & threat protection → Exclusions
- Move the project off the Desktop to a plain path like `C:\dev\marketplace`
- Use virtualenv instead: `py -3.12 -m pip install virtualenv` then `py -3.12 -m virtualenv .venv`

### If PowerShell blocks the activate script

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### Full Windows sequence

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py seed
python manage.py runserver 8000
```

Then in a second PowerShell window:

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

---

## Quick start with Docker (PostgreSQL + Redis + Celery + Nginx)

```bash
docker compose up --build
```

- Storefront: http://localhost:3000
- API: http://localhost:8000/api/
- Swagger: http://localhost:8000/api/docs/
- Django admin: http://localhost:8000/django-admin/

Migrations and seed data run automatically on first boot. Stop and wipe with `docker compose down -v`.

---

## Deploying the first build

1. **Set real secrets.** In `backend/.env.docker` (or your host's env vars) set `DJANGO_SECRET_KEY`
   to a long random string, `DJANGO_DEBUG=0`, `DJANGO_ALLOWED_HOSTS=yourdomain.com`,
   `CORS_ALLOW_ALL=0`, `CORS_ALLOWED_ORIGINS=https://yourdomain.com`, `SEED_ON_START=0`.
2. **Point the frontend at the API.** In `frontend/.env`, set `VITE_API_URL=https://yourdomain.com/api`,
   or leave it empty and let the bundled Nginx proxy `/api` to the backend container (the default).
3. **Build and run:** `docker compose -f docker-compose.yml up -d --build`.
4. **Create your admin:** `docker compose exec backend python manage.py createsuperuser`.
5. **TLS:** put Caddy, Traefik, or an Nginx reverse proxy with Let's Encrypt in front of port 3000.

Works as-is on a single VPS (2 vCPU / 4 GB is comfortable), Railway, Render, or Fly.io. For
managed Postgres, set `USE_SQLITE=0` and the `POSTGRES_*` variables to your provider's values.

---

## What's implemented

**Authentication** — JWT access and refresh with rotation, silent refresh in the Axios
interceptor, registration for customer and seller roles, email verification codes, password reset
by code, password change, role-based route guards on both the API and the router.

**Catalog** — categories with parent/child nesting, brands, products with images, SKUs, tax rate,
compare-at pricing, stock, approval workflow (seller submits → admin approves), reviews tied to
verified purchases, wishlist, recently viewed, search with autocomplete suggestions, filtering by
department, price band, rating, stock and seller, and sorting by price, rating, recency, or sales.

**Cart and checkout** — server-side persistent cart, stock validation on add and at checkout,
coupon validation (percent or fixed, minimum spend, max discount, usage caps, expiry), per-item
tax, free delivery above a threshold, four payment methods including a wallet, loyalty points
accrual, and an atomic transaction that decrements stock and writes stock movements.

**Order lifecycle** — ten statuses from pending to refunded, an append-only event timeline,
seller and admin status updates, customer cancellation that restores stock and refunds to wallet,
delivery assignment, OTP-verified delivery confirmation, invoice endpoint, and returns with
admin-approved refunds.

**Inventory** — warehouses, suppliers, per-warehouse stock items with bin and batch, stock
movements (in, out, adjust, transfer) that keep product stock in sync, purchase orders with goods
received notes, inter-warehouse transfers, low-stock reporting, and one-click reorder drafting.

**Dashboards** — seller revenue and best sellers, admin platform revenue with 30-day chart,
approvals queue, user and seller management, warehouse stock console, delivery partner run list.

**Platform** — notifications, audit log, support tickets, OpenAPI schema with Swagger and Redoc,
throttling, CORS, security headers when `DEBUG=0`, Celery worker wired for background jobs,
20 automated tests, GitHub Actions running tests and builds on every push.

### Not built (be aware before you plan around it)

The original brief listed roughly 300 features. This build covers the core commerce platform.
Deliberately left as extension points: live payment gateways (the payment service is mocked and
isolated in `apps/orders/views.py::checkout` for easy swapping), WebSocket live updates, SMS and
WhatsApp notifications, ML forecasting and fraud detection, AR/360 viewers, auctions, affiliate
and subscription modules, multi-language and multi-currency, and full PWA offline caching. The
architecture leaves room for each: add an app under `backend/apps/`, register its router, and add
a page under `frontend/src/pages/`.

---

## Project layout

```
marketplace/
├── backend/
│   ├── config/              # settings, urls, wsgi/asgi, celery
│   ├── apps/
│   │   ├── accounts/        # User, SellerProfile, Address, OTP, permissions
│   │   ├── catalog/         # Category, Brand, Product, Review, Wishlist
│   │   ├── orders/          # Cart, Coupon, Order, Payment, Returns
│   │   ├── inventory/       # Warehouse, Supplier, Stock, PurchaseOrder
│   │   └── core/            # Notifications, AuditLog, dashboards, seed, tests
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/      # Layout, guards, ProductCard, primitives
│   │   ├── pages/           # Storefront, Account, Dashboards, Misc
│   │   ├── store/           # Redux Toolkit: auth, cart, ui
│   │   └── lib/api.ts       # Axios client with token refresh
│   └── Dockerfile + nginx.conf
├── docs/                    # API reference, schema, deployment notes
├── postman_collection.json
├── docker-compose.yml
└── .github/workflows/ci.yml
```

---

## Common commands

```bash
make install    # install both sides
make seed       # migrate + load demo data
make test       # run the Django test suite (20 tests)
make up         # docker compose up --build
make down       # tear down including volumes
```

Regenerate the OpenAPI file: `cd backend && python manage.py spectacular --file ../docs/openapi.yml`

---

## Tech stack

React 18, TypeScript, Vite, Redux Toolkit, React Router, Axios, Tailwind CSS, React Hook Form,
Framer Motion, Recharts, TanStack Query · Django 5, Django REST Framework, SimpleJWT,
drf-spectacular, django-filter, PostgreSQL, Redis, Celery, Gunicorn, Nginx, Docker.
