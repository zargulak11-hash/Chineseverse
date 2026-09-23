import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { useTheme } from "../theme.jsx";
import AnimalAvatar from "./AnimalAvatar.jsx";
import Icon from "./Icon.jsx";

const NAV_INDEX = [
  ["/dashboard", "Home", "home"],
  ["/world", "World", "world"],
  ["/dna", "DNA", "dna"],
  ["/duels", "Duels", "swords"],
  ["/lessons", "Lessons", "book"],
  ["/vocabulary", "Vocabulary", "type"],
  ["/roadmap", "HSK Roadmap", "trending"],
  ["/quests", "Quests", "target"],
  ["/missions", "Missions", "flag"],
  ["/pet-teacher", "Pet Teacher", "teach"],
  ["/companion", "Companion", "heart"],
  ["/achievements", "Achievements", "award"],
];

const TODAY_FMT = new Intl.DateTimeFormat("en-US", { weekday: "long", month: "long", day: "numeric" });

// A real search over the app's own content, not a decorative box: it
// matches page names instantly, and matches lesson/location titles once
// those lists have loaded (fetched lazily, on first focus, from the same
// endpoints Lessons.jsx / WorldMap.jsx already use — no fake results).
function useGlobalSearch() {
  const [query, setQuery] = useState("");
  const [lessons, setLessons] = useState(null);
  const [locations, setLocations] = useState(null);
  const loadedRef = useRef(false);

  function ensureLoaded() {
    if (loadedRef.current) return;
    loadedRef.current = true;
    api.get("/lessons").then(setLessons).catch(() => setLessons([]));
    api.get("/world/locations").then(setLocations).catch(() => setLocations([]));
  }

  const results = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return [];
    const out = [];
    for (const [to, label, icon] of NAV_INDEX) {
      if (label.toLowerCase().includes(q)) out.push({ to, label, icon, kind: "Page" });
    }
    for (const l of lessons || []) {
      if (l.title?.toLowerCase().includes(q)) {
        out.push({ to: `/lessons/${l.id}`, label: l.title, icon: "book", kind: `HSK ${l.hsk_level || 1} lesson` });
      }
    }
    for (const loc of locations || []) {
      if (loc.name?.toLowerCase().includes(q)) {
        out.push({ to: `/world/${loc.slug}`, label: loc.name, icon: "mapPin", kind: "Location" });
      }
    }
    return out.slice(0, 8);
  }, [query, lessons, locations]);

  return { query, setQuery, results, ensureLoaded };
}

function NotifBell({ dashboard }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    function onDocClick(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  const openQuests = (dashboard?.quests_today || []).filter((q) => !q.completed);
  const mistakeCount = dashboard?.recent_mistakes?.length || 0;
  const count = openQuests.length + (mistakeCount > 0 ? 1 : 0);

  return (
    <div className="notif-wrap" ref={ref}>
      <button
        type="button"
        className="theme-toggle notif-btn"
        onClick={() => setOpen((o) => !o)}
        aria-label="Notifications"
        title="Notifications"
      >
        <Icon name="bell" size={15} />
        {count > 0 && <span className="dot" />}
      </button>
      {open && (
        <div className="notif-dropdown">
          <h4>Notifications</h4>
          {openQuests.length === 0 && mistakeCount === 0 && (
            <div className="notif-item">
              <span className="ic"><Icon name="check" size={14} /></span>
              <span>All caught up — nothing waiting on you.</span>
            </div>
          )}
          {openQuests.slice(0, 4).map((q) => (
            <Link key={q.id} to="/quests" className="notif-item" onClick={() => setOpen(false)}>
              <span className="ic"><Icon name="target" size={14} /></span>
              <span>
                <b>{q.title}</b> — {q.progress}/{q.target} today
              </span>
            </Link>
          ))}
          {mistakeCount > 0 && (
            <Link to="/mistakes" className="notif-item" onClick={() => setOpen(false)}>
              <span className="ic"><Icon name="alert" size={14} /></span>
              <span>{mistakeCount} mistake{mistakeCount === 1 ? "" : "s"} due for review</span>
            </Link>
          )}
        </div>
      )}
    </div>
  );
}

export default function Topbar({ user, dashboard, onOpenMobileSidebar }) {
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();
  const { query, setQuery, results, ensureLoaded } = useGlobalSearch();
  const [searchOpen, setSearchOpen] = useState(false);
  const searchRef = useRef(null);

  useEffect(() => {
    function onDocClick(e) {
      if (searchRef.current && !searchRef.current.contains(e.target)) setSearchOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  function goTo(to) {
    setSearchOpen(false);
    setQuery("");
    navigate(to);
  }

  const streak = dashboard?.streak?.current_streak ?? 0;
  const hsk = dashboard?.hsk_level ?? 1;
  const mastery = dashboard?.mastery ?? 0;
  const animalSlug = dashboard?.animal?.slug;

  return (
    <header className="topbar">
      <button type="button" className="mobile-menu-btn" onClick={onOpenMobileSidebar} aria-label="Open menu">
        <Icon name="menu" size={18} />
      </button>

      <div className="topbar-greeting">
        <div className="hello">你好, {user?.username}</div>
        <div className="date">{TODAY_FMT.format(new Date())}</div>
      </div>

      <div className="topbar-search" ref={searchRef}>
        <Icon name="search" size={15} className="topbar-search-ic" />
        <input
          className="input"
          placeholder="Search lessons, locations, pages…"
          value={query}
          onFocus={() => {
            ensureLoaded();
            setSearchOpen(true);
          }}
          onChange={(e) => {
            setQuery(e.target.value);
            setSearchOpen(true);
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter" && results[0]) goTo(results[0].to);
            if (e.key === "Escape") setSearchOpen(false);
          }}
        />
        {searchOpen && query.trim() && (
          <div className="search-results">
            {results.length === 0 && <div className="search-empty">No matches for "{query}"</div>}
            {results.map((r) => (
              <a key={r.kind + r.to} onClick={() => goTo(r.to)}>
                <Icon name={r.icon} size={15} />
                <span>
                  {r.label}
                  <span className="kind"> · {r.kind}</span>
                </span>
              </a>
            ))}
          </div>
        )}
      </div>

      <div className="topbar-actions">
        <NotifBell dashboard={dashboard} />
        <span className="chip">
          <Icon name="flame" size={13} />
          {streak} day
        </span>
        <span className="chip">HSK {hsk} · {mastery.toFixed(0)}%</span>
        <button
          type="button"
          className="theme-toggle"
          onClick={toggleTheme}
          title={theme === "ink" ? "Switch to Rice Paper" : "Switch to Ink"}
          aria-label="Toggle light/dark theme"
        >
          <Icon name="droplet" size={15} />
        </button>
        <Link to="/profile" className="topbar-avatar" title="Profile">
          {animalSlug ? <AnimalAvatar slug={animalSlug} size={34} /> : <Icon name="user" size={16} />}
        </Link>
      </div>
    </header>
  );
}
