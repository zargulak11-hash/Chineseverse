import { useEffect, useState } from "react";
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
          <div className="lbl">total</div>
        </div>
      </div>
      <div className="donut-legend">
        {sections.length === 0 && <span className="sub" style={{ fontSize: 12 }}>No tracked activity yet.</span>}
        {sections.map((s) => (
          <div className="donut-legend-row" key={s.section}>
            <span className="donut-dot" style={{ background: SECTION_COLORS[s.section] || "var(--accent)" }} />
            <span className="name">{s.label}</span>
            <span className="pct">{s.percent.toFixed(0)}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function Progress() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/analytics/activity").then(setData).catch((e) => setError(e.message));
  }, []);

  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  if (!data) return <Layout><Loading>Crunching your activity…</Loading></Layout>;

  return (
    <Layout>
      <h1 className="h1">Your progress</h1>
      <p className="sub">Real activity, tracked as you use the app — not estimates.</p>

      <div className="rhythm-grid" style={{ marginTop: 16 }}>
        <div className="card">
          <h2 className="h2">Learning Rhythm</h2>
          <p className="sub" style={{ margin: 0 }}>Your real activity</p>
          <div style={{ marginTop: 10 }}>
            <span style={{ fontSize: "var(--text-2xl)", fontWeight: 800 }}>{fmtMinutes(data.total_minutes)}</span>
            <span className="muted" style={{ marginLeft: 8, fontSize: 12.5 }}>total active time</span>
          </div>

          <div className="rhythm-stats-row">
            <div className="rhythm-stat" style={{ "--stat-color": "#4fc3f7" }}>
              <span className="ic"><Icon name="clock" size={15} /></span>
              <div className="num">{fmtMinutes(data.today_minutes)}</div>
              <div className="lbl">Today</div>
              <div className="sub-count">{data.today_actions} action{data.today_actions === 1 ? "" : "s"}</div>
            </div>
            <div className="rhythm-stat" style={{ "--stat-color": "#4cc26b" }}>
              <span className="ic"><Icon name="trending" size={15} /></span>
              <div className="num">{fmtMinutes(data.week_minutes)}</div>
              <div className="lbl">This week</div>
              <div className="sub-count">{data.week_actions} action{data.week_actions === 1 ? "" : "s"}</div>
            </div>
            <div className="rhythm-stat" style={{ "--stat-color": "#9b6fe0" }}>
              <span className="ic"><Icon name="chart" size={15} /></span>
              <div className="num">{fmtMinutes(data.last_week_minutes)}</div>
              <div className="lbl">Last week</div>
              <div className="sub-count">{data.last_week_actions} action{data.last_week_actions === 1 ? "" : "s"}</div>
            </div>
          </div>
        </div>

        <div className="col">
          <div className="card">
            <h2 className="h2">Streak</h2>
            <div className="streak-card-row" style={{ marginTop: 10 }}>
              <span className="streak-flame"><Icon name="flame" size={26} /></span>
              <div className="row" style={{ gap: 22 }}>
                <div>
                  <div style={{ fontSize: "var(--text-xl)", fontWeight: 800 }}>{data.streak.current_streak}</div>
                  <div className="lbl" style={{ fontSize: 10.5, color: "var(--text-faint)", textTransform: "uppercase" }}>current</div>
                </div>
                <div>
                  <div style={{ fontSize: "var(--text-xl)", fontWeight: 800 }}>{data.streak.longest_streak}</div>
                  <div className="lbl" style={{ fontSize: 10.5, color: "var(--text-faint)", textTransform: "uppercase" }}>record</div>
                </div>
              </div>
            </div>
          </div>

          <div className="card" style={{ marginTop: 16 }}>
            <h2 className="h2">Time by Section</h2>
            <SectionDonut sections={data.sections} totalMinutes={data.total_minutes} />
          </div>
        </div>
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <h2 className="h2">Activity Map</h2>
        <div className="activity-chips">
          <span className="chip"><Icon name="target" size={12} /> {data.total_actions_past_year} actions this year</span>
          <span className="chip"><Icon name="flame" size={12} /> {data.streak.current_streak}-day current streak</span>
          <span className="chip"><Icon name="trophy" size={12} /> {data.best_streak_past_year}-day best streak</span>
        </div>
        <ActivityHeatmap days={data.days} />
      </div>
    </Layout>
  );
}
