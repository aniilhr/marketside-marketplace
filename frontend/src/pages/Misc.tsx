import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { EmptyState, ProductCard, Spinner } from "../components";
import { api } from "../lib/api";
import type { Product } from "../types";

export function Wishlist() {
  const [items, setItems] = useState<{ id: number; product_detail: Product }[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get("/catalog/wishlist/")
      .then((response) => setItems(response.data.results ?? response.data))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Spinner label="Loading your saved items" />;

  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      <h1 className="text-4xl">Saved items</h1>
      {items.length === 0 ? (
        <div className="mt-8">
          <EmptyState
            title="Nothing saved yet"
            body="Tap the heart on any product to keep it here for later."
            action={
              <Link className="btn-primary" to="/products">
                Browse products
              </Link>
            }
          />
        </div>
      ) : (
        <div className="mt-8 grid grid-cols-2 gap-5 md:grid-cols-4">
          {items.map((item) => (
            <ProductCard key={item.id} product={item.product_detail} />
          ))}
        </div>
      )}
    </div>
  );
}

export function NotFound() {
  return (
    <div className="mx-auto max-w-lg px-4 py-28 text-center">
      <p className="font-display text-7xl font-extrabold">404</p>
      <h1 className="mt-4 text-2xl">That page isn't here</h1>
      <p className="mt-2 text-ink-muted">
        The link may be out of date, or the product was removed by its seller.
      </p>
      <Link className="btn-primary mt-6" to="/">
        Back to the store
      </Link>
    </div>
  );
}
