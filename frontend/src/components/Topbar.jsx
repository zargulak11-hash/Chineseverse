import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { usePrefs } from "../prefs.jsx";
import { useTheme } from "../theme.jsx";
import Icon from "./Icon.jsx";
import UserAvatar from "./UserAvatar.jsx";

const NAV_INDEX = [
  ["/dashboard", "nav.home", "home"],
  ["/real-chinese", "nav.realChinese", "mapPin"],
  ["/sound-world", "nav.soundWorld", "ear"],
  ["/detective", "nav.detective", "search"],
  ["/passport", "nav.passport", "award"],
  ["/dna", "nav.dna", "dna"],
  ["/duels", "nav.duels", "swords"],
  ["/progress", "nav.progress", "chart"],
  ["/lessons", "nav.lessons", "book"],
  ["/sentence", "nav.sentence", "sparkles"],
  ["/internet", "nav.internet", "eye"],
  ["/review", "nav.review", "clock"],
  ["/vocabulary", "nav.vocabulary", "type"],
  ["/hanzi", "nav.hanzi", "pen"],
  ["/ecosystem", "nav.ecosystem", "world"],
  ["/grammar", "nav.grammar", "seal"],
  ["/roadmap", "nav.roadmap", "trending"],
  ["/quests", "nav.quests", "target"],
  ["/missions", "nav.missions", "flag"],
  ["/pet-teacher", "nav.petTeacher", "teach"],
  ["/companion", "nav.companion", "heart"],
  ["/achievements", "nav.achievements", "award"],
  ["/assistant", "nav.assistant", "chat"],
];

// The places of the living world (backend services/world_places.py).
const WORLD_PLACES = [
  "home", "word_garden", "cafe", "university", "library", "bookstore", "street", "shop", "internet_cafe",
  "detective", "sound_plaza", "passport_office", "post_office", "bank", "police_station", "office", "hospital",
  "pharmacy", "metro", "train_station", "bus_station", "airport", "hotel", "park", "riverside", "sports_center",
  "bamboo_garden", "restaurant", "food_street", "market", "tea_house", "calligraphy", "museum", "temple", "hutong",
  "old_town", "shopping_district", "mall", "cinema", "ktv",
];

const DATE_LOCALE = { en: "en-US", ru: "ru-RU", tg: "tg-TJ", zh: "zh-CN" };

// A real search over the app's own content, not a decorative box: it
// matches page names instantly, and matches lesson/location titles once
// those lists have loaded (fetched lazily, on first focus, from the same
// endpoint Lessons.jsx already uses — no fake results) and the places of
// the living world on /real-chinese (names from i18n, no request needed).
function useGlobalSearch(t, lang) {
  const [query, setQuery] = useState("");
  const [lessons, setLessons] = useState(null);
  const loadedRef = useRef(false);

  // Lesson titles are localized by the API; the top bar persists across
  // pages, so reload them after a language switch instead of searching the
  // previous language's names.
  useEffect(() => {
    loadedRef.current = false;
    setLessons(null);
  }, [lang]);

  function ensureLoaded() {
    if (loadedRef.current) return;
    loadedRef.current = true;
    api.get("/lessons").then(setLessons).catch(() => setLessons([]));
  }

  const results = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return [];
    const out = [];
    for (const [to, labelKey, icon] of NAV_INDEX) {
      const label = t(labelKey);
      if (label.toLowerCase().includes(q)) out.push({ to, label, icon, kind: "Page" });
    }
    for (const l of lessons || []) {
      if (l.title?.toLowerCase().includes(q)) {
        out.push({ to: `/lessons/${l.id}`, label: l.title, icon: "book", kind: `HSK ${l.hsk_level || 1}` });
      }
    }
    for (const key of WORLD_PLACES) {
      const label = t(`world.place.${key}.name`);
      if (label.toLowerCase().includes(q)) {
        out.push({ to: `/real-chinese?place=${key}`, label, icon: "mapPin", kind: t("nav.realChinese") });
      }
    }
    return out.slice(0, 8);
  }, [query, lessons, t]);

  return { query, setQuery, results, ensureLoaded };
}

// How often the bell re-checks the real unread count while the app is open
// (also on every page change and when the tab/window regains focus).
// Stored notifications don't need the learner online -- this only
// refreshes the badge for someone who is.
const NOTIF_POLL_MS = 20_000;

function timeAgo(iso, lang) {
  if (!iso) return "";
  // The API returns naive UTC timestamps.
  const then = new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(iso) ? iso : `${iso}Z`).getTime();
  const secs = Math.round((then - Date.now()) / 1000);
  const rtf = new Intl.RelativeTimeFormat(DATE_LOCALE[lang] || "en-US", { numeric: "auto" });
  const abs = Math.abs(secs);
  if (abs < 60) return rtf.format(secs, "second");
  if (abs < 3600) return rtf.format(Math.round(secs / 60), "minute");
  if (abs < 86400) return rtf.format(Math.round(secs / 3600), "hour");
  if (abs < 86400 * 30) return rtf.format(Math.round(secs / 86400), "day");
  return new Intl.DateTimeFormat(DATE_LOCALE[lang] || "en-US", { month: "short", day: "numeric" }).format(new Date(then));
}

// Text for a stored notification, in the reader's language. Literal keys
// (not a template) so the i18n checker sees every one of them.
function notificationText(t, n) {
  const name = n.actor?.username || t("notifications.someone");
  switch (n.type) {
    case "follow":
      return t("notifications.follow", { name });
    case "duel_challenge":
      return t("notifications.duel_challenge", { name });
    case "duel_accepted":
      return t("notifications.duel_accepted", { name });
    case "duel_declined":
      return t("notifications.duel_declined", { name });
    case "duel_completed":
      return t("notifications.duel_completed", { name });
    default:
      return t("notifications.generic");
  }
}

// The bell shows two kinds of things: stored notifications from other
// people (GET /api/notifications -- persistent, per-user, with read state)
// and today's derived reminders (open quests, mistakes due) that come from
// the dashboard. Opening the dropdown never marks anything read; clicking
// one notification marks THAT one read (PATCH) and opens its link.
// showReminders is the Settings toggle: it only hides the derived
// reminders. Notifications from other people (e.g. a new follower) are
// always shown -- that toggle used to hide the whole bell, so on a device
// where it was off, follows never appeared.
function NotifBell({ dashboard, showReminders = true }) {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const [unread, setUnread] = useState(0);
  const [items, setItems] = useState(null);
  const [loadError, setLoadError] = useState(false);
  const ref = useRef(null);

  // The top bar stays mounted across pages now (Layout.jsx AppShell), so a
  // navigation that isn't a click here (back/forward, a link in the page)
  // must close the dropdown itself -- the old remount used to do it.
  useEffect(() => setOpen(false), [location.pathname]);

  useEffect(() => {
    function onDocClick(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  useEffect(() => {
    let alive = true;
    const check = () =>
      api
        .get("/notifications/unread-count")
        .then((r) => alive && setUnread(r.unread))
        .catch(() => {}); // badge just keeps its last value
    check();
    const id = setInterval(check, NOTIF_POLL_MS);
    const onFocus = () => document.visibilityState === "visible" && check();
    document.addEventListener("visibilitychange", onFocus);
    window.addEventListener("focus", onFocus);
    return () => {
      alive = false;
      clearInterval(id);
      document.removeEventListener("visibilitychange", onFocus);
      window.removeEventListener("focus", onFocus);
    };
    // the call also tells the server the current UI language
  }, [i18n.language, location.pathname]);

  useEffect(() => {
    if (!open) return;
    setLoadError(false);
    api
      .get("/notifications?limit=20")
      .then(setItems)
      .catch(() => setLoadError(true));
    // The list is capped; the count endpoint stays the source of truth.
    api.get("/notifications/unread-count").then((r) => setUnread(r.unread)).catch(() => {});
  }, [open]);

  async function openNotification(n) {
    setOpen(false);
    if (!n.read) {
      try {
        const updated = await api.patch(`/notifications/${n.id}/read`);
        setItems((list) => list && list.map((x) => (x.id === n.id ? updated : x)));
        setUnread((c) => Math.max(0, c - 1));
      } catch {
        // stays unread; the next poll shows the real state
      }
    }
    if (n.link) navigate(n.link);
  }

  const openQuests = showReminders ? (dashboard?.quests_today || []).filter((q) => !q.completed) : [];
  const mistakeCount = showReminders ? dashboard?.recent_mistakes?.length || 0 : 0;
  const reminders = openQuests.length + (mistakeCount > 0 ? 1 : 0);
  const stored = items || [];

  return (
    <div className="notif-wrap" ref={ref}>
      <button
        type="button"
        className="theme-toggle notif-btn"
        onClick={() => setOpen((o) => !o)}
        aria-label={unread > 0 ? t("notifications.bellUnread", { count: unread }) : t("topbar.notifications")}
        title={t("topbar.notifications")}
        aria-expanded={open}
      >
        <Icon name="bell" size={15} />
        {unread > 0 ? (
          <span className="notif-count">{unread > 9 ? "9+" : unread}</span>
        ) : (
          reminders > 0 && <span className="dot" />
        )}
      </button>
      {open && (
        <div className="notif-dropdown">
          <h4>{t("topbar.notifications")}</h4>
          {items === null && !loadError && <div className="notif-item sub">…</div>}
          {loadError && <div className="notif-item sub">{t("notifications.loadError")}</div>}
          {stored.map((n) => (
            <button
              key={n.id}
              type="button"
              className={`notif-item notif-entry${n.read ? "" : " is-unread"}`}
              onClick={() => openNotification(n)}
            >
              <UserAvatar url={n.actor?.avatar_url} name={n.actor?.username} size={28} />
              <span className="notif-text">
                <span>
                  {notificationText(t, n)}
                </span>
                <span className="notif-time">{timeAgo(n.created_at, i18n.language)}</span>
              </span>
              {!n.read && <span className="notif-unread-dot" aria-label={t("notifications.unread")} />}
            </button>
          ))}
          {items !== null && stored.length === 0 && reminders === 0 && (
            <div className="notif-item">
              <span className="ic"><Icon name="check" size={14} /></span>
              <span>{t("topbar.allCaughtUp")}</span>
            </div>
          )}
          {reminders > 0 && <h4 className="notif-subhead">{t("notifications.reminders")}</h4>}
          {openQuests.slice(0, 4).map((q) => (
            <Link key={q.id} to="/quests" className="notif-item" onClick={() => setOpen(false)}>
              <span className="ic"><Icon name="target" size={14} /></span>
              <span>
                <b>{q.title}</b> — {t("topbar.todayProgress", { progress: q.progress, target: q.target })}
              </span>
            </Link>
          ))}
          {mistakeCount > 0 && (
            <Link to="/mistakes" className="notif-item" onClick={() => setOpen(false)}>
              <span className="ic"><Icon name="alert" size={14} /></span>
              <span>{t("topbar.mistakesDue", { count: mistakeCount })}</span>
            </Link>
          )}
        </div>
      )}
    </div>
  );
}

export default function Topbar({ user, dashboard, onOpenMobileSidebar }) {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();
  const { notifEnabled } = usePrefs() || {};
  const { query, setQuery, results, ensureLoaded } = useGlobalSearch(t, i18n.language);
  const [searchOpen, setSearchOpen] = useState(false);
  const searchRef = useRef(null);
  const { pathname } = useLocation();
  useEffect(() => setSearchOpen(false), [pathname]);
  const dateFmt = useMemo(
    () => new Intl.DateTimeFormat(DATE_LOCALE[i18n.language] || "en-US", { weekday: "long", month: "long", day: "numeric" }),
    [i18n.language]
  );

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
  const avatarUrl = dashboard?.avatar_url;

  return (
    <header className="topbar">
      <button type="button" className="mobile-menu-btn" onClick={onOpenMobileSidebar} aria-label={t("ui.openMenu")}>
        <Icon name="menu" size={18} />
      </button>

      <div className="topbar-greeting">
        <div className="hello">{t("topbar.hello", { name: user?.username })}</div>
        <div className="date">{dateFmt.format(new Date())}</div>
      </div>

      <div className="topbar-search" ref={searchRef}>
        <Icon name="search" size={15} className="topbar-search-ic" />
        <input
          className="input"
          placeholder={t("topbar.searchPlaceholder")}
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
            {results.length === 0 && <div className="search-empty">{t("topbar.noMatches", { query })}</div>}
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
        <NotifBell dashboard={dashboard} showReminders={notifEnabled !== false} />
        <span className="chip">
          <Icon name="flame" size={13} />
          {streak} {t("common.day")}
        </span>
        <span className="chip">HSK {hsk} · {mastery.toFixed(0)}%</span>
        <button
          type="button"
          className="theme-toggle"
          onClick={toggleTheme}
          title={theme === "ink" ? t("ui.switchToPaper") : t("ui.switchToInk")}
          aria-label={t("ui.toggleTheme")}
        >
          <Icon name="droplet" size={15} />
        </button>
        <Link to="/profile" className="topbar-avatar" title={t("topbar.profile")}>
          <UserAvatar url={avatarUrl} name={user?.username} size={34} />
        </Link>
      </div>
    </header>
  );
}
