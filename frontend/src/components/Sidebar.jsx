import { animate } from "animejs";
import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { NavLink, useLocation } from "react-router-dom";
import { prefersReducedMotion } from "../anime.js";
import AnimalAvatar from "./AnimalAvatar.jsx";
import Icon from "./Icon.jsx";

// Every real authenticated route, grouped the way the app itself is
// organized: MAIN is the core loop (home / explore / your DNA / compete),
// LEARNING is everything that builds or reviews vocabulary and grammar.
// No route here is invented — this is the same 12-link set the old top
// nav carried, just grouped and given room to breathe. Labels come from
// i18n (nav.*); this array only carries the route shape.
const GROUPS = [
  {
    labelKey: "nav.groupMain",
    links: [
      ["/dashboard", "nav.home", "home"],
      ["/world", "nav.world", "world"],
      ["/dna", "nav.dna", "dna"],
      ["/duels", "nav.duels", "swords"],
      ["/progress", "nav.progress", "chart"],
    ],
  },
  {
    labelKey: "nav.groupLearning",
    links: [
      ["/lessons", "nav.lessons", "book"],
      ["/vocabulary", "nav.vocabulary", "type"],
      ["/roadmap", "nav.roadmap", "trending"],
      ["/quests", "nav.quests", "target"],
      ["/missions", "nav.missions", "flag"],
      ["/pet-teacher", "nav.petTeacher", "teach"],
      ["/companion", "nav.companion", "heart"],
      ["/achievements", "nav.achievements", "award"],
      ["/assistant", "nav.assistant", "chat"],
    ],
  },
];

const ALL_PATHS = GROUPS.flatMap((g) => g.links.map(([to]) => to));

export default function Sidebar({ collapsed, onToggleCollapse, mobileOpen, onCloseMobile, user, dashboard, onLogout }) {
  const { t } = useTranslation();
  const { pathname } = useLocation();
  const animalSlug = dashboard?.animal?.slug;
  const avatarUrl = dashboard?.avatar_url;
  const hsk = dashboard?.hsk_level ?? 1;

  const navRef = useRef(null);
  const pillRef = useRef(null);
  const linkRefs = useRef({});
  const placedRef = useRef(false);

  const activePath = ALL_PATHS.includes(pathname) ? pathname : null;

  function movePill(instant) {
    const nav = navRef.current;
    const pill = pillRef.current;
    const link = activePath && linkRefs.current[activePath];
    if (!nav || !pill) return;
    if (!link) {
      pill.style.opacity = 0;
      return;
    }
    const navRect = nav.getBoundingClientRect();
    const linkRect = link.getBoundingClientRect();
    const top = linkRect.top - navRect.top + nav.scrollTop;
    const left = linkRect.left - navRect.left + nav.scrollLeft;
    const { width, height } = linkRect;

    if (instant || !placedRef.current || prefersReducedMotion()) {
      Object.assign(pill.style, {
        opacity: 1,
        top: `${top}px`,
        left: `${left}px`,
        width: `${width}px`,
        height: `${height}px`,
      });
      placedRef.current = true;
      return;
    }
    animate(pill, {
      opacity: 1,
      top,
      left,
      width,
      height,
      duration: 420,
      ease: "outElastic(1, .75)",
    });
  }

  // Route change — the target link's rect is already stable, animate to it.
  useEffect(() => {
    movePill(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activePath]);

  // Collapse/expand changes the link's width via a CSS transition; wait for
  // it to settle before re-measuring, otherwise the pill chases a stale rect.
  useEffect(() => {
    placedRef.current = false;
    const id = setTimeout(() => movePill(true), 240);
    return () => clearTimeout(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [collapsed]);

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

        <nav className="sidebar-nav" ref={navRef}>
          <div ref={pillRef} className="sidebar-active-pill" style={{ opacity: 0 }} />
          {GROUPS.map((group) => (
            <div className="sidebar-group" key={group.labelKey}>
              <div className="sidebar-group-label">{t(group.labelKey)}</div>
              {group.links.map(([to, labelKey, icon]) => {
                const label = t(labelKey);
                return (
                  <NavLink
                    key={to}
                    to={to}
                    ref={(el) => {
                      if (el) linkRefs.current[to] = el;
                    }}
                    data-label={label}
                    onClick={onCloseMobile}
                    className={({ isActive }) => `sidebar-link${isActive ? " active" : ""}`}
                  >
                    <Icon name={icon} size={17} />
                    <span className="label">{label}</span>
                  </NavLink>
                );
              })}
            </div>
          ))}
        </nav>

        <div className="sidebar-profile">
          {avatarUrl ? (
            <img src={avatarUrl} alt="" className="avatar-preview" style={{ width: 36, height: 36 }} />
          ) : animalSlug ? (
            <AnimalAvatar slug={animalSlug} size={36} />
          ) : (
            <span className="sidebar-profile-fallback">
              <Icon name="user" size={17} />
            </span>
          )}
          <div className="info">
            <div className="name">{user?.username}</div>
            <div className="role">{t("nav.hskLearner", { level: hsk })}</div>
          </div>
          <button type="button" className="sidebar-logout-btn" onClick={onLogout} title={t("common.logOut")} aria-label={t("common.logOut")}>
            <Icon name="logout" size={15} />
          </button>
        </div>
      </aside>
    </>
  );
}
