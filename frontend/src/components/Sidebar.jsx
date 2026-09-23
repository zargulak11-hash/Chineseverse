import { NavLink } from "react-router-dom";
import AnimalAvatar from "./AnimalAvatar.jsx";
import Icon from "./Icon.jsx";

// Every real authenticated route, grouped the way the app itself is
// organized: MAIN is the core loop (home / explore / your DNA / compete),
// LEARNING is everything that builds or reviews vocabulary and grammar.
// No route here is invented — this is the same 12-link set the old top
// nav carried, just grouped and given room to breathe.
const GROUPS = [
  {
    label: "Main",
    links: [
      ["/dashboard", "Home", "home"],
      ["/world", "World", "world"],
      ["/dna", "DNA", "dna"],
      ["/duels", "Duels", "swords"],
    ],
  },
  {
    label: "Learning",
    links: [
      ["/lessons", "Lessons", "book"],
      ["/vocabulary", "Vocabulary", "type"],
      ["/roadmap", "HSK Roadmap", "trending"],
      ["/quests", "Quests", "target"],
      ["/missions", "Missions", "flag"],
      ["/pet-teacher", "Pet Teacher", "teach"],
      ["/companion", "Companion", "heart"],
      ["/achievements", "Achievements", "award"],
    ],
  },
];

export default function Sidebar({ collapsed, onToggleCollapse, mobileOpen, onCloseMobile, user, dashboard, onLogout }) {
  const animalSlug = dashboard?.animal?.slug;
  const hsk = dashboard?.hsk_level ?? 1;

  return (
    <>
      {mobileOpen && <div className="sidebar-backdrop" onClick={onCloseMobile} />}
      <aside className={`sidebar${collapsed ? " collapsed" : ""}${mobileOpen ? " mobile-open" : ""}`}>
        <div className="sidebar-head">
          <span className="brand sidebar-brand">
            <span className="logomark">中</span>
            <span className="label">中 ChineseVerse</span>
          </span>
          <button
            type="button"
            className="sidebar-collapse-btn"
            onClick={onToggleCollapse}
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            aria-label="Toggle sidebar"
          >
            <Icon name={collapsed ? "chevronRight" : "chevronLeft"} size={15} />
          </button>
        </div>

        <nav className="sidebar-nav">
          {GROUPS.map((group) => (
            <div className="sidebar-group" key={group.label}>
              <div className="sidebar-group-label">{group.label}</div>
              {group.links.map(([to, label, icon]) => (
                <NavLink
                  key={to}
                  to={to}
                  data-label={label}
                  onClick={onCloseMobile}
                  className={({ isActive }) => `sidebar-link${isActive ? " active" : ""}`}
                >
                  <Icon name={icon} size={17} />
                  <span className="label">{label}</span>
                </NavLink>
              ))}
            </div>
          ))}
        </nav>

        <div className="sidebar-profile">
          {animalSlug ? (
            <AnimalAvatar slug={animalSlug} size={36} />
          ) : (
            <span className="sidebar-profile-fallback">
              <Icon name="user" size={17} />
            </span>
          )}
          <div className="info">
            <div className="name">{user?.username}</div>
            <div className="role">HSK {hsk} learner</div>
          </div>
          <button type="button" className="sidebar-logout-btn" onClick={onLogout} title="Log out" aria-label="Log out">
            <Icon name="logout" size={15} />
          </button>
        </div>
      </aside>
    </>
  );
}
