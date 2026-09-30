import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import { Bar, Empty, Loading } from "../components/ui.jsx";
import { useApi } from "../hooks/useApi.js";

function Metric({ label, value, pct, alt }) {
  return (
    <div className="metric">
      <div className="metric-head">
        <span>{label}</span>
        <b>{value}</b>
      </div>
      <Bar value={pct} max={100} alt={alt} />
    </div>
  );
}

export default function Roadmap() {
  const { t } = useTranslation();
  const { data: r, error } = useApi("/hsk/roadmap");

  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  if (!r) return <Layout><Loading>{t("pages.roadmap.loading")}</Loading></Layout>;

  const stateIcon = (s) =>
    s === "locked" ? "lock" : s === "current" ? "star" : "check";
  const stateLabel = (s) =>
    s === "locked" ? t("pages.roadmap.locked") : s === "current" ? t("pages.roadmap.current") : t("pages.roadmap.unlocked");
  const pct = (done, total) => (total ? (done / total) * 100 : 0);

  const current =
    r.levels.find((l) => l.status === "current") || r.levels.find((l) => l.level === r.current_level) || r.levels[0];
  const wordsMastered = r.levels.reduce((n, l) => n + l.vocab_mastered, 0);
  const wordsTotal = r.levels.reduce((n, l) => n + l.vocab_total, 0);
  const lessonsDone = r.levels.reduce((n, l) => n + l.lessons_completed, 0);

  return (
    <Layout>
      <header className="page-head">
        <div>
          <div className="page-eyebrow">
            <Icon name="trending" size={13} /> HSK 1–9
          </div>
          <h1 className="h1">{t("pages.roadmap.title")}</h1>
          <p className="sub">{t("pages.roadmap.note")}</p>
        </div>
        <div className="kpi-row">
          <div className="kpi">
            <span className="kpi-value">HSK {current?.level ?? r.current_level}</span>
            <span className="kpi-label">{t("pages.roadmap.current")}</span>
          </div>
          <div className="kpi">
            <span className="kpi-value">{r.overall_mastery.toFixed(0)}%</span>
            <span className="kpi-label">{t("pages.roadmap.overall")}</span>
          </div>
          <div className="kpi">
            <span className="kpi-value">{wordsMastered}/{wordsTotal}</span>
            <span className="kpi-label">{t("pages.roadmap.words")}</span>
          </div>
          <div className="kpi">
            <span className="kpi-value">{lessonsDone}</span>
            <span className="kpi-label">{t("pages.roadmap.lessons")}</span>
          </div>
        </div>
      </header>

      <div className="ws">
        <div className="ws-main">
          <div className="roadmap-track">
            {r.levels.map((lvl) => {
              const stepClass =
                lvl.status === "current" ? "is-current" : lvl.status === "locked" ? "is-locked" : "is-done";
              return (
                <div key={lvl.level} className={`roadmap-step ${stepClass}`}>
                  <div className="roadmap-node" aria-hidden="true">{lvl.level}</div>
                  <div className="card">
                    <div className="roadmap-card-head">
                      <div className="row" style={{ gap: 8, flexWrap: "wrap" }}>
                        <Icon name={stateIcon(lvl.status)} size={16} />
                        <h2 className="h2" style={{ margin: 0 }}>HSK {lvl.level}</h2>
                        <span className={`badge ${lvl.status === "current" ? "accent" : ""}`}>
                          {stateLabel(lvl.status)}
                        </span>
                        {lvl.is_advanced_stage && (
                          <span className="badge" title={t("pages.roadmap.advancedStageHint")}>
                            {t("pages.roadmap.advancedStage")}
                          </span>
                        )}
                      </div>
                      <span className="muted" style={{ fontSize: 13 }}>
                        {lvl.vocab_mastered}/{lvl.vocab_total} {t("pages.roadmap.words")}
                      </span>
                    </div>
                    <div className="roadmap-metrics">
                      <Metric label={t("pages.roadmap.mastery")} value={`${lvl.mastery.toFixed(0)}%`} pct={lvl.mastery} />
                      <Metric
                        label={t("pages.roadmap.hanzi")}
                        value={`${lvl.hanzi_mastered}/${lvl.hanzi_total}`}
                        pct={pct(lvl.hanzi_mastered, lvl.hanzi_total)}
                        alt
                      />
                      <Metric
                        label={t("pages.roadmap.grammar")}
                        value={`${lvl.grammar_mastered}/${lvl.grammar_total}`}
                        pct={pct(lvl.grammar_mastered, lvl.grammar_total)}
                        alt
                      />
                      <Metric
                        label={t("pages.roadmap.lessons")}
                        value={lvl.lessons_completed}
                        pct={Math.min(100, lvl.lessons_completed * 10)}
                        alt
                      />
                    </div>
                    {lvl.ready_for_next ? (
                      <BadgeOK>{lvl.level + 1 <= 9 ? t("pages.roadmap.readyForNext", { level: lvl.level + 1 }) : t("pages.roadmap.maxLevel")}</BadgeOK>
                    ) : (
                      lvl.reason && <p className="muted" style={{ fontSize: 12, marginTop: 10 }}>{lvl.reason}</p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {current && (
          <aside className="ws-side">
            <div className="card side-card">
              <p className="side-title">{t("pages.roadmap.current")}</p>
              <div className="row spread" style={{ alignItems: "baseline" }}>
                <h2 className="h2" style={{ margin: 0, fontSize: 26 }}>HSK {current.level}</h2>
                <span className="badge accent">{current.mastery.toFixed(0)}%</span>
              </div>
              <div style={{ display: "grid", gap: 12, marginTop: 14 }}>
                <Metric
                  label={t("pages.roadmap.words")}
                  value={`${current.vocab_mastered}/${current.vocab_total}`}
                  pct={pct(current.vocab_mastered, current.vocab_total)}
                />
                <Metric
                  label={t("pages.roadmap.hanzi")}
                  value={`${current.hanzi_mastered}/${current.hanzi_total}`}
                  pct={pct(current.hanzi_mastered, current.hanzi_total)}
                  alt
                />
                <Metric
                  label={t("pages.roadmap.grammar")}
                  value={`${current.grammar_mastered}/${current.grammar_total}`}
                  pct={pct(current.grammar_mastered, current.grammar_total)}
                  alt
                />
              </div>
            </div>

            <div className="card side-card">
              <p className="side-title">{t("practice.startLevel", { level: current.level })}</p>
              <div className="side-links">
                <Link to={`/practice?source=vocab&level=${current.level}`}>
                  <button className="btn primary"><Icon name="type" size={15} /> {t("nav.vocabulary")}</button>
                </Link>
                <Link to={`/practice?source=hanzi&level=${current.level}`}>
                  <button className="btn"><Icon name="pen" size={15} /> {t("nav.hanzi")}</button>
                </Link>
                <Link to={`/practice?source=grammar&level=${current.level}`}>
                  <button className="btn"><Icon name="seal" size={15} /> {t("nav.grammar")}</button>
                </Link>
                <Link to="/lessons">
                  <button className="btn ghost"><Icon name="book" size={15} /> {t("nav.lessons")}</button>
                </Link>
                <Link to="/vocabulary">
                  <button className="btn ghost"><Icon name="type" size={15} /> {t("pages.roadmap.practiceVocab")}</button>
                </Link>
              </div>
            </div>
          </aside>
        )}
      </div>
    </Layout>
  );
}

function BadgeOK({ children }) {
  return <p className="badge good" style={{ marginTop: 12 }}>{children}</p>;
}
