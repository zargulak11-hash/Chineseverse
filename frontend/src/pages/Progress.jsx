import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import ActivityHeatmap from "../components/ActivityHeatmap.jsx";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import { Empty, Loading } from "../components/ui.jsx";
import { api } from "../api.js";
import { useApi } from "../hooks/useApi.js";

// One stage per word/character (GET /api/analytics/knowledge): only a
// recall from memory moves a word past "recognised".
const STAGES = [
  ["learning", "pages.progress.knowLearning", "pages.progress.knowLearningWhat"],
  ["recognised", "pages.progress.knowRecognised", "pages.progress.knowRecognisedWhat"],
  ["recalled", "pages.progress.knowRecalled", "pages.progress.knowRecalledWhat"],
  ["mastered", "pages.progress.knowMastered", "pages.progress.knowMasteredWhat"],
];

function KnowledgeColumn({ title, stages }) {
  const { t } = useTranslation();
  return (
    <div className="know-col">
      <div className="row spread">
        <h3 className="side-title" style={{ margin: 0 }}>{title}</h3>
        <span className="sub">{t("pages.progress.knowMet", { count: stages.met })}</span>
      </div>
      {stages.met > 0 && (
        <div className="know-bar" aria-hidden="true">
          {STAGES.map(([k]) => stages[k] > 0 && <span key={k} className={`know-seg is-${k}`} style={{ flexGrow: stages[k] }} />)}
        </div>
      )}
      <ul className="know-list">
        {STAGES.map(([k, label, what]) => (
          <li key={k}>
            <span className={`know-dot is-${k}`} aria-hidden="true" />
            <span><b>{stages[k]}</b> {t(label)}<span className="sub know-what">{t(what)}</span></span>
          </li>
        ))}
      </ul>
      {/* FSRS's own prediction (services/srs.py), only over the items it
          models, and named as a prediction. */}
      {stages.memory?.tracked > 0 && (
        <p className="sub know-due">
          {t("pages.progress.knowMemory", { pct: stages.memory.predicted_recall, count: stages.memory.tracked })}
          {stages.memory.at_risk > 0 && ` · ${t("pages.progress.knowAtRisk", { count: stages.memory.at_risk })}`}
        </p>
      )}
      {stages.due > 0 && (
        <p className="sub know-due">
          {t("pages.progress.knowDue", { count: stages.due })}
          {stages.slipping > 0 && ` · ${t("pages.progress.knowSlipping", { count: stages.slipping })}`}
        </p>
      )}
    </div>
  );
}

function KnowledgeCard() {
  const { t } = useTranslation();
  const { data, error } = useApi("/analytics/knowledge");
  if (error) return <div className="card" style={{ marginTop: 16 }}><Empty>{error}</Empty></div>;
  if (!data) return <div className="card" style={{ marginTop: 16 }}><Loading /></div>;
  const met = data.vocab.met + data.hanzi.met;
  const recognised = data.vocab.recognised + data.hanzi.recognised;
  const due = data.vocab.due + data.hanzi.due;
  const r = data.recall;
  return (
    <section className="card" style={{ marginTop: 16 }} aria-labelledby="know-title">
      <h2 className="h2" id="know-title">{t("pages.progress.knowTitle")}</h2>
      <p className="sub">{t("pages.progress.knowSub")}</p>
      {met === 0 ? (
        <p className="sub empty-teach">{t("pages.progress.knowEmpty")}</p>
      ) : (
        <>
          <div className="grid grid-2" style={{ marginTop: 16 }}>
            <KnowledgeColumn title={t("pages.progress.knowWords")} stages={data.vocab} />
            <KnowledgeColumn title={t("pages.progress.knowChars")} stages={data.hanzi} />
          </div>
          <p className="sub" style={{ marginTop: 16 }}>
            {r.answered
              ? t("pages.progress.knowRecallAcc", { days: r.days, correct: r.correct, total: r.answered })
              : t("pages.progress.knowRecallNone", { days: r.days })}
          </p>
          {(recognised > 0 || due > 0) && (
            <div className="row" style={{ flexWrap: "wrap", marginTop: 12 }}>
              {recognised > 0 && <Link to="/practice?source=recall" className="btn primary">{t("pages.progress.knowGoRecall")}</Link>}
              {due > 0 && <Link to="/review" className="btn">{t("pages.progress.knowGoReview")}</Link>}
            </div>
          )}
        </>
      )}
    </section>
  );
}

const SECTION_COLORS = {
  world: "#4fc3f7",
  vocabulary: "#c58af2",
  lessons: "#4cc26b",
  duels: "#ff8a3d",
  quests: "#c9974a",
  missions: "#ff7a45",
  pet_teacher: "#3fb6a8",
  real_life: "#f06292",
  sentence: "#9ccc65",
  detective: "#8d6e63",
  sound_world: "#26c6da",
  internet: "#7e57c2",
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

      <KnowledgeCard />

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
          {/* The Streak card above counts days the app was opened; this map
              counts days with learning in them. Named for what it counts, so
              "1 record" there and "0" here no longer read as a contradiction
              (and the current streak isn't shown twice). */}
          <span className="chip"><Icon name="trophy" size={12} /> {t("pages.progress.bestStreakDays", { count: data.best_streak_past_year })}</span>
        </div>
        <ActivityHeatmap days={data.days} />
      </div>
    </Layout>
  );
}
