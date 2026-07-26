import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";

import { api, tokens } from "../lib/api";
import type { User } from "../types";

interface AuthState {
  user: User | null;
  status: "idle" | "loading" | "ready";
}

const initialState: AuthState = { user: null, status: "idle" };

export const login = createAsyncThunk(
  "auth/login",
  async (payload: { email: string; password: string }) => {
    const { data } = await api.post("/auth/login/", payload);
    tokens.save(data.access, data.refresh);
    return data.user as User;
  },
);

export const register = createAsyncThunk(
  "auth/register",
  async (payload: Record<string, string>) => {
    const { data } = await api.post("/auth/register/", payload);
    return data.user as User;
  },
);

export const loadUser = createAsyncThunk("auth/loadUser", async () => {
  if (!tokens.access) return null;
  const { data } = await api.get("/auth/me/");
  return data as User;
});

const authSlice = createSlice({
  name: "auth",
  initialState,
  reducers: {
    logout(state) {
      tokens.clear();
      state.user = null;
    },
    setUser(state, action) {
      state.user = action.payload;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(login.fulfilled, (state, action) => {
        state.user = action.payload;
        state.status = "ready";
      })
      .addCase(loadUser.pending, (state) => {
        state.status = "loading";
      })
      .addCase(loadUser.fulfilled, (state, action) => {
        state.user = action.payload;
        state.status = "ready";
      })
      .addCase(loadUser.rejected, (state) => {
        state.user = null;
        state.status = "ready";
      });
  },
});

export const { logout, setUser } = authSlice.actions;
export default authSlice.reducer;
