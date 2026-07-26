export type Role = "customer" | "seller" | "admin" | "inventory" | "delivery";

export interface User {
  id: number;
  email: string;
  full_name: string;
  phone: string;
  role: Role;
  is_verified: boolean;
  wallet_balance: string;
  loyalty_points: number;
  referral_code: string;
  store_name?: string;
  is_approved_seller?: boolean;
}

export interface Product {
  id: number;
  name: string;
  slug: string;
  sku: string;
  price: string;
  compare_at_price: string | null;
  discount_percent: number;
  thumbnail: string;
  rating: string;
  review_count: number;
  stock: number;
  in_stock: boolean;
  is_featured: boolean;
  category_name: string;
  brand_name: string;
  store_name: string;
  sold_count: number;
  status: string;
  short_description?: string;
  description?: string;
  images?: { id: number; url: string; image: string | null }[];
  reviews?: Review[];
  category?: number;
}

export interface Review {
  id: number;
  author: string;
  rating: number;
  title: string;
  comment: string;
  is_verified_purchase: boolean;
  created_at: string;
}

export interface Category {
  id: number;
  name: string;
  slug: string;
  icon: string;
  product_count: number;
  children: Category[];
}

export interface CartItem {
  id: number;
  product: number;
  product_detail: Product;
  quantity: number;
  subtotal: string;
}

export interface Cart {
  id: number;
  items: CartItem[];
  subtotal: string;
  coupon_code: string;
  item_count: number;
}

export interface Address {
  id: number;
  label: string;
  full_name: string;
  phone: string;
  line1: string;
  line2: string;
  city: string;
  state: string;
  postal_code: string;
  country: string;
  is_default: boolean;
}

export interface OrderItem {
  id: number;
  product_name: string;
  product_slug: string;
  thumbnail: string;
  unit_price: string;
  quantity: number;
  subtotal: string;
  store_name: string;
}

export interface Order {
  id: number;
  order_number: string;
  customer_email: string;
  status: string;
  payment_method: string;
  payment_status: string;
  subtotal: string;
  discount: string;
  tax: string;
  shipping_fee: string;
  total: string;
  shipping_address: Record<string, string>;
  items: OrderItem[];
  events: { id: number; status: string; note: string; created_at: string }[];
  created_at: string;
}

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
