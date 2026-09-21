import { Link } from "react-router-dom";
import { useAuth } from "../auth.js";

const FEATURES = [
  ["🗺️", "Chinese World", "Roam the streets, restaurants and train stations of a living city. Talk to NPCs and survive real situations."],
  ["🎙️", "Voice-first", "Speak out loud. Your companion reacts to your tones, words and pace — no typing required."],
  ["🧬", "Learning DNA", "Nine live skills build a profile of how you learn, with daily missions that target your weak spots."],
  ["🕵️", "Chinese Cases", "Solve detective cases in Chinese: listen to witnesses, spot the contradiction, name the culprit."],
  ["⚔️", "DNA Duels", "Battle friends or the Buddy AI on rapid-fire word challenges."],
  ["🐼", "16 Companions", "From Zen capybaras to fierce dragons — each one teaches with a different style and voice."],
];

export default function Landing() {
  const { user } = useAuth();
  return (
    <div className="page">
      <header className="appbar" style={{ position: "static" }}>
        <span className="brand">
          <span className="logomark">🐉</span> LinguaVerse
        </span>
        <span className="spacer" />
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

      <section className="hero">
        <span className="ilb">Learn Chinese by living it</span>
        <h1>LinguaVerse</h1>
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
        {FEATURES.map(([ic, t, d]) => (
          <div className="card feat" key={t}>
            <div className="ic">{ic}</div>
            <h3 className="h2" style={{ marginTop: 8 }}>
              {t}
            </h3>
            <p className="sub" style={{ fontSize: 13.5 }}>
              {d}
            </p>
          </div>
        ))}
      </section>

      <section className="center" style={{ marginTop: 46 }}>
        <Link to="/register">
          <button className="btn primary" style={{ padding: "13px 28px", fontSize: 15 }}>
            Meet your companion
          </button>
        </Link>
        <p className="muted" style={{ marginTop: 12, fontSize: 12 }}>
          No affiliation with the official HSK exam — LinguaVerse only estimates
          your preparation readiness.
        </p>
      </section>
    </div>
  );
}