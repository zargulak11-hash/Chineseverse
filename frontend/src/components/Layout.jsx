import { animate, stagger } from "animejs";
import { createContext, useContext, useEffect, useRef, useState } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { prefersReducedMotion } from "../anime.js";
import { useAuth } from "../auth.js";
import { useDashboard } from "../context/DashboardContext.jsx";
import AchievementToast from "./AchievementToast.jsx";
import ErrorBoundary from "./ErrorBoundary.jsx";
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
function PageReveal({ children, variant }) {
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
    <main ref={ref} className={`page route-reveal${variant ? ` page-${variant}` : ""}`}>
      {children}
    </main>
  );
}

// The sidebar + top bar used to be rendered by every page's own <Layout>.
// Each route renders a different page component, so React unmounted the
// whole shell on every navigation and mounted a fresh one: the sidebar's
// scrollable <nav> came back at scrollTop 0 (clicking Companion near the
// bottom threw the sidebar to the top), the collapse state had to be
// re-read from storage, and the active-link ink never travelled. The shell
// is now mounted once by a layout route in App.jsx (AppShell) and pages'
// <Layout> only renders the page content inside it.
const ShellContext = createContext(false);

function Shell({ children }) {
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
        {children}
      </div>
      <AchievementToast />
    </div>
  );
}

// The persistent shell: the element of the layout route wrapping every
// signed-in page in App.jsx. The matched page renders in the <Outlet />.
// The page gets its own error boundary here, below the shell: a page that
// throws while rendering must not take the sidebar down with it (that
// remounted the sidebar at scrollTop 0 on the next navigation).
export function AppShell() {
  const { pathname } = useLocation();
  return (
    <ShellContext.Provider value={true}>
      <Shell>
        <ErrorBoundary resetKey={pathname} inShell>
          <Outlet />
        </ErrorBoundary>
      </Shell>
    </ShellContext.Provider>
  );
}

// What every page wraps itself in: its content, revealed on each route.
// Inside AppShell that is all it renders; a page rendered outside it (no
// layout route) still gets the full shell, so nothing can lose its chrome.
// `variant` lets a page that IS its content (the world map on /real-chinese)
// drop the reading-width column: <Layout variant="world">.
export default function Layout({ children, variant }) {
  const inShell = useContext(ShellContext);
  const location = useLocation();
  const page = <PageReveal key={location.pathname} variant={variant}>{children}</PageReveal>;
  return inShell ? page : <Shell>{page}</Shell>;
}
