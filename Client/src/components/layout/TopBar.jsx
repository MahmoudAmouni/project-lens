// Top of the chat: menu button (small screens), title, model name, clear chat.

import { Menu, RotateCcw } from "lucide-react";

export default function TopBar({ model, canClear, onClear, onOpenMenu }) {
  return (
    <header className="flex items-center gap-3 border-b border-line bg-surface px-4 py-3">
      <button
        onClick={onOpenMenu}
        className="rounded-button p-1.5 text-ink-quiet hover:bg-page lg:hidden"
        aria-label="Open documents"
      >
        <Menu size={20} />
      </button>
      <h1 className="text-base font-semibold text-brand-navy">Ask your documents</h1>
      <div className="ml-auto flex items-center gap-2">
        {model && (
          <span
            className="hidden rounded-full bg-page px-2.5 py-1 text-xs text-ink-quiet sm:inline"
            title="Main AI model"
          >
            {model.replace(/^openai\//, "")}
          </span>
        )}
        <button
          onClick={onClear}
          disabled={!canClear}
          className="flex items-center gap-1.5 rounded-button px-2.5 py-1.5 text-ink-quiet hover:bg-page hover:text-ink disabled:opacity-40"
          aria-label="Clear chat"
          title="Clear chat"
        >
          <RotateCcw size={16} />
          <span className="hidden sm:inline">Clear</span>
        </button>
      </div>
    </header>
  );
}
