import { createSlice } from "@reduxjs/toolkit";

const stored = localStorage.getItem("ms_theme");
const prefersDark =
  stored === "dark" || (!stored && window.matchMedia("(prefers-color-scheme: dark)").matches);

const uiSlice = createSlice({
  name: "ui",
  initialState: { dark: prefersDark },
  reducers: {
    toggleTheme(state) {
      state.dark = !state.dark;
      localStorage.setItem("ms_theme", state.dark ? "dark" : "light");
      document.documentElement.classList.toggle("dark", state.dark);
    },
    syncTheme(state) {
      document.documentElement.classList.toggle("dark", state.dark);
    },
  },
});

export const { toggleTheme, syncTheme } = uiSlice.actions;
export default uiSlice.reducer;
