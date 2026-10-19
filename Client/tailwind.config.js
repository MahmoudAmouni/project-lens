/** @type {import('tailwindcss').Config} */

// Every color is a theme token: an "R G B" CSS variable set in src/index.css, once for light (:root)
// and once for dark (.dark). Components only use these names, so one class on <html> switches the theme.
const token = (name) => `rgb(var(--${name}) / <alpha-value>)`;

export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          navy: token("brand-navy"),
          "navy-dark": token("brand-navy-dark"),
          "navy-light": token("brand-navy-light"),
          teal: token("brand-teal"),
          "teal-dark": token("brand-teal-dark"),
          "teal-soft": token("brand-teal-soft"),
        },
        page: token("page"),
        surface: token("surface"),
        line: token("line"),
        "row-alt": token("row-alt"),
        heading: token("heading"),
        "on-teal": token("on-teal"),
        ink: {
          DEFAULT: token("ink"),
          quiet: token("ink-quiet"),
        },
        status: {
          ok: token("status-ok"),
          warn: token("status-warn"),
          error: token("status-error"),
          "error-soft": token("status-error-soft"),
        },
      },
      fontFamily: {
        sans: ["Inter", "IBM Plex Sans Arabic", "system-ui", "sans-serif"], // Inter for Latin, Plex for Arabic
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
