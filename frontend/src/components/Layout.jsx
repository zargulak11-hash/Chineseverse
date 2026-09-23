import { animate, stagger } from "animejs";
import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { prefersReducedMotion } from "../anime.js";
import { useAuth } from "../auth.js";
import { useDashboard } from "../context/DashboardContext.jsx";
import Sidebar from "./Sidebar.jsx";
import Topbar from "./Topbar.jsx";

const COLLAPSE_KEY = "chineseverse_sidebar_collapsed";

// The one, single route transition, used on every page: a clean staggered
// fade + slight upward slide of the page's own content (hero banner, bento
// rows, cards...), each with a small per-element timing offset instead of
// everything appearing at once. Nothing else runs on top of it — there used
// to be a separate ink-wipe overlay animating at the same time, which read
// as messy competing motion; it's gone now, this is the only transition.
// Sections that run their own finer-grained entrance (Dashboard's quick
// actions/stat grid, Achievements' badge grid, ...) opt out via
// data-self-animate so the two animations don't stack on the same element.
function PageReveal({ children }) {
  const ref = useRef(null);

  useEffect(() => {
    const root = ref.current;
    if (!root) return;
    const all = Array.from(root.children);
    if (all.length === 0) return;

    if (prefersReducedMotion()) {
      all.forEach((el) => {
        el.style.opacity = 1;
      });
      return;
    }

    const selfAnimated = all.filter((el) => el.dataset.selfAnimate === "true");
    const targets = all.filter((el) => el.dataset.selfAnimate !== "true");
    selfAnimated.forEach((el) => {
      el.style.opacity = 1;
    });
    if (targets.length === 0) return;

    animate(targets, {
      opacity: [0, 1],
      translateY: [14, 0],
      duration: 420,
      delay: stagger(45, { start: 10 }),
      ease: "outCubic",
    });
  }, []);

  return (
    <main ref={ref} className="page route-reveal">
      {children}
    </main>
  );
}

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { dashboard } = useDashboard();
  const [collapsed, setCollapsed] = useState(() => {
    try {
      return localStorage.getItem(COLLAPSE_KEY) === "1";
    } catch {
      return false;
    }
  });
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  function toggleCollapse() {
    setCollapsed((c) => {
      const next = !c;
      try {
        localStorage.setItem(COLLAPSE_KEY, next ? "1" : "0");
      } catch {
        // ignore — storage may be unavailable
      }
      return next;
    });
  }

  function handleLogout() {
    logout();
    navigate("/");
  }

  return (
    <div className="shell">
      <Sidebar
        collapsed={collapsed}
        onToggleCollapse={toggleCollapse}
        mobileOpen={mobileOpen}
        onCloseMobile={() => setMobileOpen(false)}
        user={user}
        dashboard={dashboard}
        onLogout={handleLogout}
      />
      <div className="shell-main">
        <Topbar user={user} dashboard={dashboard} onOpenMobileSidebar={() => setMobileOpen(true)} />
        <PageReveal key={location.pathname}>{children}</PageReveal>
      </div>
    </div>
  );
}
