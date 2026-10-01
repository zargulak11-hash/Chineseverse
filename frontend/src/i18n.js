import i18n from "i18next";
import LanguageDetector from "i18next-browser-languagedetector";
import { initReactI18next } from "react-i18next";
import en from "./locales/en.json";
import ru from "./locales/ru.json";
import tg from "./locales/tg.json";
import zh from "./locales/zh.json";

// UI chrome only — actual Chinese lesson/vocabulary content is the subject
// being taught and always stays in Chinese regardless of this setting.
// Default is English: the app's existing copy, comments and content are
// already all in English, so English is the more natural fallback than
// assuming a Russian-speaking audience.
export const SUPPORTED_LANGS = [
  { code: "en", label: "English" },
  { code: "ru", label: "Русский" },
  { code: "tg", label: "Тоҷикӣ" },
  { code: "zh", label: "中文" },
];

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      en: { translation: en },
      ru: { translation: ru },
      tg: { translation: tg },
      zh: { translation: zh },
    },
    fallbackLng: "en",
    supportedLngs: ["en", "ru", "tg", "zh"],
    load: "languageOnly",
    interpolation: { escapeValue: false },
    detection: {
      order: ["localStorage", "navigator"],
      caches: ["localStorage"],
      lookupLocalStorage: "chineseverse_ui_lang",
      // Browsers report regional codes ("ru-RU", "zh-CN"). Without this,
      // i18n.language stayed "ru-RU" for anyone who never picked a
      // language in the app: the X-Locale header then wasn't recognized
      // (English content and notification emails) and per-language lookups
      // such as date formats missed. Keep only the language itself.
      convertDetectedLanguage: (lng) => (lng || "").replace("_", "-").split("-")[0].toLowerCase(),
    },
  });

export default i18n;
