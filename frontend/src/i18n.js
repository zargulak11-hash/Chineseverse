import i18n from "i18next";
import LanguageDetector from "i18next-browser-languagedetector";
import { initReactI18next } from "react-i18next";
import en from "./locales/en.json";

// Only English -- the fallback every other language leans on -- ships in the
// entry bundle. Russian, Tajik and Chinese are fetched when chosen (about
// 570 KB a learner never used to need loaded up front: all four sat in the
// first download). i18next waits for this backend before it switches, so
// changeLanguage() never flashes English; if the fetch fails (offline), the
// UI stays readable in the English fallback.
const LAZY = {
  ru: () => import("./locales/ru.json"),
  tg: () => import("./locales/tg.json"),
  zh: () => import("./locales/zh.json"),
};
const lazyLocales = {
  type: "backend",
  read(language, namespace, callback) {
    const load = LAZY[language];
    if (!load) return callback(null, {});
    load().then((m) => callback(null, m.default), (err) => callback(err, null));
  },
};

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

// main.jsx renders once this resolves: the first paint is already in the
// learner's language.
export const i18nReady = i18n
  .use(lazyLocales)
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      en: { translation: en },
    },
    partialBundledLanguages: true,
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
