/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          navy: "#1B3A5C",
          "navy-dark": "#142D48",
          "navy-light": "#24496F",
          teal: "#14A89A",
          "teal-dark": "#0E8075",
          "teal-soft": "#E7F6F4",
        },
        page: "#F7F9FB",
        surface: "#FFFFFF",
        line: "#E3E8EE",
        ink: {
          DEFAULT: "#0F1B2A",
          quiet: "#5B6B7D",
        },
        status: {
          ok: "#16A34A",
          warn: "#D97706",
          error: "#DC2626",
          "error-soft": "#FEF2F2",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      borderRadius: {
        card: "12px",
        button: "8px",
      },
      keyframes: {
        "fade-in": {
          from: { opacity: "0", transform: "translateY(4px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "dot-pulse": {
          "0%, 80%, 100%": { opacity: "0.25" },
          "40%": { opacity: "1" },
        },
      },
      animation: {
        "fade-in": "fade-in 0.25s ease-out",
        "dot-pulse": "dot-pulse 1.2s infinite ease-in-out",
      },
    },
  },
  plugins: [],
};
