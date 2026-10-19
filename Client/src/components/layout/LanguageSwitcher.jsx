// The EN · ع switch. Changes only the screen text and direction; answers always follow the question's language.
// The switch cross-fades the old screen into the new one (View Transitions API), so the sidebar moving sides
// and the text changing direction feel like one smooth step. Browsers without the API just switch at once.

import { useTranslation } from "react-i18next";

// The next frame, or 50 ms at most: browsers pause frames in hidden tabs, and the transition must not hang.
const nextFrame = () =>
  new Promise((resolve) => {
    requestAnimationFrame(resolve);
    setTimeout(resolve, 50);
  });

export default function LanguageSwitcher() {
  const { t, i18n } = useTranslation();
  const arabic = i18n.resolvedLanguage === "ar";

  function switchLanguage() {
    const next = i18n.resolvedLanguage === "ar" ? "en" : "ar"; // read now: a fast second click must undo the first
    const change = async () => {
      await i18n.changeLanguage(next);
      await nextFrame(); // let React draw the new language before the new screen is captured
    };
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!document.startViewTransition || reduceMotion) {
      change();
      return;
    }
    const transition = document.startViewTransition(change);
    // A fast second click skips the running fade; that is fine, so don't report it as an error.
    transition.ready.catch(() => {});
    transition.finished.catch(() => {});
  }

  return (
    <button
      onClick={switchLanguage}
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
