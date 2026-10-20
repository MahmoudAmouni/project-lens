// A red inline card with the plain error and a Try again button. Never a blank screen.

import { AlertCircle, RefreshCw } from "lucide-react";
import { useTranslation } from "react-i18next";
import { errorDetail, errorText } from "../../utils/errorText";

export default function ErrorMessage({ error, onRetry }) {
  const { t } = useTranslation();
  const detail = errorDetail(error);
  return (
    <div
      className="flex animate-fade-in items-start gap-3 rounded-card border border-status-error/30 bg-status-error-soft px-4 py-3"
      role="alert"
    >
      <AlertCircle size={18} className="mt-0.5 shrink-0 text-status-error" aria-hidden="true" />
      <div className="min-w-0 flex-1">
        <p className="leading-relaxed text-ink">{errorText(t, error)}</p>
        {detail && (
          <p dir="ltr" className="mt-1 text-start text-sm text-ink-quiet">
            {detail}
          </p>
        )}
      </div>
      <button
        onClick={onRetry}
        className="flex shrink-0 items-center gap-1.5 rounded-button border border-status-error/30 bg-surface px-3 py-1.5 text-status-error hover:bg-status-error-soft"
      >
        <RefreshCw size={14} aria-hidden="true" /> {t("error.tryAgain")}
      </button>
    </div>
  );
}
