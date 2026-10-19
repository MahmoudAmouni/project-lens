// Shown when the Server has no Groq key, so the user knows why questions cannot be answered yet.

import { KeyRound } from "lucide-react";
import { useTranslation } from "react-i18next";

export default function AiKeyBanner() {
  const { t } = useTranslation();
  return (
    <div
      role="alert"
      className="flex items-center gap-2 border-b border-status-warn/30 bg-status-warn/10 px-4 py-2 text-[13px] text-ink"
    >
      <KeyRound size={16} className="shrink-0 text-status-warn" aria-hidden="true" />
      <span>{t("aiKey")}</span>
    </div>
  );
}
