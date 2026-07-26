import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import toast from "react-hot-toast";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";

import { EmptyState, Spinner, StatusChip } from "../components";
import { api, apiError, money } from "../lib/api";
import { useAppDispatch, useAppSelector } from "../store";
import { loadUser, login, register as registerUser } from "../store/authSlice";
import { applyCoupon, fetchCart, removeCartItem, updateCartItem } from "../store/cartSlice";
import type { Address, Order } from "../types";

const ROLE_HOME: Record<string, string> = {
  customer: "/",
  seller: "/seller",
  admin: "/admin",
  inventory: "/inventory",
  delivery: "/delivery",
};

/* ------------------------------------------------------------------ login */

export function Login() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const location = useLocation() as { state?: { from?: string } };
  const { register, handleSubmit, formState } = useForm<{ email: string; password: string }>();

  const onSubmit = handleSubmit(async (values) => {
    try {
      const user = await dispatch(login(values)).unwrap();
      toast.success(`Welcome back, ${user.full_name || user.email}`);
      navigate(location.state?.from || ROLE_HOME[user.role] || "/");
    } catch (error) {
      toast.error(apiError(error, "Those details didn't match an account."));
    }
  });

  return (
    <div className="mx-auto grid max-w-5xl gap-10 px-4 py-16 md:grid-cols-2">
      <div>
        <h1 className="text-4xl">Sign in</h1>
        <p className="mt-3 text-ink-muted">
          One account works across shopping, selling, warehouse and delivery — your role decides
          what you see.
        </p>
        <div className="card mt-6 p-5 text-sm">
          <p className="label">Demo accounts (password: Password123!)</p>
          <ul className="mt-2 space-y-1 font-mono text-xs text-ink-muted">
            <li>customer@shop.test</li>
            <li>seller@shop.test</li>
            <li>admin@shop.test</li>
            <li>inventory@shop.test</li>
            <li>delivery@shop.test</li>
          </ul>
        </div>
      </div>

      <form onSubmit={onSubmit} className="card h-fit p-6">
        <label className="label">Email</label>
        <input className="field" type="email" {...register("email", { required: true })} />
        <label className="label mt-4">Password</label>
        <input className="field" type="password" {...register("password", { required: true })} />
        <button className="btn-primary mt-6 w-full" disabled={formState.isSubmitting}>
          {formState.isSubmitting ? "Signing in" : "Sign in"}
        </button>
        <p className="mt-4 text-center text-sm text-ink-muted">
          New here?{" "}
          <Link className="text-forest-600 hover:underline" to="/register">
            Create an account
          </Link>
        </p>
      </form>
    </div>
  );
}

/* ------------------------------------------------------------------ register */

export function Register() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const [role, setRole] = useState("customer");
  const { register, handleSubmit, formState } = useForm<Record<string, string>>();

  const onSubmit = handleSubmit(async (values) => {
    try {
      await dispatch(registerUser({ ...values, role })).unwrap();
      await dispatch(login({ email: values.email, password: values.password })).unwrap();
      toast.success("Account created. Check the API console for your verification code.");
      navigate(role === "seller" ? "/seller" : "/");
    } catch (error) {
      toast.error(apiError(error, "Couldn't create that account."));
    }
  });

  return (
    <div className="mx-auto max-w-lg px-4 py-16">
      <h1 className="text-4xl">Create an account</h1>
      <form onSubmit={onSubmit} className="card mt-6 p-6">
        <div className="flex gap-2">
          {["customer", "seller"].map((option) => (
            <button
              type="button"
              key={option}
              onClick={() => setRole(option)}
              className={role === option ? "btn-primary flex-1" : "btn-ghost flex-1"}
            >
              {option === "customer" ? "Shop" : "Sell"}
            </button>
          ))}
        </div>

        <label className="label mt-5">Full name</label>
        <input className="field" {...register("full_name", { required: true })} />

        <label className="label mt-4">Email</label>
        <input className="field" type="email" {...register("email", { required: true })} />

        <label className="label mt-4">Phone</label>
        <input className="field" {...register("phone")} />

        {role === "seller" && (
          <>
            <label className="label mt-4">Store name</label>
            <input className="field" {...register("store_name", { required: true })} />
            <p className="mt-1 text-xs text-ink-muted">
              An admin reviews new stores before listings go live.
            </p>
          </>
        )}

        <label className="label mt-4">Password</label>
        <input
          className="field"
          type="password"
          {...register("password", { required: true, minLength: 8 })}
        />
        <p className="mt-1 text-xs text-ink-muted">At least 8 characters, not all numbers.</p>

        <button className="btn-primary mt-6 w-full" disabled={formState.isSubmitting}>
          Create account
        </button>
      </form>
    </div>
  );
}

/* ------------------------------------------------------------------ cart */

export function CartPage() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const cart = useAppSelector((state) => state.cart.cart);
  const [code, setCode] = useState("");

  useEffect(() => {
    dispatch(fetchCart());
  }, [dispatch]);

  if (!cart) return <Spinner label="Loading your cart" />;

  if (!cart.items.length) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-24">
        <EmptyState
          title="Your cart is empty"
          body="Browse departments and add something you like — items stay here across sessions."
          action={
            <Link className="btn-primary" to="/products">
              Browse products
            </Link>
          }
        />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      <h1 className="text-4xl">Your cart</h1>
      <div className="mt-8 grid gap-8 lg:grid-cols-[1fr_340px]">
        <div className="space-y-4">
          {cart.items.map((item) => (
            <div key={item.id} className="card flex gap-4 p-4">
              <img
                src={item.product_detail.thumbnail}
                alt=""
                className="h-24 w-24 rounded-lg object-cover"
              />
              <div className="flex-1">
                <Link to={`/product/${item.product_detail.slug}`} className="font-medium">
                  {item.product_detail.name}
                </Link>
                <p className="text-sm text-ink-muted">{item.product_detail.store_name}</p>
                <div className="mt-3 flex items-center gap-3">
                  <input
                    type="number"
                    min={1}
                    value={item.quantity}
                    onChange={(event) =>
                      dispatch(
                        updateCartItem({ itemId: item.id, quantity: Number(event.target.value) }),
                      )
                    }
                    className="field w-20 py-1.5"
                    aria-label={`Quantity for ${item.product_detail.name}`}
                  />
                  <button
                    className="text-sm text-red-600 hover:underline"
                    onClick={() => dispatch(removeCartItem(item.id))}
                  >
                    Remove
                  </button>
                </div>
              </div>
              <p className="font-display text-lg">{money(item.subtotal)}</p>
            </div>
          ))}
        </div>

        <aside className="card h-fit p-6">
          <h2 className="text-xl">Summary</h2>
          <div className="mt-4 flex justify-between text-sm">
            <span>Subtotal</span>
            <span>{money(cart.subtotal)}</span>
          </div>
          <div className="mt-2 flex justify-between text-sm text-ink-muted">
            <span>Delivery</span>
            <span>{Number(cart.subtotal) >= 999 ? "Free" : money(49)}</span>
          </div>

          <label className="label mt-5">Coupon code</label>
          <div className="flex gap-2">
            <input
              className="field"
              value={code}
              onChange={(event) => setCode(event.target.value.toUpperCase())}
              placeholder="WELCOME10"
            />
            <button
              className="btn-ghost"
              onClick={async () => {
                try {
                  await dispatch(applyCoupon(code)).unwrap();
                  toast.success("Coupon applied");
                } catch (error) {
                  toast.error(apiError(error, "That coupon isn't valid for this cart."));
                }
              }}
            >
              Apply
            </button>
          </div>
          {cart.coupon_code && (
            <p className="mt-2 text-sm text-forest-600">{cart.coupon_code} applied at checkout.</p>
          )}

          <button className="btn-primary mt-6 w-full" onClick={() => navigate("/checkout")}>
            Continue to checkout
          </button>
        </aside>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ checkout */

export function Checkout() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const cart = useAppSelector((state) => state.cart.cart);
  const [addresses, setAddresses] = useState<Address[]>([]);
  const [addressId, setAddressId] = useState<number | null>(null);
  const [method, setMethod] = useState("cod");
  const [placing, setPlacing] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const { register, handleSubmit, reset } = useForm<Address>();

  const loadAddresses = () =>
    api.get("/auth/addresses/").then((response) => {
      const list = response.data.results ?? response.data;
      setAddresses(list);
      if (list.length) setAddressId(list[0].id);
      else setShowForm(true);
    });

  useEffect(() => {
    dispatch(fetchCart());
    loadAddresses();
  }, [dispatch]);

  const saveAddress = handleSubmit(async (values) => {
    try {
      await api.post("/auth/addresses/", { ...values, is_default: true });
      toast.success("Address saved");
      reset();
      setShowForm(false);
      loadAddresses();
    } catch (error) {
      toast.error(apiError(error));
    }
  });

  const placeOrder = async () => {
    if (!addressId) return toast.error("Add a delivery address first.");
    setPlacing(true);
    try {
      const { data } = await api.post("/orders/checkout/", {
        address_id: addressId,
        payment_method: method,
        coupon_code: cart?.coupon_code || "",
      });
      await dispatch(fetchCart());
      toast.success(`Order ${data.order_number} placed`);
      navigate(`/orders/${data.order_number}`);
    } catch (error) {
      toast.error(apiError(error, "Checkout failed."));
    } finally {
      setPlacing(false);
    }
  };

  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      <h1 className="text-4xl">Checkout</h1>
      <div className="mt-8 grid gap-8 lg:grid-cols-[1fr_340px]">
        <div className="space-y-6">
          <section className="card p-6">
            <h2 className="text-xl">Delivery address</h2>
            <div className="mt-4 space-y-3">
              {addresses.map((address) => (
                <label
                  key={address.id}
                  className={`flex cursor-pointer gap-3 rounded-lg border p-4 text-sm ${
                    addressId === address.id
                      ? "border-forest-500 bg-forest-50 dark:bg-night-line"
                      : "border-ink/10"
                  }`}
                >
                  <input
                    type="radio"
                    checked={addressId === address.id}
                    onChange={() => setAddressId(address.id)}
                  />
                  <span>
                    <strong>{address.label}</strong> · {address.full_name}
                    <br />
                    {address.line1}, {address.city}, {address.state} {address.postal_code}
                  </span>
                </label>
              ))}
            </div>
            <button className="btn-ghost mt-4" onClick={() => setShowForm(!showForm)}>
              {showForm ? "Cancel" : "Add a new address"}
            </button>

            {showForm && (
              <form onSubmit={saveAddress} className="mt-4 grid gap-3 sm:grid-cols-2">
                <input className="field" placeholder="Label (Home)" {...register("label")} />
                <input
                  className="field"
                  placeholder="Full name"
                  {...register("full_name", { required: true })}
                />
                <input
                  className="field"
                  placeholder="Phone"
                  {...register("phone", { required: true })}
                />
                <input
                  className="field"
                  placeholder="Address line 1"
                  {...register("line1", { required: true })}
                />
                <input className="field" placeholder="City" {...register("city", { required: true })} />
                <input
                  className="field"
                  placeholder="State"
                  {...register("state", { required: true })}
                />
                <input
                  className="field"
                  placeholder="Postal code"
                  {...register("postal_code", { required: true })}
                />
                <button className="btn-primary sm:col-span-2">Save address</button>
              </form>
            )}
          </section>

          <section className="card p-6">
            <h2 className="text-xl">Payment</h2>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              {[
                ["cod", "Cash on delivery"],
                ["card", "Card"],
                ["upi", "UPI"],
                ["wallet", "Wallet balance"],
              ].map(([value, label]) => (
                <label
                  key={value}
                  className={`flex cursor-pointer items-center gap-3 rounded-lg border p-4 text-sm ${
                    method === value ? "border-forest-500 bg-forest-50 dark:bg-night-line" : "border-ink/10"
                  }`}
                >
                  <input type="radio" checked={method === value} onChange={() => setMethod(value)} />
                  {label}
                </label>
              ))}
            </div>
            <p className="mt-3 text-xs text-ink-muted">
              Card and UPI are wired to a mock gateway. Swap in Stripe or Razorpay keys in the
              backend payment service to go live.
            </p>
          </section>
        </div>

        <aside className="card h-fit p-6">
          <h2 className="text-xl">Order summary</h2>
          <ul className="mt-4 space-y-2 text-sm">
            {cart?.items.map((item) => (
              <li key={item.id} className="flex justify-between gap-3">
                <span className="line-clamp-1">
                  {item.product_detail.name} × {item.quantity}
                </span>
                <span>{money(item.subtotal)}</span>
              </li>
            ))}
          </ul>
          <div className="mt-4 border-t border-ink/10 pt-4 text-sm">
            <div className="flex justify-between">
              <span>Subtotal</span>
              <span>{money(cart?.subtotal || 0)}</span>
            </div>
            {cart?.coupon_code && (
              <div className="mt-1 flex justify-between text-forest-600">
                <span>Coupon</span>
                <span>{cart.coupon_code}</span>
              </div>
            )}
          </div>
          <button className="btn-primary mt-6 w-full" onClick={placeOrder} disabled={placing}>
            {placing ? "Placing order" : "Place order"}
          </button>
        </aside>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ orders */

export function Orders() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const user = useAppSelector((state) => state.auth.user);

  useEffect(() => {
    api
      .get("/orders/")
      .then((response) => setOrders(response.data.results ?? response.data))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Spinner label="Loading orders" />;

  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      <h1 className="text-4xl">{user?.role === "customer" ? "Your orders" : "Orders"}</h1>
      {orders.length === 0 ? (
        <div className="mt-8">
          <EmptyState
            title="No orders yet"
            body="Once an order is placed it shows up here with a full status timeline."
            action={
              <Link className="btn-primary" to="/products">
                Start shopping
              </Link>
            }
          />
        </div>
      ) : (
        <div className="mt-8 space-y-4">
          {orders.map((order) => (
            <Link key={order.id} to={`/orders/${order.order_number}`} className="card block p-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="font-mono text-sm">{order.order_number}</p>
                  <p className="text-xs text-ink-muted">
                    {new Date(order.created_at).toLocaleString()} · {order.items.length} items
                  </p>
                </div>
                <StatusChip status={order.status} />
                <p className="font-display text-xl">{money(order.total)}</p>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

export function OrderDetail() {
  const { orderNumber } = useParams();
  const [order, setOrder] = useState<Order | null>(null);

  const load = () =>
    api.get(`/orders/${orderNumber}/`).then((response) => setOrder(response.data));

  useEffect(() => {
    load();
  }, [orderNumber]);

  if (!order) return <Spinner label="Loading order" />;

  const cancel = async () => {
    try {
      await api.post(`/orders/${order.order_number}/cancel/`);
      toast.success("Order cancelled and stock returned");
      load();
    } catch (error) {
      toast.error(apiError(error));
    }
  };

  const downloadInvoice = async () => {
    const { data } = await api.get(`/orders/${order.order_number}/invoice/`);
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${data.invoice_number}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="mx-auto max-w-4xl px-4 py-10">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-mono text-2xl">{order.order_number}</h1>
          <p className="text-sm text-ink-muted">
            Placed {new Date(order.created_at).toLocaleString()}
          </p>
        </div>
        <StatusChip status={order.status} />
      </div>

      <div className="mt-8 grid gap-6 lg:grid-cols-[1fr_320px]">
        <div className="space-y-6">
          <section className="card p-5">
            <h2 className="text-lg">Items</h2>
            <ul className="mt-4 space-y-3">
              {order.items.map((item) => (
                <li key={item.id} className="flex items-center gap-4">
                  <img src={item.thumbnail} alt="" className="h-16 w-16 rounded-lg object-cover" />
                  <div className="flex-1">
                    <p className="font-medium">{item.product_name}</p>
                    <p className="text-xs text-ink-muted">
                      {item.store_name} · {item.quantity} × {money(item.unit_price)}
                    </p>
                  </div>
                  <span>{money(item.subtotal)}</span>
                </li>
              ))}
            </ul>
          </section>

          <section className="card p-5">
            <h2 className="text-lg">Timeline</h2>
            <ol className="mt-4 space-y-3">
              {order.events.map((event) => (
                <li key={event.id} className="flex gap-3 text-sm">
                  <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-forest-500" />
                  <div>
                    <p className="capitalize">{event.status.replace(/_/g, " ")}</p>
                    <p className="text-xs text-ink-muted">
                      {new Date(event.created_at).toLocaleString()} {event.note}
                    </p>
                  </div>
                </li>
              ))}
            </ol>
          </section>
        </div>

        <aside className="card h-fit p-5 text-sm">
          <h2 className="text-lg">Payment</h2>
          <dl className="mt-3 space-y-2">
            <Row label="Subtotal" value={money(order.subtotal)} />
            <Row label="Discount" value={`- ${money(order.discount)}`} />
            <Row label="Tax" value={money(order.tax)} />
            <Row label="Delivery" value={money(order.shipping_fee)} />
            <Row label="Total" value={money(order.total)} strong />
            <Row label="Method" value={order.payment_method.toUpperCase()} />
            <Row label="Status" value={order.payment_status} />
          </dl>
          <div className="mt-4 border-t border-ink/10 pt-4">
            <p className="label">Ships to</p>
            <p className="text-ink-muted">
              {order.shipping_address.full_name}
              <br />
              {order.shipping_address.line1}, {order.shipping_address.city}
              <br />
              {order.shipping_address.state} {order.shipping_address.postal_code}
            </p>
          </div>
          <button className="btn-ghost mt-4 w-full" onClick={downloadInvoice}>
            Download invoice
          </button>
          {!["delivered", "cancelled", "shipped", "out_for_delivery"].includes(order.status) && (
            <button className="btn-ghost mt-2 w-full text-red-600" onClick={cancel}>
              Cancel order
            </button>
          )}
        </aside>
      </div>
    </div>
  );
}

function Row({ label, value, strong }: { label: string; value: string; strong?: boolean }) {
  return (
    <div className={`flex justify-between ${strong ? "font-display text-lg" : ""}`}>
      <dt className="text-ink-muted">{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

/* ------------------------------------------------------------------ profile */

export function Profile() {
  const dispatch = useAppDispatch();
  const user = useAppSelector((state) => state.auth.user);
  const { register, handleSubmit } = useForm({ defaultValues: user || {} });

  const save = handleSubmit(async (values) => {
    try {
      await api.patch("/auth/me/", { full_name: values.full_name, phone: values.phone });
      dispatch(loadUser());
      toast.success("Profile updated");
    } catch (error) {
      toast.error(apiError(error));
    }
  });

  if (!user) return null;

  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      <h1 className="text-4xl">Your profile</h1>
      <form onSubmit={save} className="card mt-6 p-6">
        <label className="label">Full name</label>
        <input className="field" {...register("full_name")} />
        <label className="label mt-4">Phone</label>
        <input className="field" {...register("phone")} />
        <label className="label mt-4">Email</label>
        <input className="field" value={user.email} disabled />
        <button className="btn-primary mt-6">Save changes</button>
      </form>

      <div className="mt-6 grid gap-4 sm:grid-cols-3">
        <div className="card p-5">
          <p className="label">Wallet</p>
          <p className="font-display text-2xl">{money(user.wallet_balance)}</p>
        </div>
        <div className="card p-5">
          <p className="label">Loyalty points</p>
          <p className="font-display text-2xl">{user.loyalty_points}</p>
        </div>
        <div className="card p-5">
          <p className="label">Referral code</p>
          <p className="font-mono text-lg">{user.referral_code}</p>
        </div>
      </div>
    </div>
  );
}
