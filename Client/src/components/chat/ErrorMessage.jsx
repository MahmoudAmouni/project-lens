// A red inline card with the plain error and a Try again button. Never a blank screen.

import { AlertCircle, RefreshCw } from "lucide-react";

export default function ErrorMessage({ text, onRetry }) {
  return (
    <div
      className="flex animate-fade-in items-start gap-3 rounded-card border border-status-error/30 bg-status-error-soft px-4 py-3"
      role="alert"
    >
      <AlertCircle size={18} className="mt-0.5 shrink-0 text-status-error" aria-hidden="true" />
      <p className="flex-1 leading-relaxed text-ink">{text}</p>
      <button
        onClick={onRetry}
        className="flex shrink-0 items-center gap-1.5 rounded-button border border-status-error/30 bg-surface px-3 py-1.5 text-status-error hover:bg-status-error-soft"
      >
        <RefreshCw size={14} aria-hidden="true" /> Try again
      </button>
    </div>
  );
}
