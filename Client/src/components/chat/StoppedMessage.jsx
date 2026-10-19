// Shown where an answer would have been, after the user pressed Stop.

import { CircleStop, RefreshCw } from "lucide-react";
import { useTranslation } from "react-i18next";

export default function StoppedMessage({ onAskAgain }) {
  const { t } = useTranslation();
  return (
    <div className="flex animate-fade-in items-center gap-2 px-1 text-[13px] text-ink-quiet">
      <CircleStop size={15} aria-hidden="true" />
      <span>{t("stopped.text")}</span>
      <button
        onClick={onAskAgain}
        className="flex items-center gap-1 font-medium text-brand-teal-dark hover:underline"
      >
        <RefreshCw size={13} aria-hidden="true" /> {t("answer.askAgain")}
      </button>
    </div>
  );
}
