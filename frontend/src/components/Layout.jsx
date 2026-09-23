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
//
// Most pages render a <Loading> spinner first and swap in their real
// content once a fetch resolves (same `<main>` DOM node throughout, since
// the route hasn't changed) — animating once on mount would just reveal the
// spinner, then let the real content pop in untouched afterwards. A
// MutationObserver waits for that swap and reveals whichever children are
// actually the real content, not a transient placeholder.
function PageReveal({ children }) {
  const ref = useRef(null);

  useEffect(() => {
    const root = ref.current;
    if (!root) return undefined;
    let done = false;
    let inFlight = null;

    function isPlaceholderOnly() {
      const kids = root.children;
      return kids.length === 1 && kids[0].classList.contains("loading");
    }

    function reveal() {
      if (done || root.children.length === 0 || isPlaceholderOnly()) return;
      done = true;
      observer.disconnect();

      const all = Array.from(root.children);
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

      inFlight = animate(targets, {
        opacity: [0, 1],
        translateY: [16, 0],
        duration: 550,
        delay: stagger(55, { start: 20 }),
        ease: "outSine",
      });
    }

    const observer = new MutationObserver(reveal);
    observer.observe(root, { childList: true });
    reveal();

    // React (StrictMode, concurrent features) can mount/cleanup/remount this
    // effect in quick succession — cancel any in-flight reveal from a prior
    // instance instead of leaving two animations racing on the same
    // elements' opacity (the visible symptom was opacity flickering up and
    // down instead of climbing smoothly to 1).
    return () => {
      observer.disconnect();
      inFlight?.revert();
    };
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
