import { animate, stagger } from "animejs";
import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { prefersReducedMotion } from "../anime.js";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import { Bar, Empty, Loading } from "../components/ui.jsx";
import { useDashboard } from "../context/DashboardContext.jsx";
import { useApi } from "../hooks/useApi.js";

const CAT_ICON = {
  voice: "mic",
  social: "swords",
  progress: "trending",
  case_skill: "search",
  default: "award",
};

export default function Achievements() {
  const { t, i18n } = useTranslation();
  const { data, error } = useApi("/achievements");
  // XP / streak / level come from the dashboard the app already shares
  // (DashboardContext) -- no extra request for this page.
  const { dashboard } = useDashboard() || {};
  const badges = data || [];
  const rootRef = useRef(null);

  useEffect(() => {
    const root = rootRef.current;
    if (!root || badges.length === 0) return;
    const targets = Array.from(root.querySelectorAll(".ach-grid > .card"));
    if (prefersReducedMotion()) {
      targets.forEach((el) => {
        el.style.opacity = 1;
      });
      return;
    }
    animate(targets, {
      opacity: [0, 1],
      translateY: [26, 0],
      scale: [0.88, 1],
      duration: 640,
      delay: stagger(50),
      ease: "outElastic(1, .7)",
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [badges.length]);

  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  if (!data) return <Layout><Loading /></Layout>;

  const unlocked = badges.filter((b) => b.unlocked);
  const locked = badges.filter((b) => !b.unlocked);
  const completion = badges.length ? (unlocked.length / badges.length) * 100 : 0;
  const fmtDate = (iso) => new Date(iso).toLocaleDateString(i18n.language);
  const categoryLabel = (c) =>
    t(`pages.achievements.category.${c}`, { defaultValue: c || t("pages.achievements.hidden") });

  const recent = [...unlocked]
    .filter((b) => b.unlocked_at)
    .sort((a, b) => new Date(b.unlocked_at) - new Date(a.unlocked_at))
    .slice(0, 5);

  const byCategory = Object.values(
    badges.reduce((acc, b) => {
      const key = b.category || "general";
      acc[key] = acc[key] || { key, total: 0, done: 0 };
      acc[key].total += 1;
      if (b.unlocked) acc[key].done += 1;
      return acc;
    }, {})
  ).sort((a, b) => b.total - a.total);

  const badgeCard = (b) => (
    <div key={b.id} className={`card hover${b.unlocked ? " burst" : ""}`}
      style={
        b.unlocked
          ? { borderColor: "var(--accent-border)", boxShadow: "var(--ring-accent)" }
          : { opacity: 0.6 }
      }>
      <div className={`seal-stamp${b.unlocked ? "" : " locked"}`}>
        <Icon name={b.unlocked ? (CAT_ICON[b.category] || CAT_ICON.default) : "lock"} size={19} />
      </div>
      <b style={{ display: "block", marginTop: 10 }}>{b.title}</b>
      <p className="sub" style={{ fontSize: 12, marginTop: 4 }}>{b.description}</p>
      <span className={`badge ${b.unlocked ? "good" : ""}`}>
        {b.unlocked ? t("pages.achievements.unlocked") : categoryLabel(b.category)}
      </span>
      {b.unlocked_at && (
        <p className="muted" style={{ fontSize: 11, marginTop: 8 }}>{fmtDate(b.unlocked_at)}</p>
      )}
    </div>
  );

  return (
    <Layout>
      <header className="page-head">
        <div>
          <div className="page-eyebrow">
            <Icon name="award" size={13} /> {t("pages.achievements.earned", { unlocked: unlocked.length, total: badges.length })}
          </div>
          <h1 className="h1">{t("pages.achievements.title")}</h1>
          <div className="hbar" style={{ marginTop: 10, maxWidth: 520 }}>
            <Bar value={completion} />
            <span style={{ fontWeight: 800 }}>{completion.toFixed(0)}%</span>
          </div>
        </div>
        <div className="kpi-row">
          <div className="kpi">
            <span className="kpi-value">{unlocked.length}/{badges.length}</span>
            <span className="kpi-label">{t("pages.achievements.unlocked")}</span>
          </div>
          <div className="kpi">
            <span className="kpi-value">{dashboard?.user?.total_xp ?? "—"}</span>
            <span className="kpi-label">{t("common.xp")}</span>
          </div>
          <div className="kpi">
            <span className="kpi-value">{dashboard?.streak?.current_streak ?? "—"}</span>
            <span className="kpi-label">{t("dashboard.dayStreak")}</span>
          </div>
          <div className="kpi">
            <span className="kpi-value">{dashboard ? `HSK ${dashboard.hsk_level}` : "—"}</span>
            <span className="kpi-label">{t("dashboard.level")}</span>
          </div>
        </div>
      </header>

      <div className="ws">
        <div className="ws-main" ref={rootRef} data-self-animate="true">
          {badges.length === 0 && <Empty>{t("pages.achievements.noneYet")}</Empty>}
          {unlocked.length > 0 && (
            <>
              <h2 className="h2 section-title">{t("pages.achievements.unlocked")} · {unlocked.length}</h2>
              <div className="ach-grid">{unlocked.map(badgeCard)}</div>
            </>
          )}
          {locked.length > 0 && (
            <>
              <h2 className="h2 section-title">{t("pages.achievements.inProgress")} · {locked.length}</h2>
              <div className="ach-grid">{locked.map(badgeCard)}</div>
            </>
          )}
        </div>

        <aside className="ws-side">
          <div className="card side-card">
            <p className="side-title">{t("pages.achievements.recent")}</p>
            {recent.length === 0 ? (
              <p className="sub">{t("pages.achievements.noneYet")}</p>
            ) : (
              <div className="ach-recent">
                {recent.map((b) => (
                  <div key={b.id} className="ach-recent-row">
                    <div className="seal-stamp">
                      <Icon name={CAT_ICON[b.category] || CAT_ICON.default} size={15} />
                    </div>
                    <div style={{ minWidth: 0 }}>
                      <b style={{ display: "block", fontSize: 14 }}>{b.title}</b>
                      <span className="muted" style={{ fontSize: 12 }}>{fmtDate(b.unlocked_at)}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="card side-card">
            <p className="side-title">{t("pages.achievements.byCategory")}</p>
            <div style={{ display: "grid", gap: 12 }}>
              {byCategory.map((c) => (
                <div key={c.key} className="metric">
                  <div className="metric-head">
                    <span>{categoryLabel(c.key)}</span>
                    <b>{c.done}/{c.total}</b>
                  </div>
                  <Bar value={(c.done / c.total) * 100} alt={c.done === 0} />
                </div>
              ))}
            </div>
          </div>
        </aside>
      </div>
    </Layout>
  );
}
