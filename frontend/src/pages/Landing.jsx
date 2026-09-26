import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { useAuth } from "../auth.js";
import AnimalAvatar from "../components/AnimalAvatar.jsx";
import BrandLogo from "../components/BrandLogo.jsx";
import HeroCarousel from "../components/HeroCarousel.jsx";
import Icon from "../components/Icon.jsx";
import InkBrush from "../components/InkBrush.jsx";
import { useTheme } from "../theme.jsx";

// Each feature gets its own color and its own size — bento-style
// asymmetric rhythm, not a row of identical boxes. Column spans (out of
// 6, at the >=760px breakpoint): World is featured/wide (4) next to
// Voice (2); DNA/Cases/Duels form one even row of three (2 each);
// Companions has no span class, so it defaults to the full 6 — a
// banner leading straight into the animal showcase below it.
const FEATURES = [
  ["world", "featWorldTitle", "featWorldDesc", "#4FC3F7", "feat-span-4"],
  ["mic", "featVoiceTitle", "featVoiceDesc", "#C58AF2", "feat-span-2"],
  ["dna", "featDnaTitle", "featDnaDesc", "#4CC26B", "feat-span-2"],
  ["search", "featCasesTitle", "featCasesDesc", "#FF7A45", "feat-span-2"],
  ["swords", "featDuelsTitle", "featDuelsDesc", "#FF8A3D", "feat-span-2"],
  ["paw", "featCompanionsTitle", "featCompanionsDesc", "#FFC24B", ""],
];

const SHOWCASE = ["fox", "wolf", "snake", "monkey", "cat", "phoenix", "owl", "panda"];

export default function Landing() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const { theme, toggleTheme } = useTheme();
  return (
    <>
      <div className="appbar-wrap">
        <header className="appbar">
          <span className="brand">
            <BrandLogo className="brand-logo--bar" />
          </span>
          <span className="spacer" />
          <button
            type="button"
            className="theme-toggle"
            onClick={toggleTheme}
            title={theme === "ink" ? "Switch to Rice Paper" : "Switch to Ink"}
            aria-label="Toggle light/dark theme"
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
              <Link to="/register">
                <button className="btn primary">{t("landing.startFree")}</button>
              </Link>
            </>
          )}
        </header>
      </div>
      <div className="page">

      <section className="hero">
        <HeroCarousel />
        <InkBrush variant="hero" />
        <span className="ilb">{t("landing.kicker")}</span>
        <h1 className="hero-brand">
          <BrandLogo className="brand-logo--hero" />
        </h1>
        <p className="tagline">{t("landing.tagline")}</p>
        <div className="row center" style={{ justifyContent: "center" }}>
          {user ? (
            <Link to="/dashboard">
              <button className="btn primary" style={{ fontSize: 16, padding: "13px 26px" }}>
                {t("landing.continueLearning")}
              </button>
            </Link>
          ) : (
            <Link to="/register">
              <button className="btn primary" style={{ fontSize: 16, padding: "13px 26px" }}>
                {t("landing.createAccount")}
              </button>
            </Link>
          )}
        </div>
      </section>

      <section className="features">
        {FEATURES.map(([ic, titleKey, descKey, color, span]) => (
          <div className={`card feat ${span}`} key={titleKey} style={{ "--feat-color": color }}>
            <div className="ic">
              <Icon name={ic} size={19} />
            </div>
            <h3 className="h2" style={{ marginTop: 8 }}>
              {t(`landing.${titleKey}`)}
            </h3>
            <p className="sub" style={{ fontSize: 13.5 }}>
              {t(`landing.${descKey}`)}
            </p>
          </div>
        ))}
      </section>

      <section className="center" style={{ marginTop: 56, position: "relative" }}>
        <InkBrush variant="corner" />
        <p className="scrollhint">{t("landing.showcase")}</p>
        <div className="row center" style={{ justifyContent: "center", marginTop: 16, gap: 18 }}>
          {SHOWCASE.map((slug) => (
            <div key={slug} className="col" style={{ alignItems: "center", gap: 6 }}>
              <AnimalAvatar slug={slug} size={54} />
            </div>
          ))}
        </div>
      </section>

      <section className="center" style={{ marginTop: 46 }}>
        <Link to="/register">
          <button className="btn primary" style={{ padding: "13px 28px", fontSize: 15 }}>
            {t("landing.meetCompanion")}
          </button>
        </Link>
        <p className="muted" style={{ marginTop: 12, fontSize: 12 }}>
          {t("landing.hskDisclaimer")}
        </p>
      </section>
      </div>
    </>
  );
}
