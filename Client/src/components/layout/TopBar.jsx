// Top of the chat: menu button (small screens), title, model name, language and theme switches, clear chat.

import { Menu, RotateCcw } from "lucide-react";
import { useTranslation } from "react-i18next";
import LanguageSwitcher from "./LanguageSwitcher";
import ThemeToggle from "./ThemeToggle";

export default function TopBar({ model, canClear, onClear, onOpenMenu, theme, onToggleTheme }) {
  const { t } = useTranslation();
  return (
    <header className="flex items-center gap-3 border-b border-line bg-surface px-4 py-3">
      <button
        onClick={onOpenMenu}
        className="rounded-button p-1.5 text-ink-quiet hover:bg-page lg:hidden"
        aria-label={t("topBar.openMenu")}
      >
        <Menu size={20} />
      </button>
      <h1 className="text-base font-semibold text-heading">{t("topBar.title")}</h1>
      <div className="ms-auto flex items-center gap-1.5">
        {model && (
          <span
            dir="ltr"
            className="hidden rounded-full bg-page px-2.5 py-1 text-xs text-ink-quiet sm:inline"
            title={t("topBar.model")}
          >
            {model.replace(/^openai\//, "")}
          </span>
        )}
        <LanguageSwitcher />
        <ThemeToggle theme={theme} onToggle={onToggleTheme} />
        <button
          onClick={onClear}
          disabled={!canClear}
          className="flex items-center gap-1.5 rounded-button px-2.5 py-1.5 text-ink-quiet hover:bg-page hover:text-ink disabled:opacity-40"
          aria-label={t("topBar.clearChat")}
          title={t("topBar.clearChat")}
        >
          <RotateCcw size={16} />
          <span className="hidden sm:inline">{t("topBar.clear")}</span>
        </button>
      </div>
    </header>
  );
}
