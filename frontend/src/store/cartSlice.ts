import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";

import { api } from "../lib/api";
import type { Cart } from "../types";

interface CartState {
  cart: Cart | null;
  loading: boolean;
}

const initialState: CartState = { cart: null, loading: false };

export const fetchCart = createAsyncThunk("cart/fetch", async () => {
  const { data } = await api.get("/cart/");
  return data as Cart;
});

export const addToCart = createAsyncThunk(
  "cart/add",
  async (payload: { product: number; quantity?: number }) => {
    const { data } = await api.post("/cart/items/", { quantity: 1, ...payload });
    return data as Cart;
  },
);

export const updateCartItem = createAsyncThunk(
  "cart/update",
  async (payload: { itemId: number; quantity: number }) => {
    const { data } = await api.patch(`/cart/items/${payload.itemId}/`, {
      quantity: payload.quantity,
    });
    return data as Cart;
  },
);

export const removeCartItem = createAsyncThunk("cart/remove", async (itemId: number) => {
  const { data } = await api.delete(`/cart/items/${itemId}/remove/`);
  return data as Cart;
});

export const applyCoupon = createAsyncThunk("cart/coupon", async (code: string) => {
  const { data } = await api.post("/cart/apply-coupon/", { code });
  return data.cart as Cart;
});

const cartSlice = createSlice({
  name: "cart",
  initialState,
  reducers: {
    clearCart(state) {
      state.cart = null;
    },
  },
  extraReducers: (builder) => {
    [fetchCart, addToCart, updateCartItem, removeCartItem, applyCoupon].forEach((thunk) => {
      builder.addCase(thunk.fulfilled, (state, action) => {
        state.cart = action.payload as Cart;
        state.loading = false;
      });
      builder.addCase(thunk.pending, (state) => {
        state.loading = true;
      });
      builder.addCase(thunk.rejected, (state) => {
        state.loading = false;
      });
    });
  },
});

export const { clearCart } = cartSlice.actions;
export default cartSlice.reducer;
