import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { useAuth } from "../auth.js";
import AnimalAvatar from "../components/AnimalAvatar.jsx";
import BrandLogo from "../components/BrandLogo.jsx";
import HeroCarousel from "../components/HeroCarousel.jsx";
import Icon from "../components/Icon.jsx";
import InkBrush from "../components/InkBrush.jsx";
import PublicHeader from "../components/PublicHeader.jsx";

// Each feature gets its own color and its own size — bento-style
// asymmetric rhythm, not a row of identical boxes. Column spans (out of
// 6, at the >=760px breakpoint): World is featured/wide (4) next to
// Voice (2); DNA/Cases/Duels form one even row of three (2 each);
// Companions has no span class, so it defaults to the full 6 — a
// banner leading straight into the animal showcase below it.
// The learning loop leads (the path with one next step, the mistakes that
// come back, real books), then the city, voice and companions that make it
// ChineseVerse. Detective cases and duels are still in the app; they were
// pitched here as if they were the product.
const FEATURES = [
  ["route", "featPathTitle", "featPathDesc", "#E9B44C", "feat-span-4"],
  ["crosshair", "featNotebookTitle", "featNotebookDesc", "#FF7A45", "feat-span-2"],
  ["bookOpen", "featStoriesTitle", "featStoriesDesc", "#4CC26B", "feat-span-2"],
  ["world", "featWorldTitle", "featWorldDesc", "#4FC3F7", "feat-span-2"],
  ["mic", "featVoiceTitle", "featVoiceDesc", "#C58AF2", "feat-span-2"],
  ["paw", "featCompanionsTitle", "featCompanionsDesc", "#FFC24B", ""],
];

const SHOWCASE = ["fox", "wolf", "snake", "monkey", "cat", "phoenix", "owl", "panda"];

export default function Landing() {
  const { t } = useTranslation();
  const { user } = useAuth();
  return (
    <>
      <PublicHeader />
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
          <Link to="/download" className="btn ghost landing-app-btn">
            <Icon name="phone" size={17} /> {t("download.cta")}
          </Link>
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

      {/* The Android app, one tap from the bottom of the page too: the hero
          button scrolls out of view long before a visitor decides. */}
      <section className="card landing-app">
        <div className="landing-app-ic" aria-hidden="true">
          <Icon name="phone" size={26} />
        </div>
        <div className="landing-app-text">
          <h2 className="h2">{t("download.promoTitle")}</h2>
          <p className="sub">{t("download.promoText")}</p>
        </div>
        <Link to="/download" className="btn primary">
          <Icon name="download" size={16} /> {t("download.cta")}
        </Link>
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
