import { useEffect, useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../auth.js";
import { animalFace } from "./AnimalEmoji.jsx";

const LINKS = [
  ["/dashboard", "Home"],
  ["/world", "World"],
  ["/lessons", "Lessons"],
  ["/vocabulary", "Words"],
  ["/dna", "DNA"],
  ["/roadmap", "HSK"],
  ["/quests", "Quests"],
  ["/duels", "Duels"],
  ["/companion", "Companion"],
  ["/achievements", "Badges"],
];

export default function Layout({ children, hero = false }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [dashboard, setDashboard] = useState(null);

  useEffect(() => {
    api
      .get("/dashboard")
      .then(setDashboard)
      .catch(() => {});
  }, []);

  function handleLogout() {
    logout();
    navigate("/");
  }

  const animalSlug = dashboard?.animal?.slug;
  const hsk = dashboard?.hsk_level ?? 1;
  const mastery = dashboard?.mastery ?? 0;
  const streak = dashboard?.streak?.current_streak ?? 0;
  const accent = dashboard?.animal?.accent_color ?? "#f59e0b";

  return (
    <>
      <header className="appbar">
        <Link className="brand" to="/dashboard">
          <span className="logomark">🐉</span> LinguaVerse
        </Link>
        <nav className="nav">
          {LINKS.map(([to, label]) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) => `navlink${isActive ? " active" : ""}`}
            >
              {label}
            </NavLink>
          ))}
        </nav>
        <span className="spacer" />
        <span className="chip">🔥 {streak} day</span>
        <span className="chip">HSK {hsk} · {mastery.toFixed(0)}%</span>
        {animalSlug && (
          <Link to="/companion" title="My companion">
            <span className="chip" style={{ borderColor: accent }}>
              {animalFace(animalSlug)}
              <b>{dashboard?.animal?.name}</b>
            </span>
          </Link>
        )}
        <span className="chip">
          Hi, <b>{user?.username}</b>
        </span>
        <Link to="/profile" className="btn small ghost">
          Profile
        </Link>
        <button className="btn small danger" onClick={handleLogout}>
          Log out
        </button>
      </header>
      <main className={`page${hero ? "" : ""}`}>{children}</main>
    </>
  );
}