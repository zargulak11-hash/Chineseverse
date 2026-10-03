import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useLocation } from "react-router-dom";
import { achievementDone, achievementIcon, achievementTitle } from "../achievements.js";
import { api } from "../api.js";
import { useDashboard } from "../context/DashboardContext.jsx";
import Icon from "./Icon.jsx";

const SHOW_MS = 6500;

// "Achievement unlocked!" -- a small note in the corner, never a modal: it
// must not interrupt a lesson. The dashboard lists unlocks not announced yet
// (new_achievements); each is announced once and marked seen on the server,
// so a refresh, another device or a new login doesn't repeat it. Several at
// once (e.g. progress made before achievements existed) become one note.
export default function AchievementToast() {
  const { t } = useTranslation();
  const { pathname } = useLocation();
  const { dashboard, setDashboard } = useDashboard() || {};
  const [note, setNote] = useState(null);
  const announced = useRef(new Set());

  // Never during an HSK exam: it is announced on the next page instead.
  const holding = pathname.startsWith("/exam/");

  useEffect(() => {
    if (holding) return;
    const fresh = (dashboard?.new_achievements || []).filter((a) => !announced.current.has(a.id));
    if (fresh.length === 0) return;
    fresh.forEach((a) => announced.current.add(a.id));
    setNote(fresh);
    api.post("/achievements/seen", { ids: fresh.map((a) => a.id) }).catch(() => {
      // Not marked: it may be announced once more later -- better than never.
    });
    // The shared dashboard would still list them until its next fetch.
    setDashboard?.((d) => (d ? { ...d, new_achievements: [] } : d));
  }, [dashboard, setDashboard, holding]);

  useEffect(() => {
    if (!note) return undefined;
    const timer = setTimeout(() => setNote(null), SHOW_MS);
    return () => clearTimeout(timer);
  }, [note]);

  if (!note || holding) return null;
  const one = note.length === 1 ? note[0] : null;
  return (
    <div className="card ach-toast" role="status" aria-live="polite">
      <div className="seal-stamp"><Icon name={one ? achievementIcon(one) : "trophy"} size={17} /></div>
      <div className="ach-toast-body">
        <span className="ach-toast-kicker">
          {one ? t("achievements.toast.one") : t("achievements.toast.many", { count: note.length })}
        </span>
        {one && <b className="ach-title">{achievementTitle(t, one.code, one.title)}</b>}
        {one && <span className="ach-text">{achievementDone(t, one)}</span>}
        {pathname !== "/achievements" && (
          <Link to="/achievements" className="ach-toast-link" onClick={() => setNote(null)}>
            {t("achievements.toast.view")} <Icon name="arrowRight" size={13} />
          </Link>
        )}
      </div>
      <button type="button" className="icon-btn" aria-label={t("achievements.toast.close")} onClick={() => setNote(null)}>
        <Icon name="x" size={16} />
      </button>
    </div>
  );
}
