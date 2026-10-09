import { useTranslation } from "react-i18next";
import { SUPPORTED_LANGS } from "../i18n.js";

// The interface language on the pages outside the app shell (landing, sign
// in, sign up). They had no switcher at all: a Russian- or Tajik-speaking
// visitor whose browser is set to English met an English-only site until
// onboarding. A native <select> keeps it one compact control that works with
// a keyboard, a screen reader and touch. Settings and onboarding keep their
// segmented buttons.
export default function LanguagePicker() {
  const { t, i18n } = useTranslation();
  return (
    <select
      className="input lang-select"
      value={i18n.resolvedLanguage || i18n.language}
      onChange={(e) => i18n.changeLanguage(e.target.value)}
      aria-label={t("settings.language")}
    >
      {SUPPORTED_LANGS.map((l) => (
        <option key={l.code} value={l.code} lang={l.code}>
          {l.label}
        </option>
      ))}
    </select>
  );
}
