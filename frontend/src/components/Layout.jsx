import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth.js";
import { useDashboard } from "../context/DashboardContext.jsx";
import Sidebar from "./Sidebar.jsx";
import Topbar from "./Topbar.jsx";

const COLLAPSE_KEY = "chineseverse_sidebar_collapsed";

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
        <main className="page route-ink-wipe" key={location.pathname}>
          {children}
        </main>
      </div>
    </div>
  );
}
