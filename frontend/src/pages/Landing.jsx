import { Link } from "react-router-dom";
import { useAuth } from "../auth.js";
import AnimalAvatar from "../components/AnimalAvatar.jsx";
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
  ["world", "Chinese World", "Roam the streets, restaurants and train stations of a living city. Talk to NPCs and survive real situations.", "#4FC3F7", "feat-span-4"],
  ["mic", "Voice-first", "Speak out loud. Your companion reacts to your tones, words and pace — no typing required.", "#C58AF2", "feat-span-2"],
  ["dna", "Learning DNA", "Nine live skills build a profile of how you learn, with daily missions that target your weak spots.", "#4CC26B", "feat-span-2"],
  ["search", "Chinese Cases", "Solve detective cases in Chinese: listen to witnesses, spot the contradiction, name the culprit.", "#FF7A45", "feat-span-2"],
  ["swords", "DNA Duels", "Battle friends or the Buddy AI on rapid-fire word challenges.", "#FF8A3D", "feat-span-2"],
  ["paw", "16 Companions", "From Zen capybaras to fierce dragons — each one teaches with a different style and voice.", "#FFC24B", ""],
];

const SHOWCASE = ["fox", "wolf", "snake", "cheetah", "cat", "phoenix", "golden-dragon", "panda"];

export default function Landing() {
  const { user } = useAuth();
  const { theme, toggleTheme } = useTheme();
  return (
    <>
      <div className="appbar-wrap">
        <header className="appbar">
          <span className="brand">
            <span className="logomark">中</span>
            中 ChineseVerse
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
              <button className="btn primary">Open your dashboard</button>
            </Link>
          ) : (
            <>
              <Link to="/login">
                <button className="btn ghost">Log in</button>
              </Link>
              <Link to="/register">
                <button className="btn primary">Start free</button>
              </Link>
            </>
          )}
        </header>
      </div>
      <div className="page">

      <section className="hero">
        <InkBrush variant="hero" />
        <span className="ilb">Learn Chinese by living it</span>
        <h1>中 ChineseVerse</h1>
        <p className="tagline">
          Talk your way through a Chinese city with a companion by your side.
          Every conversation is practice; every practice grows your DNA.
        </p>
        <div className="row center" style={{ justifyContent: "center" }}>
          {user ? (
            <Link to="/dashboard">
              <button className="btn primary" style={{ fontSize: 16, padding: "13px 26px" }}>
                Continue learning →
              </button>
            </Link>
          ) : (
            <Link to="/register">
              <button className="btn primary" style={{ fontSize: 16, padding: "13px 26px" }}>
                Create your account
              </button>
            </Link>
          )}
        </div>
      </section>

      <section className="features">
        {FEATURES.map(([ic, t, d, color, span]) => (
          <div className={`card feat ${span}`} key={t} style={{ "--feat-color": color }}>
            <div className="ic">
              <Icon name={ic} size={19} />
            </div>
            <h3 className="h2" style={{ marginTop: 8 }}>
              {t}
            </h3>
            <p className="sub" style={{ fontSize: 13.5 }}>
              {d}
            </p>
          </div>
        ))}
      </section>

      <section className="center" style={{ marginTop: 56, position: "relative" }}>
        <InkBrush variant="corner" />
        <p className="scrollhint">Sixteen companions, one art style</p>
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
            Meet your companion
          </button>
        </Link>
        <p className="muted" style={{ marginTop: 12, fontSize: 12 }}>
          No affiliation with the official HSK exam — ChineseVerse only estimates
          your preparation readiness.
        </p>
      </section>
      </div>
    </>
  );
}
