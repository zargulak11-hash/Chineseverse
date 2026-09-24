import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import ActivityHeatmap from "../components/ActivityHeatmap.jsx";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import { Empty, Loading } from "../components/ui.jsx";
import { api } from "../api.js";

const SECTION_COLORS = {
  world: "#4fc3f7",
  vocabulary: "#c58af2",
  lessons: "#4cc26b",
  duels: "#ff8a3d",
  quests: "#c9974a",
  missions: "#ff7a45",
  pet_teacher: "#3fb6a8",
};

function fmtMinutes(m) {
  if (m >= 60) {
    const h = Math.floor(m / 60);
    const mm = Math.round(m % 60);
    return mm ? `${h}h ${mm}m` : `${h}h`;
  }
  return `${Math.round(m)}m`;
}

function SectionDonut({ sections, totalMinutes }) {
  const { t } = useTranslation();
  let acc = 0;
  const stops = sections.map((s) => {
    const color = SECTION_COLORS[s.section] || "var(--accent)";
    const start = acc;
    acc += s.percent;
    return `${color} ${start}% ${acc}%`;
  });
  const gradient = stops.length > 0 ? `conic-gradient(${stops.join(", ")})` : "var(--surface-2)";

  return (
    <div className="donut-wrap">
      <div className="donut" style={{ "--donut-gradient": gradient }}>
        <div className="donut-center">
          <div className="num">{fmtMinutes(totalMinutes)}</div>
          <div className="lbl">{t("pages.progress.total")}</div>
        </div>
      </div>
      <div className="donut-legend">
        {sections.length === 0 && <span className="sub" style={{ fontSize: 12 }}>{t("pages.progress.noActivity")}</span>}
        {sections.map((s) => (
          <div className="donut-legend-row" key={s.section}>
            <span className="donut-dot" style={{ background: SECTION_COLORS[s.section] || "var(--accent)" }} />
            <span className="name">{t(`pages.progress.section.${s.section}`, { defaultValue: s.label })}</span>
            <span className="pct">{s.percent.toFixed(0)}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function Progress() {
  const { t, i18n } = useTranslation();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/analytics/activity").then(setData).catch((e) => setError(e.message));
  }, [i18n.language]);

  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  if (!data) return <Layout><Loading>{t("pages.progress.loading")}</Loading></Layout>;

  return (
    <Layout>
      <h1 className="h1">{t("pages.progress.title")}</h1>
      <p className="sub">{t("pages.progress.subtitle")}</p>

      <div className="rhythm-grid" style={{ marginTop: 16 }}>
        <div className="card">
          <h2 className="h2">{t("pages.progress.learningRhythm")}</h2>
          <p className="sub" style={{ margin: 0 }}>{t("pages.progress.yourRealActivity")}</p>
          <div style={{ marginTop: 10 }}>
            <span style={{ fontSize: "var(--text-2xl)", fontWeight: 800 }}>{fmtMinutes(data.total_minutes)}</span>
            <span className="muted" style={{ marginLeft: 8, fontSize: 12.5 }}>{t("pages.progress.totalActiveTime")}</span>
          </div>

          <div className="rhythm-stats-row">
            <div className="rhythm-stat" style={{ "--stat-color": "#4fc3f7" }}>
              <span className="ic"><Icon name="clock" size={15} /></span>
              <div className="num">{fmtMinutes(data.today_minutes)}</div>
              <div className="lbl">{t("common.today")}</div>
              <div className="sub-count">{t("pages.progress.actions", { count: data.today_actions })}</div>
            </div>
            <div className="rhythm-stat" style={{ "--stat-color": "#4cc26b" }}>
              <span className="ic"><Icon name="trending" size={15} /></span>
              <div className="num">{fmtMinutes(data.week_minutes)}</div>
              <div className="lbl">{t("common.thisWeek")}</div>
              <div className="sub-count">{t("pages.progress.actions", { count: data.week_actions })}</div>
            </div>
            <div className="rhythm-stat" style={{ "--stat-color": "#9b6fe0" }}>
              <span className="ic"><Icon name="chart" size={15} /></span>
              <div className="num">{fmtMinutes(data.last_week_minutes)}</div>
              <div className="lbl">{t("common.lastWeek")}</div>
              <div className="sub-count">{t("pages.progress.actions", { count: data.last_week_actions })}</div>
            </div>
          </div>
        </div>

        <div className="col">
          <div className="card">
            <h2 className="h2">{t("pages.profile.streak")}</h2>
            <div className="streak-card-row" style={{ marginTop: 10 }}>
              <span className="streak-flame"><Icon name="flame" size={26} /></span>
              <div className="row" style={{ gap: 22 }}>
                <div>
                  <div style={{ fontSize: "var(--text-xl)", fontWeight: 800 }}>{data.streak.current_streak}</div>
                  <div className="lbl" style={{ fontSize: 10.5, color: "var(--text-faint)", textTransform: "uppercase" }}>{t("pages.profile.current")}</div>
                </div>
                <div>
                  <div style={{ fontSize: "var(--text-xl)", fontWeight: 800 }}>{data.streak.longest_streak}</div>
                  <div className="lbl" style={{ fontSize: 10.5, color: "var(--text-faint)", textTransform: "uppercase" }}>{t("pages.progress.record")}</div>
                </div>
              </div>
            </div>
          </div>

          <div className="card" style={{ marginTop: 16 }}>
            <h2 className="h2">{t("pages.progress.timeBySection")}</h2>
            <SectionDonut sections={data.sections} totalMinutes={data.total_minutes} />
          </div>
        </div>
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <h2 className="h2">{t("pages.progress.activityMap")}</h2>
        <div className="activity-chips">
          <span className="chip"><Icon name="target" size={12} /> {t("pages.progress.actionsThisYear", { count: data.total_actions_past_year })}</span>
          <span className="chip"><Icon name="flame" size={12} /> {t("pages.progress.currentStreakDays", { count: data.streak.current_streak })}</span>
          <span className="chip"><Icon name="trophy" size={12} /> {t("pages.progress.bestStreakDays", { count: data.best_streak_past_year })}</span>
        </div>
        <ActivityHeatmap days={data.days} />
      </div>
    </Layout>
  );
}
