import { useEffect } from "react";
import { Toaster } from "react-hot-toast";
import { Route, Routes } from "react-router-dom";

import { Layout, RequireAuth } from "./components";
import { CartPage, Checkout, OrderDetail, Orders, Profile } from "./pages/Account";
import { Login, Register } from "./pages/Auth";
import {
  AdminDashboard,
  DeliveryDashboard,
  InventoryDashboard,
  SellerDashboard,
} from "./pages/Dashboards";
import { NotFound, Wishlist } from "./pages/Misc";
import { Home, ProductDetail, Products } from "./pages/Storefront";
import { useAppDispatch } from "./store";
import { loadUser } from "./store/authSlice";
import { syncTheme } from "./store/uiSlice";

export default function App() {
  const dispatch = useAppDispatch();

  useEffect(() => {
    dispatch(syncTheme());
    dispatch(loadUser());
  }, [dispatch]);

  return (
    <>
      <Toaster position="top-right" toastOptions={{ duration: 3000 }} />
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Home />} />
          <Route path="products" element={<Products />} />
          <Route path="product/:slug" element={<ProductDetail />} />
          <Route path="login" element={<Login />} />
          <Route path="register" element={<Register />} />

          <Route element={<RequireAuth />}>
            <Route path="cart" element={<CartPage />} />
            <Route path="checkout" element={<Checkout />} />
            <Route path="orders" element={<Orders />} />
            <Route path="orders/:orderNumber" element={<OrderDetail />} />
            <Route path="wishlist" element={<Wishlist />} />
            <Route path="profile" element={<Profile />} />
          </Route>

          <Route element={<RequireAuth roles={["seller"]} />}>
            <Route path="seller" element={<SellerDashboard />} />
          </Route>
          <Route element={<RequireAuth roles={["admin"]} />}>
            <Route path="admin" element={<AdminDashboard />} />
          </Route>
          <Route element={<RequireAuth roles={["inventory", "admin"]} />}>
            <Route path="inventory" element={<InventoryDashboard />} />
          </Route>
          <Route element={<RequireAuth roles={["delivery"]} />}>
            <Route path="delivery" element={<DeliveryDashboard />} />
          </Route>

          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </>
  );
}