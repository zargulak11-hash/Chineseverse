import { useTranslation } from "react-i18next";
import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../auth.js";
import { isNativeApp } from "../platform.js";
import { useTheme } from "../theme.jsx";
import BrandLogo from "./BrandLogo.jsx";
import Icon from "./Icon.jsx";
import LanguagePicker from "./LanguagePicker.jsx";

// The header of the public pages (Landing, Download): logo, the Android
// app, language, theme, and sign-in or the way back into the app. Signed-in
// learners use the app shell's own Topbar everywhere else.
//
// The app link used to exist only as buttons inside the landing page, so a
// visitor had to scroll to find it; it is now in the bar on every public
// page (icon-only on a small phone, see .appbar-app). Not inside the app
// itself, which is already what that link downloads.
export default function PublicHeader() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const { pathname } = useLocation();
  return (
    <div className="appbar-wrap">
      <header className="appbar">
        <Link to="/" className="brand" aria-label={t("nav.toLanding")}
              onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}>
          <BrandLogo className="brand-logo--bar" />
          <BrandLogo variant="mark" className="brand-logo--bar-mark" />
        </Link>
        <span className="spacer" />
        {!isNativeApp && (
          <Link
            to="/download"
            className="btn ghost appbar-app"
            aria-label={t("download.cta")}
            aria-current={pathname === "/download" ? "page" : undefined}
          >
            <Icon name="phone" size={16} />
            <span className="appbar-app-label">{t("download.cta")}</span>
          </Link>
        )}
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
