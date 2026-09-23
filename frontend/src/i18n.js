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
    },
  });

export default i18n;
