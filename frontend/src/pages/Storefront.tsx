import { useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";

import { EmptyState, ProductCard, SkeletonGrid, Spinner, StatusChip } from "../components";
import { api, apiError, money } from "../lib/api";
import { useAppDispatch, useAppSelector } from "../store";
import { addToCart } from "../store/cartSlice";
import type { Category, Paginated, Product } from "../types";

/* ------------------------------------------------------------------ home */

export function Home() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [featured, setFeatured] = useState<Product[]>([]);
  const [trending, setTrending] = useState<Product[]>([]);
  const [coupons, setCoupons] = useState<{ code: string; description: string }[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.get("/catalog/categories/"),
      api.get("/catalog/products/featured/"),
      api.get("/catalog/products/trending/"),
      api.get("/public-coupons/"),
    ])
      .then(([categoryRes, featuredRes, trendingRes, couponRes]) => {
        setCategories(categoryRes.data.results ?? categoryRes.data);
        setFeatured(featuredRes.data);
        setTrending(trendingRes.data);
        setCoupons(couponRes.data);
      })
      .catch(() => toast.error("Couldn't reach the store. Is the API running?"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <section className="border-b border-black/5 bg-paper-raised dark:border-night-line dark:bg-night-raised">
        <div className="mx-auto grid max-w-7xl gap-10 px-4 py-16 lg:grid-cols-[1.1fr_0.9fr] lg:py-24">
          <div>
            <p className="label">Marketplace · {categories.length} departments</p>
            <h1 className="mt-3 text-5xl font-extrabold leading-[0.95] sm:text-6xl">
              Every shop on
              <br />
              one checkout.
            </h1>
            <p className="mt-5 max-w-md text-lg text-ink-muted">
              Independent sellers and established brands, one cart, one delivery promise. Sellers
              keep their storefront; you keep a single order history.
            </p>
            <div className="mt-7 flex flex-wrap gap-3">
              <Link to="/products" className="btn-primary">
                Start browsing
              </Link>
              <Link to="/register" className="btn-ghost">
                Open a seller account
              </Link>
            </div>
            {coupons.length > 0 && (
              <div className="mt-8 flex flex-wrap gap-2">
                {coupons.map((coupon) => (
                  <span key={coupon.code} className="chip border border-dashed border-forest-500 text-forest-600">
                    {coupon.code} — {coupon.description}
                  </span>
                ))}
              </div>
            )}
          </div>

          <div className="grid grid-cols-2 gap-3 self-center">
            {categories.slice(0, 4).map((category, index) => (
              <Link
                key={category.id}
                to={`/products?category=${category.slug}`}
                className={`card flex flex-col justify-between p-5 transition hover:-translate-y-1 ${
                  index === 0 ? "col-span-2" : ""
                }`}
              >
                <span className="font-display text-2xl">{category.name}</span>
                <span className="mt-6 text-sm text-ink-muted">
                  {category.product_count} listings
                </span>
              </Link>
            ))}
          </div>
        </div>
      </section>

      <Section title="Featured this week" link="/products?is_featured=true">
        {loading ? <SkeletonGrid count={4} /> : <Grid products={featured.slice(0, 8)} />}
      </Section>

      <Section title="Selling fast" link="/products?ordering=-sold_count">
        {loading ? <SkeletonGrid count={4} /> : <Grid products={trending.slice(0, 8)} />}
      </Section>
    </div>
  );
}

function Section({
  title,
  link,
  children,
}: {
  title: string;
  link: string;
  children: React.ReactNode;
}) {
  return (
    <section className="mx-auto max-w-7xl px-4 py-12">
      <div className="mb-6 flex items-end justify-between">
        <h2 className="text-3xl">{title}</h2>
        <Link to={link} className="text-sm font-medium text-forest-600 hover:underline">
          See all
        </Link>
      </div>
      {children}
    </section>
  );
}

function Grid({ products }: { products: Product[] }) {
  if (!products.length) {
    return <p className="text-sm text-ink-muted">Nothing here yet. Run the seed command to load demo data.</p>;
  }
  return (
    <div className="grid grid-cols-2 gap-5 md:grid-cols-3 lg:grid-cols-4">
      {products.map((product) => (
        <ProductCard key={product.id} product={product} />
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ listing */

export function Products() {
  const [params, setParams] = useSearchParams();
  const [data, setData] = useState<Paginated<Product> | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);

  const filters = useMemo(() => Object.fromEntries(params.entries()), [params]);

  useEffect(() => {
    api.get("/catalog/categories/").then((response) =>
      setCategories(response.data.results ?? response.data),
    );
  }, []);

  useEffect(() => {
    setLoading(true);
    api
      .get("/catalog/products/", { params: filters })
      .then((response) => setData(response.data))
      .catch((error) => toast.error(apiError(error)))
      .finally(() => setLoading(false));
  }, [filters]);

  const update = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    next.delete("page");
    setParams(next);
  };

  return (
    <div className="mx-auto max-w-7xl px-4 py-10">
      <h1 className="text-4xl">Browse</h1>
      <p className="mt-2 text-sm text-ink-muted">
        {data ? `${data.count} products` : "Loading products"}
        {filters.search ? ` matching “${filters.search}”` : ""}
      </p>

      <div className="mt-8 grid gap-8 lg:grid-cols-[240px_1fr]">
        <aside className="space-y-6">
          <div>
            <p className="label">Department</p>
            <select
              className="field"
              value={filters.category || ""}
              onChange={(event) => update("category", event.target.value)}
            >
              <option value="">All departments</option>
              {categories.map((category) => (
                <option key={category.id} value={category.slug}>
                  {category.name}
                </option>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <p className="label">Min price</p>
              <input
                className="field"
                type="number"
                defaultValue={filters.min_price || ""}
                onBlur={(event) => update("min_price", event.target.value)}
              />
            </div>
            <div>
              <p className="label">Max price</p>
              <input
                className="field"
                type="number"
                defaultValue={filters.max_price || ""}
                onBlur={(event) => update("max_price", event.target.value)}
              />
            </div>
          </div>
          <div>
            <p className="label">Minimum rating</p>
            <select
              className="field"
              value={filters.min_rating || ""}
              onChange={(event) => update("min_rating", event.target.value)}
            >
              <option value="">Any rating</option>
              <option value="4">4 and up</option>
              <option value="3">3 and up</option>
            </select>
          </div>
          <div>
            <p className="label">Sort by</p>
            <select
              className="field"
              value={filters.ordering || "-created_at"}
              onChange={(event) => update("ordering", event.target.value)}
            >
              <option value="-created_at">Newest</option>
              <option value="price">Price: low to high</option>
              <option value="-price">Price: high to low</option>
              <option value="-rating">Best rated</option>
              <option value="-sold_count">Best selling</option>
            </select>
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={filters.in_stock === "true"}
              onChange={(event) => update("in_stock", event.target.checked ? "true" : "")}
            />
            In stock only
          </label>
          <button className="btn-ghost w-full" onClick={() => setParams(new URLSearchParams())}>
            Clear filters
          </button>
        </aside>

        <div>
          {loading ? (
            <SkeletonGrid />
          ) : data && data.results.length ? (
            <>
              <div className="grid grid-cols-2 gap-5 md:grid-cols-3 xl:grid-cols-4">
                {data.results.map((product) => (
                  <ProductCard key={product.id} product={product} />
                ))}
              </div>
              <div className="mt-10 flex items-center justify-center gap-3">
                <button
                  className="btn-ghost"
                  disabled={!data.previous}
                  onClick={() => update("page", String(Number(filters.page || 1) - 1))}
                >
                  Previous
                </button>
                <span className="text-sm text-ink-muted">Page {filters.page || 1}</span>
                <button
                  className="btn-ghost"
                  disabled={!data.next}
                  onClick={() => update("page", String(Number(filters.page || 1) + 1))}
                >
                  Next
                </button>
              </div>
            </>
          ) : (
            <EmptyState
              title="No products match those filters"
              body="Try widening the price range or clearing the department filter."
              action={
                <button className="btn-primary" onClick={() => setParams(new URLSearchParams())}>
                  Clear filters
                </button>
              }
            />
          )}
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ detail */

export function ProductDetail() {
  const { slug } = useParams();
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const user = useAppSelector((state) => state.auth.user);
  const [product, setProduct] = useState<Product | null>(null);
  const [related, setRelated] = useState<Product[]>([]);
  const [quantity, setQuantity] = useState(1);
  const [active, setActive] = useState(0);
  const [rating, setRating] = useState(5);
  const [comment, setComment] = useState("");

  const load = () => {
    api.get(`/catalog/products/${slug}/`).then((response) => setProduct(response.data));
    api.get(`/catalog/products/${slug}/related/`).then((response) => setRelated(response.data));
  };

  useEffect(load, [slug]);

  if (!product) return <Spinner label="Loading product" />;

  const gallery = [product.thumbnail, ...(product.images || []).map((i) => i.url)].filter(Boolean);

  const add = async () => {
    if (!user) return navigate("/login");
    try {
      await dispatch(addToCart({ product: product.id, quantity })).unwrap();
      toast.success("Added to cart");
    } catch (error) {
      toast.error(apiError(error));
    }
  };

  const submitReview = async (event: React.FormEvent) => {
    event.preventDefault();
    try {
      await api.post("/catalog/reviews/", { product: product.id, rating, comment });
      toast.success("Review published");
      setComment("");
      load();
    } catch (error) {
      toast.error(apiError(error, "You may have already reviewed this product."));
    }
  };

  return (
    <div className="mx-auto max-w-7xl px-4 py-10">
      <div className="grid gap-10 lg:grid-cols-2">
        <div>
          <img
            src={gallery[active] || "https://placehold.co/800x800/F1EFE9/6A7482?text=No+image"}
            alt={product.name}
            className="card aspect-square w-full object-cover"
          />
          <div className="mt-3 flex gap-3">
            {gallery.slice(0, 5).map((url, index) => (
              <button
                key={index}
                onClick={() => setActive(index)}
                className={`h-16 w-16 overflow-hidden rounded-lg border-2 ${
                  active === index ? "border-forest-500" : "border-transparent"
                }`}
              >
                <img src={url} alt="" className="h-full w-full object-cover" />
              </button>
            ))}
          </div>
        </div>

        <div>
          <p className="label">
            {product.store_name} · {product.category_name}
          </p>
          <h1 className="mt-2 text-4xl">{product.name}</h1>
          <p className="mt-3 text-ink-muted">{product.short_description}</p>

          <div className="mt-6 flex items-baseline gap-3">
            <span className="font-display text-4xl">{money(product.price)}</span>
            {product.compare_at_price && (
              <>
                <span className="text-lg text-ink-muted line-through">
                  {money(product.compare_at_price)}
                </span>
                <span className="chip bg-amber-400 text-ink">{product.discount_percent}% off</span>
              </>
            )}
          </div>

          <p className="mt-2 text-sm">
            {product.in_stock ? (
              <span className="text-forest-600">In stock — {product.stock} available</span>
            ) : (
              <span className="text-red-600">Out of stock</span>
            )}
          </p>

          <div className="mt-6 flex gap-3">
            <input
              type="number"
              min={1}
              max={product.stock}
              value={quantity}
              onChange={(event) => setQuantity(Number(event.target.value))}
              className="field w-24"
              aria-label="Quantity"
            />
            <button className="btn-primary flex-1" onClick={add} disabled={!product.in_stock}>
              Add to cart
            </button>
          </div>

          <div className="card mt-8 p-5">
            <h2 className="text-lg">About this product</h2>
            <p className="mt-2 whitespace-pre-line text-sm text-ink-muted">{product.description}</p>
            <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
              <div>
                <dt className="label">SKU</dt>
                <dd>{product.sku}</dd>
              </div>
              <div>
                <dt className="label">Brand</dt>
                <dd>{product.brand_name || "Unbranded"}</dd>
              </div>
            </dl>
          </div>
        </div>
      </div>

      <section className="mt-14">
        <h2 className="text-2xl">Reviews ({product.review_count})</h2>
        <div className="mt-5 grid gap-6 lg:grid-cols-[1fr_360px]">
          <div className="space-y-4">
            {(product.reviews || []).length === 0 && (
              <p className="text-sm text-ink-muted">No reviews yet. Be the first.</p>
            )}
            {(product.reviews || []).map((review) => (
              <div key={review.id} className="card p-5">
                <div className="flex items-center gap-3">
                  <span className="font-medium">{review.author || "Verified buyer"}</span>
                  <span className="chip bg-paper-sunk text-ink-soft">{review.rating} / 5</span>
                  {review.is_verified_purchase && <StatusChip status="approved" />}
                </div>
                <p className="mt-2 text-sm text-ink-muted">{review.comment}</p>
              </div>
            ))}
          </div>

          {user && (
            <form onSubmit={submitReview} className="card h-fit p-5">
              <h3 className="text-lg">Write a review</h3>
              <label className="label mt-4">Rating</label>
              <select
                className="field"
                value={rating}
                onChange={(event) => setRating(Number(event.target.value))}
              >
                {[5, 4, 3, 2, 1].map((value) => (
                  <option key={value} value={value}>
                    {value} star{value > 1 ? "s" : ""}
                  </option>
                ))}
              </select>
              <label className="label mt-4">What stood out?</label>
              <textarea
                className="field h-28"
                value={comment}
                onChange={(event) => setComment(event.target.value)}
                required
              />
              <button className="btn-primary mt-4 w-full">Publish review</button>
            </form>
          )}
        </div>
      </section>

      {related.length > 0 && (
        <section className="mt-14">
          <h2 className="text-2xl">Similar products</h2>
          <div className="mt-5 grid grid-cols-2 gap-5 md:grid-cols-4">
            {related.slice(0, 4).map((item) => (
              <ProductCard key={item.id} product={item} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
