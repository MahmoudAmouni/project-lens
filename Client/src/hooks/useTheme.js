// Light or dark: the saved choice first, otherwise the computer's setting. Adds or removes "dark" on <html>.
// index.html sets the same class before React starts, so the page never flashes white in dark mode.

import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "projectlens-theme";
const systemDark = () => window.matchMedia("(prefers-color-scheme: dark)").matches;

function savedTheme() {
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch {
    return null; // private mode or blocked storage: follow the system
  }
}

export function useTheme() {
  const [theme, setTheme] = useState(() => savedTheme() ?? (systemDark() ? "dark" : "light"));

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
  }, [theme]);

  // Follow the computer's setting until the user picks a theme.
  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const follow = (event) => !savedTheme() && setTheme(event.matches ? "dark" : "light");
    media.addEventListener("change", follow);
    return () => media.removeEventListener("change", follow);
  }, []);

  const toggle = useCallback(() => {
    setTheme((current) => {
      const next = current === "dark" ? "light" : "dark";
      try {
        localStorage.setItem(STORAGE_KEY, next);
      } catch {
        // the choice just won't be remembered
      }
      return next;
    });
  }, []);

  return { theme, toggle };
}
