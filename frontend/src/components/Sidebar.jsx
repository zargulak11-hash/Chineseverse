import { animate } from "animejs";
import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { NavLink, useLocation } from "react-router-dom";
import { prefersReducedMotion } from "../anime.js";
import BrandLogo from "./BrandLogo.jsx";
import Icon from "./Icon.jsx";
import UserAvatar from "./UserAvatar.jsx";

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
      ["/real-chinese", "nav.realChinese", "mapPin"],
      ["/sound-world", "nav.soundWorld", "ear"],
      ["/detective", "nav.detective", "search"],
      ["/dna", "nav.dna", "dna"],
      ["/duels", "nav.duels", "swords"],
      ["/progress", "nav.progress", "chart"],
    ],
  },
  {
    labelKey: "nav.groupLearning",
    links: [
      ["/lessons", "nav.lessons", "book"],
      ["/sentence", "nav.sentence", "sparkles"],
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
      ["/voice-companion", "nav.voiceCompanion", "mic"],
      ["/achievements", "nav.achievements", "award"],
      ["/assistant", "nav.assistant", "chat"],
    ],
  },
];

// Owner-only — never shown to a regular user. This is a UX convenience,
// not the access boundary: even someone who forges is_admin in their own
// browser still hits a real 401/403 from the API (see app.deps.require_admin
// and App.jsx's RequireAdmin route guard).
const ADMIN_GROUP = {
  labelKey: "nav.groupAdmin",
  links: [
    ["/admin", "nav.adminHome", "chart"],
    ["/admin/users", "nav.adminUsers", "lock"],
  ],
};

export default function Sidebar({ collapsed, onToggleCollapse, mobileOpen, onCloseMobile, user, dashboard, onLogout }) {
  const { t } = useTranslation();
  const { pathname } = useLocation();
  const avatarUrl = dashboard?.avatar_url;
  const hsk = dashboard?.hsk_level ?? 1;

  const groups = user?.is_admin ? [...GROUPS, ADMIN_GROUP] : GROUPS;
  const allPaths = groups.flatMap((g) => g.links.map(([to]) => to));

  const navRef = useRef(null);
  const inkRef = useRef(null);
  const linkRefs = useRef({});
  const placedRef = useRef(false);

  const activePath = allPaths.includes(pathname) ? pathname : null;

  // The active indicator isn't a pill sliding into place — it's ink landing
  // on rice paper: each move oversizes and blurs the blob for an instant,
  // as if freshly touched down, then it settles/focuses into shape. Position
  // tracking itself (measure the active link's rect, FLIP to it) is
  // unchanged; only what happens visually while it travels is new.
  function moveInk(instant) {
    const nav = navRef.current;
    const ink = inkRef.current;
    const link = activePath && linkRefs.current[activePath];
    if (!nav || !ink) return;
    if (!link) {
      ink.style.opacity = 0;
      return;
    }
    const navRect = nav.getBoundingClientRect();
    const linkRect = link.getBoundingClientRect();
    const top = linkRect.top - navRect.top + nav.scrollTop;
    const left = linkRect.left - navRect.left + nav.scrollLeft;
    const { width, height } = linkRect;

    if (instant || !placedRef.current || prefersReducedMotion()) {
      Object.assign(ink.style, {
        opacity: 1,
        filter: "blur(0px)",
        top: `${top}px`,
        left: `${left}px`,
        width: `${width}px`,
        height: `${height}px`,
      });
      placedRef.current = true;
      return;
    }
    animate(ink, {
      opacity: [0.35, 1],
      filter: ["blur(7px)", "blur(0px)"],
      top,
      left,
      width,
      height,
      duration: 480,
      ease: "outExpo",
    });
  }

  // Route change — the target link's rect is already stable, animate to it.
  useEffect(() => {
    moveInk(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activePath]);

  // Collapse/expand changes the link's width via a CSS transition; wait for
  // it to settle before re-measuring, otherwise the ink chases a stale rect.
  useEffect(() => {
    placedRef.current = false;
    const id = setTimeout(() => moveInk(true), 240);
    return () => clearTimeout(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [collapsed]);

  return (
    <>
      {mobileOpen && <div className="sidebar-backdrop" onClick={onCloseMobile} />}
      <aside className={`sidebar${collapsed ? " collapsed" : ""}${mobileOpen ? " mobile-open" : ""}`}>
        <div className="sidebar-head">
          <span className="brand sidebar-brand">
            <BrandLogo className="brand-logo--sidebar" />
            <BrandLogo variant="mark" className="brand-logo--sidebar-mark" />
          </span>
          <button
            type="button"
            className="sidebar-collapse-btn"
            onClick={onToggleCollapse}
            title={collapsed ? t("ui.expandSidebar") : t("ui.collapseSidebar")}
            aria-label={collapsed ? t("ui.expandSidebar") : t("ui.collapseSidebar")}
          >
            <Icon name={collapsed ? "chevronRight" : "chevronLeft"} size={15} />
          </button>
        </div>

        <nav className="sidebar-nav" ref={navRef}>
          <div ref={inkRef} className="sidebar-ink-blob" style={{ opacity: 0 }} />
          {groups.map((group) => (
            <div className="sidebar-group" key={group.labelKey}>
              <div className="sidebar-group-label">
                <span className="sidebar-group-mark" aria-hidden="true" />
                {t(group.labelKey)}
              </div>
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
                    <span className="sidebar-link-brush" aria-hidden="true" />
                    <Icon name={icon} size={17} />
                    <span className="label">{label}</span>
                    {to === "/review" && dashboard?.review_due > 0 && (
                      <span className="sidebar-count" aria-label={t("practice.dueCount", { count: dashboard.review_due })}>
                        {dashboard.review_due > 99 ? "99+" : dashboard.review_due}
                      </span>
                    )}
                  </NavLink>
                );
              })}
            </div>
          ))}
        </nav>

        <div className="sidebar-profile">
          <UserAvatar url={avatarUrl} name={user?.username} size={36} />
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
