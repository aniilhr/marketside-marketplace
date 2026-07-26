import { motion } from "framer-motion";
import { useState } from "react";
import { useForm } from "react-hook-form";
import toast from "react-hot-toast";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { apiError } from "../lib/api";
import { useAppDispatch } from "../store";
import { login, register as registerUser } from "../store/authSlice";

/* Set to false before a public deployment to hide the demo account picker. */
const SHOW_DEMO_ACCOUNTS = false;
const DEMO_PASSWORD = "";

const ROLE_HOME: Record<string, string> = {
  customer: "/",
  seller: "/seller",
  admin: "/admin",
  inventory: "/inventory",
  delivery: "/delivery",
};

const DEMO_ROLES = [
  { id: "customer", label: "Customer", email: "customer@shop.test", blurb: "Shop, cart and track orders" },
  { id: "seller", label: "Seller", email: "seller@shop.test", blurb: "Listings, orders and revenue" },
  { id: "admin", label: "Admin", email: "admin@shop.test", blurb: "Approvals and platform metrics" },
  { id: "inventory", label: "Inventory", email: "inventory@shop.test", blurb: "Stock, warehouses, reorders" },
  { id: "delivery", label: "Delivery", email: "delivery@shop.test", blurb: "Runs and OTP confirmation" },
];

const ICONS: Record<string, string> = {
  customer: "M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4zM3 6h18M16 10a4 4 0 0 1-8 0",
  seller: "M3 9h18l-1.5-5h-15zM4 9v11a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1V9M9 21v-6h6v6",
  admin: "M12 2 4 6v6c0 5 3.4 9.4 8 10 4.6-.6 8-5 8-10V6zM9 12l2 2 4-4",
  inventory: "M21 8 12 3 3 8v8l9 5 9-5zM3 8l9 5 9-5M12 13v8",
  delivery: "M1 3h13v13H1zM14 8h4l3 3v5h-7M6.5 19a2 2 0 1 0 0-4 2 2 0 0 0 0 4M17.5 19a2 2 0 1 0 0-4 2 2 0 0 0 0 4",
};

function Icon({ name, className = "h-5 w-5" }: { name: string; className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <path d={ICONS[name]} />
    </svg>
  );
}

/* ---------------------------------------------------------------- shell */

function AuthShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid min-h-[calc(100vh-4rem)] lg:grid-cols-[1.05fr_1fr]">
      {/* Brand panel */}
      <aside className="brand-panel relative hidden flex-col justify-between p-12 text-white lg:flex">
        <div className="relative z-10">
          <Link to="/" className="font-display text-2xl font-extrabold tracking-tight">
            market<span className="text-amber-400">side</span>
          </Link>
        </div>

        <div className="relative z-10 max-w-md">
          <h2 className="font-display text-5xl font-extrabold leading-[1.05]">
            One account.
            <br />
            Every side of
            <br />
            the marketplace.
          </h2>
          <p className="mt-5 text-white/70">
            Shoppers, sellers, warehouse staff and delivery partners all sign in here. Your role
            decides what opens next.
          </p>

          <ul className="mt-9 space-y-4">
            {[
              ["seller", "Sellers get their own storefront and payouts"],
              ["inventory", "Stock updates the moment an order is placed"],
              ["delivery", "Deliveries confirmed with a customer OTP"],
            ].map(([icon, text]) => (
              <li key={icon} className="flex items-center gap-3 text-sm text-white/85">
                <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-white/10 ring-1 ring-white/15">
                  <Icon name={icon} className="h-4 w-4" />
                </span>
                {text}
              </li>
            ))}
          </ul>
        </div>

        <div className="relative z-10 flex gap-8 text-sm text-white/60">
          <div>
            <p className="font-display text-2xl text-white">5</p>
            <p>roles</p>
          </div>
          <div>
            <p className="font-display text-2xl text-white">91</p>
            <p>endpoints</p>
          </div>
          <div>
            <p className="font-display text-2xl text-white">10</p>
            <p>order states</p>
          </div>
        </div>
      </aside>

      {/* Form panel */}
      <section className="flex items-center justify-center px-4 py-12 sm:px-8">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, ease: "easeOut" }}
          className="w-full max-w-md"
        >
          {children}
        </motion.div>
      </section>
    </div>
  );
}

function Tabs({ mode }: { mode: "login" | "register" }) {
  return (
    <div className="mb-8 grid grid-cols-2 gap-1 rounded-full bg-paper-sunk p-1 dark:bg-night-line">
      <Link
        to="/login"
        className={`rounded-full py-2.5 text-center text-sm font-medium transition ${
          mode === "login" ? "bg-paper-raised shadow-sm dark:bg-night-raised" : "text-ink-muted"
        }`}
      >
        Sign in
      </Link>
      <Link
        to="/register"
        className={`rounded-full py-2.5 text-center text-sm font-medium transition ${
          mode === "register" ? "bg-paper-raised shadow-sm dark:bg-night-raised" : "text-ink-muted"
        }`}
      >
        Create account
      </Link>
    </div>
  );
}

function PasswordField({
  registration,
  placeholder = "Your password",
  autoComplete = "current-password",
}: {
  registration: Record<string, unknown>;
  placeholder?: string;
  autoComplete?: string;
}) {
  const [visible, setVisible] = useState(false);
  return (
    <div className="relative">
      <input
        className="field pr-16"
        type={visible ? "text" : "password"}
        placeholder={placeholder}
        autoComplete={autoComplete}
        {...registration}
      />
      <button
        type="button"
        onClick={() => setVisible(!visible)}
        className="absolute right-3 top-1/2 -translate-y-1/2 text-xs font-semibold uppercase tracking-wide text-ink-muted transition hover:text-forest-600"
      >
        {visible ? "Hide" : "Show"}
      </button>
    </div>
  );
}

/* ---------------------------------------------------------------- login */

export function Login() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const location = useLocation() as { state?: { from?: string } };
  const [picked, setPicked] = useState<string | null>(null);
  const { register, handleSubmit, setValue, formState } = useForm<{
    email: string;
    password: string;
  }>();

  const quickFill = (role: (typeof DEMO_ROLES)[number]) => {
    setPicked(role.id);
    setValue("email", role.email, { shouldValidate: true });
    setValue("password", DEMO_PASSWORD, { shouldValidate: true });
  };

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
    <AuthShell>
      <Tabs mode="login" />

      <h1 className="text-4xl">Welcome back</h1>
      <p className="mt-2 text-sm text-ink-muted">
        Sign in and we'll take you to the right dashboard for your role.
      </p>

      {SHOW_DEMO_ACCOUNTS && (
        <div className="mt-7">
          <p className="label">Try a demo account — tap to fill</p>
          <div className="grid gap-2 sm:grid-cols-2">
            {DEMO_ROLES.map((role) => (
              <button
                key={role.id}
                type="button"
                onClick={() => quickFill(role)}
                className={`role-tile ${picked === role.id ? "role-tile-active" : ""}`}
              >
                <span className="role-tile-icon">
                  <Icon name={role.id} />
                </span>
                <span className="min-w-0 text-left">
                  <span className="block text-sm font-semibold">{role.label}</span>
                  <span className="block truncate text-xs text-ink-muted">{role.blurb}</span>
                </span>
              </button>
            ))}
          </div>
          <p className="mt-2 text-xs text-ink-muted">
            All demo accounts use the password{" "}
            <code className="rounded bg-paper-sunk px-1.5 py-0.5 font-mono dark:bg-night-line">
              {DEMO_PASSWORD}
            </code>
          </p>
        </div>
      )}

      <form onSubmit={onSubmit} className="mt-7 space-y-4">
        <div>
          <label className="label">Email address</label>
          <input
            className="field"
            type="email"
            placeholder="you@example.com"
            autoComplete="email"
            {...register("email", { required: "Enter your email address" })}
          />
          {formState.errors.email && (
            <p className="mt-1.5 text-xs text-red-600">{formState.errors.email.message}</p>
          )}
        </div>

        <div>
          <div className="flex items-baseline justify-between">
            <label className="label">Password</label>
            <Link to="/login" className="mb-1.5 text-xs font-medium text-forest-600 hover:underline">
              Forgot password?
            </Link>
          </div>
          <PasswordField registration={register("password", { required: "Enter your password" })} />
          {formState.errors.password && (
            <p className="mt-1.5 text-xs text-red-600">{formState.errors.password.message}</p>
          )}
        </div>

        <label className="flex cursor-pointer items-center gap-2 text-sm text-ink-muted">
          <input type="checkbox" className="checkbox" defaultChecked />
          Keep me signed in on this device
        </label>

        <button className="btn-primary w-full" disabled={formState.isSubmitting}>
          {formState.isSubmitting ? (
            <>
              <span className="spinner" /> Signing in
            </>
          ) : (
            "Sign in"
          )}
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-ink-muted">
        New to Marketside?{" "}
        <Link className="font-medium text-forest-600 hover:underline" to="/register">
          Create an account
        </Link>
      </p>
    </AuthShell>
  );
}

/* ---------------------------------------------------------------- register */

export function Register() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const [role, setRole] = useState<"customer" | "seller">("customer");
  const { register, handleSubmit, formState } = useForm<Record<string, string>>();

  const onSubmit = handleSubmit(async (values) => {
    try {
      await dispatch(registerUser({ ...values, role })).unwrap();
      await dispatch(login({ email: values.email, password: values.password })).unwrap();
      toast.success("Account created. Your verification code is in the API console.");
      navigate(role === "seller" ? "/seller" : "/");
    } catch (error) {
      toast.error(apiError(error, "Couldn't create that account."));
    }
  });

  return (
    <AuthShell>
      <Tabs mode="register" />

      <h1 className="text-4xl">Create an account</h1>
      <p className="mt-2 text-sm text-ink-muted">
        Takes under a minute. You can switch to selling later from your profile.
      </p>

      <div className="mt-7 grid grid-cols-2 gap-3">
        {[
          { id: "customer", title: "I want to shop", blurb: "Browse and buy from every store" },
          { id: "seller", title: "I want to sell", blurb: "Open a storefront of your own" },
        ].map((option) => (
          <button
            key={option.id}
            type="button"
            onClick={() => setRole(option.id as "customer" | "seller")}
            className={`choice-card ${role === option.id ? "choice-card-active" : ""}`}
          >
            <Icon name={option.id} className="h-5 w-5" />
            <span className="mt-2 block text-sm font-semibold">{option.title}</span>
            <span className="mt-0.5 block text-xs text-ink-muted">{option.blurb}</span>
          </button>
        ))}
      </div>

      <form onSubmit={onSubmit} className="mt-6 space-y-4">
        <div>
          <label className="label">Full name</label>
          <input
            className="field"
            placeholder="Anil Kumar"
            autoComplete="name"
            {...register("full_name", { required: "Tell us your name" })}
          />
          {formState.errors.full_name && (
            <p className="mt-1.5 text-xs text-red-600">
              {String(formState.errors.full_name.message)}
            </p>
          )}
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="label">Email</label>
            <input
              className="field"
              type="email"
              placeholder="you@example.com"
              autoComplete="email"
              {...register("email", { required: "Enter an email address" })}
            />
          </div>
          <div>
            <label className="label">Phone</label>
            <input
              className="field"
              placeholder="98765 43210"
              autoComplete="tel"
              {...register("phone")}
            />
          </div>
        </div>

        {role === "seller" && (
          <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }}>
            <label className="label">Store name</label>
            <input
              className="field"
              placeholder="Northline Supply"
              {...register("store_name", { required: role === "seller" })}
            />
            <p className="mt-1.5 text-xs text-ink-muted">
              An admin reviews new stores before your listings go live.
            </p>
          </motion.div>
        )}

        <div>
          <label className="label">Password</label>
          <PasswordField
            registration={register("password", {
              required: "Choose a password",
              minLength: { value: 8, message: "Use at least 8 characters" },
            })}
            placeholder="At least 8 characters"
            autoComplete="new-password"
          />
          {formState.errors.password ? (
            <p className="mt-1.5 text-xs text-red-600">
              {String(formState.errors.password.message)}
            </p>
          ) : (
            <p className="mt-1.5 text-xs text-ink-muted">
              At least 8 characters, and not all numbers.
            </p>
          )}
        </div>

        <button className="btn-primary w-full" disabled={formState.isSubmitting}>
          {formState.isSubmitting ? (
            <>
              <span className="spinner" /> Creating account
            </>
          ) : (
            "Create account"
          )}
        </button>

        <p className="text-center text-xs text-ink-muted">
          By continuing you agree to the marketplace seller and buyer terms.
        </p>
      </form>

      <p className="mt-6 text-center text-sm text-ink-muted">
        Already have an account?{" "}
        <Link className="font-medium text-forest-600 hover:underline" to="/login">
          Sign in
        </Link>
      </p>
    </AuthShell>
  );
}