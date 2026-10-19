// i18n setup: English and Arabic screen text. The saved choice first, then the browser's language.
// Changing the language also sets <html lang dir>, so Arabic flips the whole layout right-to-left.

import i18n from "i18next";
import LanguageDetector from "i18next-browser-languagedetector";
import { initReactI18next } from "react-i18next";
import ar from "./locales/ar.json";
import en from "./locales/en.json";

export const STORAGE_KEY = "projectlens-language";

function applyToPage(language) {
  const arabic = language.startsWith("ar");
  document.documentElement.lang = arabic ? "ar" : "en";
  document.documentElement.dir = arabic ? "rtl" : "ltr";
}

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: { en: { translation: en }, ar: { translation: ar } },
    supportedLngs: ["en", "ar"],
    nonExplicitSupportedLngs: true, // "ar-LB" -> "ar"
    fallbackLng: "en",
    interpolation: { escapeValue: false }, // React already escapes
    detection: {
      order: ["localStorage", "navigator"],
      lookupLocalStorage: STORAGE_KEY,
      caches: ["localStorage"],
    },
  });

applyToPage(i18n.resolvedLanguage ?? "en");
i18n.on("languageChanged", applyToPage);

export default i18n;
