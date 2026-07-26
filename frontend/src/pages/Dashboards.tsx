import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import toast from "react-hot-toast";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { EmptyState, Spinner, StatCard, StatusChip } from "../components";
import { api, apiError, money } from "../lib/api";
import { useAppSelector } from "../store";
import type { Category, Order, Product } from "../types";

const TABS = "flex flex-wrap gap-2 border-b border-ink/10 pb-3";

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button onClick={onClick} className={active ? "btn-primary" : "btn-ghost"}>
      {children}
    </button>
  );
}

function useSalesSeries() {
  const [series, setSeries] = useState<{ date: string; revenue: number }[]>([]);
  useEffect(() => {
    api
      .get("/reports/sales/")
      .then((response) =>
        setSeries(
          (response.data.series || []).map((row: { date: string; revenue: string }) => ({
            date: row.date.slice(5),
            revenue: Number(row.revenue),
          })),
        ),
      )
      .catch(() => setSeries([]));
  }, []);
  return series;
}

function RevenueChart({ data }: { data: { date: string; revenue: number }[] }) {
  if (!data.length) {
    return <p className="py-10 text-sm text-ink-muted">No sales in the last 30 days.</p>;
  }
  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" />
        <XAxis dataKey="date" fontSize={12} />
        <YAxis fontSize={12} />
        <Tooltip formatter={(value: number) => money(value)} />
        <Line type="monotone" dataKey="revenue" stroke="#1F6B47" strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}

/* ------------------------------------------------------------------ seller */

export function SellerDashboard() {
  const user = useAppSelector((state) => state.auth.user);
  const [tab, setTab] = useState<"overview" | "products" | "orders" | "new">("overview");
  const [stats, setStats] = useState<Record<string, never> | null>(null);
  const [products, setProducts] = useState<Product[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const series = useSalesSeries();
  const { register, handleSubmit, reset } = useForm<Record<string, string>>();

  const loadProducts = () =>
    api
      .get("/catalog/products/?mine=1&page_size=50")
      .then((response) => setProducts(response.data.results ?? response.data));

  useEffect(() => {
    api.get("/catalog/seller/dashboard/").then((response) => setStats(response.data));
    api.get("/orders/").then((response) => setOrders(response.data.results ?? response.data));
    api
      .get("/catalog/categories/?tree=0&page_size=100")
      .then((response) => setCategories(response.data.results ?? response.data));
    loadProducts();
  }, []);

  const createProduct = handleSubmit(async (values) => {
    try {
      await api.post("/catalog/products/", {
        ...values,
        category: Number(values.category),
        price: values.price,
        stock: Number(values.stock || 0),
        image_urls: values.thumbnail ? [values.thumbnail] : [],
      });
      toast.success("Listing submitted for approval");
      reset();
      setTab("products");
      loadProducts();
    } catch (error) {
      toast.error(apiError(error));
    }
  });

  const stat = (key: string) => (stats ? (stats as Record<string, unknown>)[key] : "—");

  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      <h1 className="text-4xl">{user?.store_name || "Seller"} dashboard</h1>
      {user && !user.is_approved_seller && (
        <p className="card mt-4 border-amber-400 p-4 text-sm">
          Your store is awaiting admin approval. You can add listings now — they go live once the
          store is approved.
        </p>
      )}

      <div className={`mt-6 ${TABS}`}>
        <TabButton active={tab === "overview"} onClick={() => setTab("overview")}>
          Overview
        </TabButton>
        <TabButton active={tab === "products"} onClick={() => setTab("products")}>
          Products
        </TabButton>
        <TabButton active={tab === "orders"} onClick={() => setTab("orders")}>
          Orders
        </TabButton>
        <TabButton active={tab === "new"} onClick={() => setTab("new")}>
          Add a product
        </TabButton>
      </div>

      {tab === "overview" && (
        <div className="mt-8 space-y-6">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label="Revenue" value={money(String(stat("revenue") ?? 0))} hint="Excluding cancelled" />
            <StatCard label="Orders" value={String(stat("orders") ?? 0)} />
            <StatCard label="Listings" value={String(stat("products") ?? 0)} />
            <StatCard label="Low stock" value={String(stat("low_stock") ?? 0)} hint="At or below threshold" />
          </div>
          <div className="card p-6">
            <h2 className="text-xl">Revenue, last 30 days</h2>
            <RevenueChart data={series} />
          </div>
        </div>
      )}

      {tab === "products" && (
        <div className="card mt-8 overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-ink/10 text-xs uppercase tracking-wider text-ink-muted">
              <tr>
                <th className="p-4">Product</th>
                <th className="p-4">Price</th>
                <th className="p-4">Stock</th>
                <th className="p-4">Status</th>
              </tr>
            </thead>
            <tbody>
              {products.map((product) => (
                <tr key={product.id} className="border-b border-ink/5">
                  <td className="p-4">{product.name}</td>
                  <td className="p-4">{money(product.price)}</td>
                  <td className="p-4">
                    <StockEditor product={product} onSaved={loadProducts} />
                  </td>
                  <td className="p-4">
                    <StatusChip status={product.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!products.length && <p className="p-6 text-sm text-ink-muted">No listings yet.</p>}
        </div>
      )}

      {tab === "orders" && <OrderTable orders={orders} allowStatus />}

      {tab === "new" && (
        <form onSubmit={createProduct} className="card mt-8 grid gap-4 p-6 sm:grid-cols-2">
          <div className="sm:col-span-2">
            <label className="label">Product name</label>
            <input className="field" {...register("name", { required: true })} />
          </div>
          <div>
            <label className="label">SKU</label>
            <input className="field" {...register("sku", { required: true })} />
          </div>
          <div>
            <label className="label">Category</label>
            <select className="field" {...register("category", { required: true })}>
              {categories.map((category) => (
                <option key={category.id} value={category.id}>
                  {category.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Price</label>
            <input className="field" type="number" step="0.01" {...register("price", { required: true })} />
          </div>
          <div>
            <label className="label">Compare at price</label>
            <input className="field" type="number" step="0.01" {...register("compare_at_price")} />
          </div>
          <div>
            <label className="label">Stock</label>
            <input className="field" type="number" {...register("stock")} />
          </div>
          <div>
            <label className="label">Image URL</label>
            <input className="field" {...register("thumbnail")} />
          </div>
          <div className="sm:col-span-2">
            <label className="label">Description</label>
            <textarea className="field h-28" {...register("description")} />
          </div>
          <button className="btn-primary sm:col-span-2">Submit for approval</button>
        </form>
      )}
    </div>
  );
}

function StockEditor({ product, onSaved }: { product: Product; onSaved: () => void }) {
  const [value, setValue] = useState(product.stock);
  return (
    <div className="flex items-center gap-2">
      <input
        type="number"
        className="field w-20 py-1"
        value={value}
        onChange={(event) => setValue(Number(event.target.value))}
      />
      {value !== product.stock && (
        <button
          className="text-xs text-forest-600 hover:underline"
          onClick={async () => {
            try {
              await api.patch(`/catalog/products/${product.slug}/`, { stock: value });
              toast.success("Stock updated");
              onSaved();
            } catch (error) {
              toast.error(apiError(error));
            }
          }}
        >
          Save
        </button>
      )}
    </div>
  );
}

function OrderTable({ orders, allowStatus }: { orders: Order[]; allowStatus?: boolean }) {
  const [rows, setRows] = useState(orders);
  useEffect(() => setRows(orders), [orders]);

  const setStatus = async (order: Order, status: string) => {
    try {
      const { data } = await api.post(`/orders/${order.order_number}/status/`, { status });
      setRows((current) => current.map((row) => (row.id === data.id ? data : row)));
      toast.success(`Marked as ${status.replace(/_/g, " ")}`);
    } catch (error) {
      toast.error(apiError(error));
    }
  };

  if (!rows.length) {
    return (
      <div className="mt-8">
        <EmptyState title="No orders yet" body="New orders appear here the moment they're placed." />
      </div>
    );
  }

  return (
    <div className="card mt-8 overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-ink/10 text-xs uppercase tracking-wider text-ink-muted">
          <tr>
            <th className="p-4">Order</th>
            <th className="p-4">Customer</th>
            <th className="p-4">Total</th>
            <th className="p-4">Status</th>
            {allowStatus && <th className="p-4">Update</th>}
          </tr>
        </thead>
        <tbody>
          {rows.map((order) => (
            <tr key={order.id} className="border-b border-ink/5">
              <td className="p-4 font-mono text-xs">{order.order_number}</td>
              <td className="p-4">{order.customer_email}</td>
              <td className="p-4">{money(order.total)}</td>
              <td className="p-4">
                <StatusChip status={order.status} />
              </td>
              {allowStatus && (
                <td className="p-4">
                  <select
                    className="field py-1"
                    value={order.status}
                    onChange={(event) => setStatus(order, event.target.value)}
                  >
                    {[
                      "confirmed",
                      "packed",
                      "ready_to_ship",
                      "shipped",
                      "out_for_delivery",
                      "delivered",
                    ].map((status) => (
                      <option key={status} value={status}>
                        {status.replace(/_/g, " ")}
                      </option>
                    ))}
                  </select>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ------------------------------------------------------------------ admin */

export function AdminDashboard() {
  const [tab, setTab] = useState<"overview" | "approvals" | "sellers" | "orders" | "users">("overview");
  const [stats, setStats] = useState<Record<string, unknown> | null>(null);
  const [pending, setPending] = useState<Product[]>([]);
  const [sellers, setSellers] = useState<Record<string, unknown>[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [users, setUsers] = useState<Record<string, unknown>[]>([]);
  const series = useSalesSeries();

  const loadAll = () => {
    api.get("/admin/dashboard/").then((response) => setStats(response.data));
    api
      .get("/catalog/products/?status=pending&page_size=50")
      .then((response) => setPending(response.data.results ?? response.data));
    api.get("/auth/sellers/").then((response) => setSellers(response.data.results ?? response.data));
    api.get("/orders/").then((response) => setOrders(response.data.results ?? response.data));
    api.get("/auth/users/").then((response) => setUsers(response.data.results ?? response.data));
  };

  useEffect(loadAll, []);

  const decide = async (product: Product, action: "approve" | "reject") => {
    try {
      await api.post(`/catalog/products/${product.slug}/${action}/`);
      toast.success(`Listing ${action}d`);
      loadAll();
    } catch (error) {
      toast.error(apiError(error));
    }
  };

  if (!stats) return <Spinner label="Loading admin data" />;

  const topProducts = (stats.top_products as { name: string; sold_count: number }[]) || [];

  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      <h1 className="text-4xl">Platform admin</h1>

      <div className={`mt-6 ${TABS}`}>
        <TabButton active={tab === "overview"} onClick={() => setTab("overview")}>
          Overview
        </TabButton>
        <TabButton active={tab === "approvals"} onClick={() => setTab("approvals")}>
          Approvals ({pending.length})
        </TabButton>
        <TabButton active={tab === "sellers"} onClick={() => setTab("sellers")}>
          Sellers
        </TabButton>
        <TabButton active={tab === "orders"} onClick={() => setTab("orders")}>
          Orders
        </TabButton>
        <TabButton active={tab === "users"} onClick={() => setTab("users")}>
          Users
        </TabButton>
      </div>

      {tab === "overview" && (
        <div className="mt-8 space-y-6">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label="Revenue" value={money(String(stats.revenue))} />
            <StatCard label="Orders" value={String(stats.orders)} />
            <StatCard label="Customers" value={String(stats.customers)} />
            <StatCard label="Sellers" value={String(stats.sellers)} hint={`${stats.pending_sellers} awaiting approval`} />
          </div>
          <div className="grid gap-6 lg:grid-cols-2">
            <div className="card p-6">
              <h2 className="text-xl">Revenue, last 30 days</h2>
              <RevenueChart data={series} />
            </div>
            <div className="card p-6">
              <h2 className="text-xl">Best sellers</h2>
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={topProducts}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" />
                  <XAxis dataKey="name" hide />
                  <YAxis fontSize={12} />
                  <Tooltip />
                  <Bar dataKey="sold_count" fill="#F0A81C" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

      {tab === "approvals" && (
        <div className="mt-8 space-y-3">
          {pending.length === 0 && (
            <EmptyState title="Nothing waiting" body="New seller listings show up here for review." />
          )}
          {pending.map((product) => (
            <div key={product.id} className="card flex flex-wrap items-center gap-4 p-4">
              <img src={product.thumbnail} alt="" className="h-16 w-16 rounded-lg object-cover" />
              <div className="flex-1">
                <p className="font-medium">{product.name}</p>
                <p className="text-xs text-ink-muted">
                  {product.store_name} · {money(product.price)} · SKU {product.sku}
                </p>
              </div>
              <button className="btn-primary" onClick={() => decide(product, "approve")}>
                Approve
              </button>
              <button className="btn-ghost text-red-600" onClick={() => decide(product, "reject")}>
                Reject
              </button>
            </div>
          ))}
        </div>
      )}

      {tab === "sellers" && (
        <div className="mt-8 space-y-3">
          {sellers.map((seller) => (
            <div key={String(seller.id)} className="card flex flex-wrap items-center gap-4 p-4">
              <div className="flex-1">
                <p className="font-medium">{String(seller.store_name)}</p>
                <p className="text-xs text-ink-muted">{String(seller.email)}</p>
              </div>
              <StatusChip status={seller.is_approved ? "approved" : "pending"} />
              {!seller.is_approved && (
                <button
                  className="btn-primary"
                  onClick={async () => {
                    await api.post(`/auth/sellers/${seller.id}/approve/`);
                    toast.success("Store approved");
                    loadAll();
                  }}
                >
                  Approve store
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {tab === "orders" && <OrderTable orders={orders} allowStatus />}

      {tab === "users" && (
        <div className="card mt-8 overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-ink/10 text-xs uppercase tracking-wider text-ink-muted">
              <tr>
                <th className="p-4">Email</th>
                <th className="p-4">Name</th>
                <th className="p-4">Role</th>
                <th className="p-4">Verified</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={String(user.id)} className="border-b border-ink/5">
                  <td className="p-4">{String(user.email)}</td>
                  <td className="p-4">{String(user.full_name)}</td>
                  <td className="p-4">
                    <span className="chip bg-paper-sunk text-ink-soft">{String(user.role)}</span>
                  </td>
                  <td className="p-4">{user.is_verified ? "Yes" : "No"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ inventory */

export function InventoryDashboard() {
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [movement, setMovement] = useState({ product: "", movement_type: "in", quantity: 1 });
  const [products, setProducts] = useState<Product[]>([]);

  const load = () => {
    api.get("/inventory/dashboard/").then((response) => setData(response.data));
    api
      .get("/catalog/products/?page_size=100")
      .then((response) => setProducts(response.data.results ?? response.data));
  };

  useEffect(load, []);

  if (!data) return <Spinner label="Loading warehouse data" />;

  const lowStock = (data.low_stock_items as Record<string, unknown>[]) || [];
  const movements = (data.recent_movements as Record<string, unknown>[]) || [];

  const record = async (event: React.FormEvent) => {
    event.preventDefault();
    try {
      await api.post("/inventory/movements/", {
        product: Number(movement.product),
        movement_type: movement.movement_type,
        quantity: Number(movement.quantity),
        note: "Manual entry",
      });
      toast.success("Stock movement recorded");
      load();
    } catch (error) {
      toast.error(apiError(error));
    }
  };

  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      <h1 className="text-4xl">Warehouse</h1>

      <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Units on hand" value={String(data.total_units)} />
        <StatCard label="Low stock" value={String(data.low_stock)} hint="At or below threshold" />
        <StatCard label="Out of stock" value={String(data.out_of_stock)} />
        <StatCard label="Open purchase orders" value={String(data.open_purchase_orders)} />
      </div>

      <div className="mt-8 grid gap-6 lg:grid-cols-2">
        <form onSubmit={record} className="card p-6">
          <h2 className="text-xl">Record a stock movement</h2>
          <label className="label mt-4">Product</label>
          <select
            className="field"
            value={movement.product}
            onChange={(event) => setMovement({ ...movement, product: event.target.value })}
            required
          >
            <option value="">Choose a product</option>
            {products.map((product) => (
              <option key={product.id} value={product.id}>
                {product.name} (on hand: {product.stock})
              </option>
            ))}
          </select>
          <div className="mt-4 grid grid-cols-2 gap-3">
            <div>
              <label className="label">Type</label>
              <select
                className="field"
                value={movement.movement_type}
                onChange={(event) =>
                  setMovement({ ...movement, movement_type: event.target.value })
                }
              >
                <option value="in">Stock in</option>
                <option value="out">Stock out</option>
                <option value="adjust">Adjustment</option>
              </select>
            </div>
            <div>
              <label className="label">Quantity</label>
              <input
                type="number"
                className="field"
                value={movement.quantity}
                onChange={(event) =>
                  setMovement({ ...movement, quantity: Number(event.target.value) })
                }
              />
            </div>
          </div>
          <button className="btn-primary mt-5 w-full">Record movement</button>
          <button
            type="button"
            className="btn-ghost mt-2 w-full"
            onClick={async () => {
              try {
                const { data: result } = await api.post("/inventory/auto-reorder/");
                toast.success(result.detail);
                load();
              } catch (error) {
                toast.error(apiError(error));
              }
            }}
          >
            Draft reorder for low stock
          </button>
        </form>

        <div className="card p-6">
          <h2 className="text-xl">Needs restocking</h2>
          {lowStock.length === 0 ? (
            <p className="mt-4 text-sm text-ink-muted">Everything is above its threshold.</p>
          ) : (
            <ul className="mt-4 space-y-2 text-sm">
              {lowStock.map((item) => (
                <li key={String(item.id)} className="flex justify-between border-b border-ink/5 pb-2">
                  <span>{String(item.name)}</span>
                  <span className="text-amber-500">
                    {String(item.stock)} left (threshold {String(item.low_stock_threshold)})
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <div className="card mt-6 p-6">
        <h2 className="text-xl">Recent movements</h2>
        <ul className="mt-4 space-y-2 text-sm">
          {movements.map((row) => (
            <li key={String(row.id)} className="flex justify-between border-b border-ink/5 pb-2">
              <span>{String(row.product_name)}</span>
              <span className="text-ink-muted">
                {String(row.movement_type)} · {String(row.quantity)} ·{" "}
                {new Date(String(row.created_at)).toLocaleString()}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ delivery */

export function DeliveryDashboard() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [otp, setOtp] = useState<Record<string, string>>({});

  const load = () =>
    api.get("/orders/").then((response) => setOrders(response.data.results ?? response.data));

  useEffect(() => {
    load();
  }, []);

  const confirm = async (order: Order) => {
    try {
      await api.post(`/orders/${order.order_number}/confirm-delivery/`, {
        otp: otp[order.order_number],
      });
      toast.success("Delivery confirmed");
      load();
    } catch (error) {
      toast.error(apiError(error, "That OTP didn't match."));
    }
  };

  const active = orders.filter((order) => order.status !== "delivered");
  const done = orders.filter((order) => order.status === "delivered");

  return (
    <div className="mx-auto max-w-4xl px-4 py-10">
      <h1 className="text-4xl">Deliveries</h1>
      <div className="mt-6 grid gap-4 sm:grid-cols-3">
        <StatCard label="Assigned" value={active.length} />
        <StatCard label="Completed" value={done.length} />
        <StatCard label="Earnings" value={money(done.length * 40)} hint="At 40 per delivery" />
      </div>

      <h2 className="mt-10 text-2xl">Active runs</h2>
      {active.length === 0 ? (
        <div className="mt-4">
          <EmptyState
            title="Nothing assigned right now"
            body="An admin assigns orders to you; they appear here with a customer OTP to verify."
          />
        </div>
      ) : (
        <div className="mt-4 space-y-3">
          {active.map((order) => (
            <div key={order.id} className="card p-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="font-mono text-sm">{order.order_number}</p>
                  <p className="text-xs text-ink-muted">
                    {order.shipping_address.full_name} · {order.shipping_address.line1},{" "}
                    {order.shipping_address.city}
                  </p>
                </div>
                <StatusChip status={order.status} />
              </div>
              <div className="mt-4 flex gap-2">
                <input
                  className="field w-40"
                  placeholder="Customer OTP"
                  value={otp[order.order_number] || ""}
                  onChange={(event) =>
                    setOtp({ ...otp, [order.order_number]: event.target.value })
                  }
                />
                <button className="btn-primary" onClick={() => confirm(order)}>
                  Confirm delivery
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
