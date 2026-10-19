// The EN · ع switch. Changes only the screen text and direction; answers always follow the question's language.

import { useTranslation } from "react-i18next";

export default function LanguageSwitcher() {
  const { t, i18n } = useTranslation();
  const arabic = i18n.resolvedLanguage === "ar";

  return (
    <button
      onClick={() => i18n.changeLanguage(arabic ? "en" : "ar")}
      aria-label={t("language.switch")}
      title={t("language.switch")}
      className="flex items-center rounded-button px-2 py-1.5 text-[13px] text-ink-quiet hover:bg-page hover:text-ink"
    >
      <span className={arabic ? "" : "font-semibold text-ink"}>EN</span>
      <span className="px-1" aria-hidden="true">
        ·
      </span>
      <span className={arabic ? "font-semibold text-ink" : ""}>ع</span>
    </button>
  );
}
