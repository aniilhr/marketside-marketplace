import { motion } from "framer-motion";
import { ReactNode, useEffect, useState } from "react";
import toast from "react-hot-toast";
import { Link, NavLink, Navigate, Outlet, useLocation, useNavigate } from "react-router-dom";

import { api, apiError, money } from "../lib/api";
import { useAppDispatch, useAppSelector } from "../store";
import { logout } from "../store/authSlice";
import { addToCart, fetchCart } from "../store/cartSlice";
import { toggleTheme } from "../store/uiSlice";
import type { Product, Role } from "../types";

/* ---------------------------------------------------------------- primitives */

export function Spinner({ label = "Loading" }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 py-10 text-sm text-ink-muted" role="status">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-forest-500 border-t-transparent" />
      {label}
    </div>
  );
}

export function SkeletonGrid({ count = 8 }: { count?: number }) {
  return (
    <div className="grid grid-cols-2 gap-5 md:grid-cols-3 lg:grid-cols-4">
      {Array.from({ length: count }).map((_, index) => (
        <div key={index} className="space-y-3">
          <div className="skeleton aspect-square w-full" />
          <div className="skeleton h-4 w-3/4" />
          <div className="skeleton h-4 w-1/3" />
        </div>
      ))}
    </div>
  );
}

export function EmptyState({
  title,
  body,
  action,
}: {
  title: string;
  body: string;
  action?: ReactNode;
}) {
  return (
    <div className="card flex flex-col items-center gap-3 p-12 text-center">
      <h3 className="text-xl">{title}</h3>
      <p className="max-w-sm text-sm text-ink-muted">{body}</p>
      {action}
    </div>
  );
}

export function StatCard({
  label,
  value,
  hint,
}: {
  label: string;
  value: string | number;
  hint?: string;
}) {
  return (
    <div className="card p-5">
      <p className="label mb-2">{label}</p>
      <p className="font-display text-3xl">{value}</p>
      {hint && <p className="mt-1 text-xs text-ink-muted">{hint}</p>}
    </div>
  );
}

const STATUS_TONE: Record<string, string> = {
  pending: "bg-amber-100 text-amber-500",
  confirmed: "bg-forest-50 text-forest-600",
  packed: "bg-forest-50 text-forest-600",
  ready_to_ship: "bg-forest-50 text-forest-600",
  shipped: "bg-forest-100 text-forest-700",
  out_for_delivery: "bg-amber-100 text-amber-500",
  delivered: "bg-forest-500 text-white",
  cancelled: "bg-red-100 text-red-600",
  returned: "bg-red-100 text-red-600",
  refunded: "bg-red-100 text-red-600",
  approved: "bg-forest-500 text-white",
  rejected: "bg-red-100 text-red-600",
};

export function StatusChip({ status }: { status: string }) {
  return (
    <span className={`chip ${STATUS_TONE[status] || "bg-paper-sunk text-ink-soft"}`}>
      {status.replace(/_/g, " ")}
    </span>
  );
}

/* ---------------------------------------------------------------- guards */

export function RequireAuth({ roles }: { roles?: Role[] }) {
  const { user, status } = useAppSelector((state) => state.auth);
  const location = useLocation();

  if (status !== "ready") return <Spinner label="Checking your session" />;
  if (!user) return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  if (roles && !roles.includes(user.role)) {
    return (
      <div className="mx-auto max-w-lg px-4 py-24">
        <EmptyState
          title="You don't have access to this area"
          body={`This page is for ${roles.join(", ")} accounts. You're signed in as ${user.role}.`}
          action={
            <Link className="btn-primary" to="/">
              Back to the store
            </Link>
          }
        />
      </div>
    );
  }
  return <Outlet />;
}

/* ---------------------------------------------------------------- product card */

export function ProductCard({ product }: { product: Product }) {
  const dispatch = useAppDispatch();
  const user = useAppSelector((state) => state.auth.user);
  const navigate = useNavigate();
  const [wished, setWished] = useState(false);

  const add = async () => {
    if (!user) return navigate("/login");
    try {
      await dispatch(addToCart({ product: product.id })).unwrap();
      toast.success("Added to cart");
    } catch (error) {
      toast.error(apiError(error, "Couldn't add that item"));
    }
  };

  const wish = async () => {
    if (!user) return navigate("/login");
    try {
      const { data } = await api.post("/catalog/wishlist/", { product: product.id });
      setWished(data.active);
      toast.success(data.detail);
    } catch (error) {
      toast.error(apiError(error));
    }
  };

  return (
    <motion.article
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="card group flex flex-col overflow-hidden"
    >
      <Link to={`/product/${product.slug}`} className="relative block overflow-hidden bg-paper-sunk">
        <img
          src={product.thumbnail || "https://placehold.co/600x600/F1EFE9/6A7482?text=No+image"}
          alt={product.name}
          loading="lazy"
          className="aspect-square w-full object-cover transition duration-500 group-hover:scale-105"
        />
        {product.discount_percent > 0 && (
          <span className="absolute left-3 top-3 chip bg-amber-400 text-ink">
            {product.discount_percent}% off
          </span>
        )}
        {!product.in_stock && (
          <span className="absolute right-3 top-3 chip bg-ink text-white">Sold out</span>
        )}
      </Link>
      <div className="flex flex-1 flex-col gap-2 p-4">
        <p className="text-[11px] uppercase tracking-wider text-ink-muted">{product.store_name}</p>
        <Link to={`/product/${product.slug}`} className="line-clamp-2 font-medium leading-snug">
          {product.name}
        </Link>
        <div className="mt-auto flex items-baseline gap-2 pt-2">
          <span className="font-display text-lg">{money(product.price)}</span>
          {product.compare_at_price && (
            <span className="text-sm text-ink-muted line-through">
              {money(product.compare_at_price)}
            </span>
          )}
        </div>
        <p className="text-xs text-ink-muted">
          {Number(product.rating) > 0
            ? `${product.rating} out of 5 · ${product.review_count} reviews`
            : "No reviews yet"}
        </p>
        <div className="flex gap-2 pt-2">
          <button className="btn-primary flex-1" onClick={add} disabled={!product.in_stock}>
            Add to cart
          </button>
          <button className="btn-ghost px-3" onClick={wish} aria-label="Save for later">
            {wished ? "♥" : "♡"}
          </button>
        </div>
      </div>
    </motion.article>
  );
}

/* ---------------------------------------------------------------- shell */

const ROLE_HOME: Record<Role, string> = {
  customer: "/orders",
  seller: "/seller",
  admin: "/admin",
  inventory: "/inventory",
  delivery: "/delivery",
};

export function Layout() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const { user } = useAppSelector((state) => state.auth);
  const cart = useAppSelector((state) => state.cart.cart);
  const dark = useAppSelector((state) => state.ui.dark);
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState<{ name: string; slug: string }[]>([]);

  useEffect(() => {
    if (user) dispatch(fetchCart());
  }, [user, dispatch]);

  useEffect(() => {
    if (query.trim().length < 2) return setSuggestions([]);
    const timer = setTimeout(async () => {
      try {
        const { data } = await api.get("/catalog/search-suggestions/", { params: { q: query } });
        setSuggestions(data.products);
      } catch {
        setSuggestions([]);
      }
    }, 250);
    return () => clearTimeout(timer);
  }, [query]);

  const submitSearch = (event: React.FormEvent) => {
    event.preventDefault();
    setSuggestions([]);
    navigate(`/products?search=${encodeURIComponent(query)}`);
  };

  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-40 border-b border-black/5 bg-paper/90 backdrop-blur dark:border-night-line dark:bg-night/90">
        <div className="mx-auto flex max-w-7xl items-center gap-4 px-4 py-3">
          <Link to="/" className="font-display text-xl font-extrabold tracking-tight">
            market<span className="text-forest-500">side</span>
          </Link>

          <form onSubmit={submitSearch} className="relative hidden flex-1 md:block">
            <input
              className="field"
              placeholder="Search products, brands and stores"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              aria-label="Search products"
            />
            {suggestions.length > 0 && (
              <ul className="card absolute z-50 mt-2 w-full overflow-hidden p-1">
                {suggestions.map((item) => (
                  <li key={item.slug}>
                    <Link
                      to={`/product/${item.slug}`}
                      onClick={() => setSuggestions([])}
                      className="block rounded-lg px-3 py-2 text-sm hover:bg-paper-sunk dark:hover:bg-night-line"
                    >
                      {item.name}
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </form>

          <nav className="ml-auto flex items-center gap-1 text-sm">
            <NavLink to="/products" className="btn-ghost hidden sm:inline-flex">
              Browse
            </NavLink>
            <button
              className="btn-ghost px-3"
              onClick={() => dispatch(toggleTheme())}
              aria-label="Switch colour theme"
            >
              {dark ? "☀" : "☾"}
            </button>
            <Link to="/cart" className="btn-ghost">
              Cart{cart?.item_count ? ` · ${cart.item_count}` : ""}
            </Link>
            {user ? (
              <div className="flex items-center gap-1">
                <Link to={ROLE_HOME[user.role]} className="btn-ghost hidden sm:inline-flex">
                  {user.role === "customer" ? "Orders" : "Dashboard"}
                </Link>
                <button
                  className="btn-primary"
                  onClick={() => {
                    dispatch(logout());
                    navigate("/");
                  }}
                >
                  Sign out
                </button>
              </div>
            ) : (
              <Link to="/login" className="btn-primary">
                Sign in
              </Link>
            )}
          </nav>
        </div>
      </header>

      <main className="flex-1">
        <Outlet />
      </main>

      <footer className="border-t border-black/5 bg-paper-sunk py-10 dark:border-night-line dark:bg-night-raised">
        <div className="mx-auto grid max-w-7xl gap-8 px-4 sm:grid-cols-3">
          <div>
            <p className="font-display text-lg font-bold">marketside</p>
            <p className="mt-2 max-w-xs text-sm text-ink-muted">
              A marketplace where independent shops sell alongside larger brands, on one checkout.
            </p>
          </div>
          <div className="text-sm">
            <p className="label">Shop</p>
            <Link className="block py-1 hover:underline" to="/products">
              All products
            </Link>
            <Link className="block py-1 hover:underline" to="/products?is_featured=true">
              Featured
            </Link>
            <Link className="block py-1 hover:underline" to="/register">
              Sell with us
            </Link>
          </div>
          <div className="text-sm">
            <p className="label">Developers</p>
            <a className="block py-1 hover:underline" href="/api/docs/">
              API documentation
            </a>
            <a className="block py-1 hover:underline" href="/api/schema/">
              OpenAPI schema
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
