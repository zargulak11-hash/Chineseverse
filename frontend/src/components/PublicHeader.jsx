import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { useAuth } from "../auth.js";
import { useTheme } from "../theme.jsx";
import BrandLogo from "./BrandLogo.jsx";
import Icon from "./Icon.jsx";
import LanguagePicker from "./LanguagePicker.jsx";

// The header of the public pages (Landing, Download): logo, language,
// theme, and sign-in or the way back into the app. Signed-in learners use
// the app shell's own Topbar everywhere else.
export default function PublicHeader() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const { theme, toggleTheme } = useTheme();
  return (
    <div className="appbar-wrap">
      <header className="appbar">
        <Link to="/" className="brand" aria-label={t("nav.toLanding")}
              onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}>
          <BrandLogo className="brand-logo--bar" />
        </Link>
        <span className="spacer" />
        <LanguagePicker />
        <button
          type="button"
          className="theme-toggle"
          onClick={toggleTheme}
          title={theme === "ink" ? t("ui.switchToPaper") : t("ui.switchToInk")}
          aria-label={t("ui.toggleTheme")}
        >
          <Icon name="droplet" size={15} />
        </button>
        {user ? (
          <Link to="/dashboard">
            <button className="btn primary">{t("landing.openDashboard")}</button>
          </Link>
        ) : (
          <>
            <Link to="/login">
              <button className="btn ghost">{t("landing.logIn")}</button>
            </Link>
            {/* On a small phone the hero's own "Create account" is the call
                to action; this one wrapped onto a row of its own. */}
            <Link to="/register" className="appbar-cta">
              <button className="btn primary">{t("landing.startFree")}</button>
            </Link>
          </>
        )}
      </header>
    </div>
  );
}
