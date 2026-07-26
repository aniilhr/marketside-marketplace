/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: { DEFAULT: "#14171C", soft: "#2C333D", muted: "#6A7482" },
        paper: { DEFAULT: "#FAF9F6", raised: "#FFFFFF", sunk: "#F1EFE9" },
        forest: { 50: "#EAF3ED", 100: "#CFE3D6", 500: "#1F6B47", 600: "#17563A", 700: "#0F3D29" },
        amber: { 100: "#FDECC8", 400: "#F0A81C", 500: "#D8900A" },
        night: { DEFAULT: "#0E1116", raised: "#171B22", line: "#242A33" },
      },
      fontFamily: {
        display: ['"Bricolage Grotesque"', "system-ui", "sans-serif"],
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "monospace"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(20,23,28,0.04), 0 8px 24px -12px rgba(20,23,28,0.18)",
      },
      borderRadius: { xl2: "1.25rem" },
    },
  },
  plugins: [],
};
