import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth.js";
import { useDashboard } from "../context/DashboardContext.jsx";
import AnimalAvatar from "./AnimalAvatar.jsx";
import Icon from "./Icon.jsx";

const LINKS = [
  ["/dashboard", "Home", "home"],
  ["/world", "World", "world"],
  ["/lessons", "Lessons", "book"],
  ["/vocabulary", "Words", "type"],
  ["/dna", "DNA", "dna"],
  ["/roadmap", "HSK", "trending"],
  ["/quests", "Quests", "target"],
  ["/missions", "Missions", "flag"],
  ["/duels", "Duels", "swords"],
  ["/companion", "Companion", "heart"],
  ["/pet-teacher", "Teach", "teach"],
  ["/achievements", "Badges", "award"],
];

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { dashboard } = useDashboard();

  function handleLogout() {
    logout();
    navigate("/");
  }

  const animalSlug = dashboard?.animal?.slug;
  const hsk = dashboard?.hsk_level ?? 1;
  const mastery = dashboard?.mastery ?? 0;
  const streak = dashboard?.streak?.current_streak ?? 0;

  return (
    <>
      <header className="appbar">
        <Link className="brand" to="/dashboard">
          <span className="logomark">
            <Icon name="paw" size={16} />
          </span>
          LinguaVerse
        </Link>
        <nav className="nav">
          {LINKS.map(([to, label, icon]) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) => `navlink${isActive ? " active" : ""}`}
            >
              <Icon name={icon} size={14} />
              {label}
            </NavLink>
          ))}
        </nav>
        <span className="spacer" />
        <span className="chip">
          <Icon name="flame" size={13} />
          {streak} day
        </span>
        <span className="chip">HSK {hsk} · {mastery.toFixed(0)}%</span>
        <span className="chip">
          <Icon name="coin" size={13} />
          {dashboard?.user?.coins ?? 0}
        </span>
        {animalSlug && (
          <Link to="/companion" title="My companion">
            <span className="chip">
              <AnimalAvatar slug={animalSlug} size={20} />
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
          <Icon name="logout" size={13} />
          Log out
        </button>
      </header>
      <main className="page" key={location.pathname}>
        {children}
      </main>
    </>
  );
}
