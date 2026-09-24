import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useLocation } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../auth.js";

const DashboardContext = createContext(null);

// Previously Layout AND most individual pages (Dashboard, Companion, Duels)
// each fetched /dashboard independently, firing 2-3 concurrent identical
// requests on a single page view. This fetches it once per navigation and
// shares it, with `refresh()` for pages that just changed something
// dashboard-derived (animal, streak, XP) and want it to reflect immediately.
export function DashboardProvider({ children }) {
  const { user } = useAuth();
  const location = useLocation();
  const { i18n } = useTranslation();
  const [dashboard, setDashboard] = useState(null);
  const [error, setError] = useState("");
  const [version, setVersion] = useState(0);

  const refresh = useCallback(() => setVersion((v) => v + 1), []);

  useEffect(() => {
    if (!user) {
      setDashboard(null);
      return;
    }
    setError("");
    api
      .get("/dashboard")
      .then(setDashboard)
      .catch((e) => setError(e.message));
  }, [user, location.pathname, version, i18n.language]);

  return (
    <DashboardContext.Provider value={{ dashboard, setDashboard, error, refresh }}>
      {children}
    </DashboardContext.Provider>
  );
}

export function useDashboard() {
  return useContext(DashboardContext);
}
