import { Link, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../auth.js";
import { useDashboard } from "../context/DashboardContext.jsx";
import AnimalAvatar from "./AnimalAvatar.jsx";

const LINKS = [
  ["/dashboard", "Home"],
  ["/world", "World"],
  ["/lessons", "Lessons"],
  ["/vocabulary", "Words"],
  ["/dna", "DNA"],
  ["/roadmap", "HSK"],
  ["/quests", "Quests"],
  ["/missions", "Missions"],
  ["/duels", "Duels"],
  ["/companion", "Companion"],
  ["/pet-teacher", "Teach"],
  ["/achievements", "Badges"],
];

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { dashboard } = useDashboard();

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
        <span className="chip">🪙 {dashboard?.user?.coins ?? 0}</span>
        {animalSlug && (
          <Link to="/companion" title="My companion">
            <span className="chip" style={{ borderColor: accent }}>
              <AnimalAvatar slug={animalSlug} accentColor={accent} size={20} />
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
      <main className="page">{children}</main>
    </>
  );
}