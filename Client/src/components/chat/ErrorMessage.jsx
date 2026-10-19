// A red inline card with the plain error and a Try again button. Never a blank screen.

import { AlertCircle, RefreshCw } from "lucide-react";
import { useTranslation } from "react-i18next";
import { errorText } from "../../utils/errorText";

export default function ErrorMessage({ error, onRetry }) {
  const { t } = useTranslation();
  return (
    <div
      className="flex animate-fade-in items-start gap-3 rounded-card border border-status-error/30 bg-status-error-soft px-4 py-3"
      role="alert"
    >
      <AlertCircle size={18} className="mt-0.5 shrink-0 text-status-error" aria-hidden="true" />
      <p className="flex-1 leading-relaxed text-ink">{errorText(t, error)}</p>
      <button
        onClick={onRetry}
        className="flex shrink-0 items-center gap-1.5 rounded-button border border-status-error/30 bg-surface px-3 py-1.5 text-status-error hover:bg-status-error-soft"
      >
        <RefreshCw size={14} aria-hidden="true" /> {t("error.tryAgain")}
      </button>
    </div>
  );
}
