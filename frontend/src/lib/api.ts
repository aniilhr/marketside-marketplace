import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "/api",
  headers: { "Content-Type": "application/json" },
});

const ACCESS = "ms_access";
const REFRESH = "ms_refresh";

export const tokens = {
  get access() {
    return localStorage.getItem(ACCESS);
  },
  get refresh() {
    return localStorage.getItem(REFRESH);
  },
  save(access: string, refresh?: string) {
    localStorage.setItem(ACCESS, access);
    if (refresh) localStorage.setItem(REFRESH, refresh);
  },
  clear() {
    localStorage.removeItem(ACCESS);
    localStorage.removeItem(REFRESH);
  },
};

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = tokens.access;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

let refreshing: Promise<string> | null = null;

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as InternalAxiosRequestConfig & { _retried?: boolean };
    const isAuthCall = original?.url?.includes("/auth/login") || original?.url?.includes("/auth/refresh");

    if (error.response?.status === 401 && !original._retried && tokens.refresh && !isAuthCall) {
      original._retried = true;
      try {
        refreshing =
          refreshing ||
          axios
            .post(`${api.defaults.baseURL}/auth/refresh/`, { refresh: tokens.refresh })
            .then((response) => {
              tokens.save(response.data.access, response.data.refresh);
              return response.data.access as string;
            })
            .finally(() => {
              refreshing = null;
            });
        const access = await refreshing;
        original.headers.Authorization = `Bearer ${access}`;
        return api(original);
      } catch {
        tokens.clear();
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  },
);

export function apiError(error: unknown, fallback = "Something went wrong. Try again.") {
  const err = error as AxiosError<Record<string, unknown>>;
  const data = err.response?.data;
  if (!data) return fallback;
  if (typeof data.detail === "string") return data.detail;
  const first = Object.entries(data)[0];
  if (!first) return fallback;
  const [field, value] = first;
  const message = Array.isArray(value) ? value[0] : value;
  return `${field}: ${message}`;
}

export const money = (value: string | number) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 })
    .format(Number(value));
