// Sun/moon button in the top bar.

import { Moon, Sun } from "lucide-react";

export default function ThemeToggle({ theme, onToggle }) {
  const dark = theme === "dark";
  const label = dark ? "Switch to light mode" : "Switch to dark mode";
  return (
    <button
      onClick={onToggle}
      aria-label={label}
      title={label}
      className="rounded-button p-1.5 text-ink-quiet hover:bg-page hover:text-ink"
    >
      {dark ? <Sun size={18} /> : <Moon size={18} />}
    </button>
  );
}
