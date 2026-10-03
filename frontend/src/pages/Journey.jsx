import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import { NextStepHero } from "../components/NextStep.jsx";
import { Bar, Empty, Loading } from "../components/ui.jsx";
import { useApi } from "../hooks/useApi.js";

// "Your Chinese journey" (/journey): where the learner is, the one next step,
// the foundation in order, HSK 1-9 as stages, and the special places worth
// opening now. Everything comes from GET /api/journey (services/journey.py),
// i.e. from the learner's own records -- nothing here is marked done for them.

const FEATURE_ICON = {
  "sound-world": "ear", sentence: "sparkles", detective: "search", passport: "award", dna: "dna",
  ecosystem: "world", internet: "eye", stories: "bookOpen", "real-chinese": "mapPin",
};
const FEATURE_NAME = {
  "sound-world": "nav.soundWorld", sentence: "nav.sentence", detective: "nav.detective", passport: "nav.passport",
  dna: "nav.dna", ecosystem: "nav.ecosystem", internet: "nav.internet", stories: "nav.stories",
  "real-chinese": "nav.realChinese",
};

export default function Journey() {
  const { t } = useTranslation();
  const { data, error } = useApi("/journey");
  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  if (!data) return <Layout><Loading /></Layout>;
  const f = data.foundation;
  return (
    <Layout>
      <header className="page-head">
        <div>
          <div className="page-eyebrow"><Icon name="route" size={13} /> {t("journey.eyebrow")}</div>
          <h1 className="h1">{t("journey.title")}</h1>
          <p className="sub">{t("journey.subtitle")}</p>
        </div>
        <div className="kpi-row">
          <div className="kpi">
            <span className="kpi-value">{t(`journey.stage.${data.stage}`)}</span>
            <span className="kpi-label">HSK {data.level}</span>
          </div>
          <div className="kpi">
            <span className="kpi-value">{data.lessons_done}</span>
            <span className="kpi-label">{t("journey.lessonsDone")}</span>
          </div>
          <div className="kpi">
            <span className="kpi-value">{data.known_words}</span>
            <span className="kpi-label">{t("journey.wordsKnown")}</span>
          </div>
        </div>
      </header>

      <NextStepHero journey={data} />

      <section className="journey-section">
        <h2 className="h2 section-title">{t("journey.foundationTitle")}</h2>
        <p className="sub">{f.past ? t("journey.foundationPast") : t("journey.foundationSub")}</p>
        <Bar value={f.done} max={f.total} />
        <ol className="journey-steps">
          {f.steps.map((s, i) => (
            <li key={s.key} className={`journey-step card is-${s.status}`}>
              <div className="journey-step-head">
                <span className="journey-step-no" aria-hidden="true">
                  {s.status === "done" ? <Icon name="check" size={14} /> : i + 1}
                </span>
                <span className={`badge ${s.status === "done" ? "good" : s.status === "current" ? "accent" : ""}`}>
                  {t(`journey.status.${s.status}`)}
                </span>
              </div>
              <h3 className="journey-step-title">{t(`journey.step.${s.key}.title`)}</h3>
              <p className="sub">{t(`journey.step.${s.key}.what`)}</p>
              <Link to={s.to} className={`btn small${s.status === "current" ? " primary" : ""}`}>
                {s.status === "done" ? t("journey.continue") : t("journey.go")} <Icon name="arrowRight" size={13} />
              </Link>
            </li>
          ))}
        </ol>
      </section>

      <section className="journey-section">
        <h2 className="h2 section-title">{t("journey.levelsTitle")}</h2>
        <p className="sub">{t("journey.levelsSub")}</p>
        <ol className="journey-levels">
          {data.levels.map((l) => (
            <li key={l.level} className={`card journey-level is-${l.status}`}>
              <div className="row spread" style={{ margin: 0 }}>
                <b className="journey-level-name">HSK {l.level}</b>
                <span className={`badge ${l.status === "current" ? "accent" : l.status === "done" ? "good" : ""}`}>
                  {t(`journey.levelStatus.${l.status}`)}
                </span>
              </div>
              <span className="journey-level-stage">{t(`journey.stage.${l.stage}`)}</span>
              <p className="sub">{t(`journey.levelDesc.${l.level}`)}</p>
              <ul className="journey-level-facts">
                {l.lessons_total > 0 && <li>{t("journey.levelLessons", { done: l.lessons_done, total: l.lessons_total })}</li>}
                {l.stories_total > 0 && <li>{t("journey.levelStories", { read: l.stories_read, total: l.stories_total })}</li>}
                {l.exam_passed && <li className="is-good"><Icon name="check" size={12} /> {t("journey.examPassed")}</li>}
              </ul>
              <div className="row" style={{ gap: 8, marginTop: "auto", flexWrap: "wrap" }}>
                <Link to={`/lessons?level=${l.level}`} className="btn small ghost">{t("nav.lessons")}</Link>
                {l.stories_total > 0 && <Link to={`/stories?level=${l.level}`} className="btn small ghost">{t("nav.stories")}</Link>}
              </div>
            </li>
          ))}
        </ol>
        <p className="sub" style={{ marginTop: 8 }}>{t("journey.band79")}</p>
      </section>

      <section className="journey-section">
        <h2 className="h2 section-title">{t("journey.exploreTitle")}</h2>
        <p className="sub">{t("journey.exploreSub")}</p>
        <div className="grid cards">
          {data.features.map((ft) => (
            <Link key={ft.key} to={ft.to} className={`card hover journey-feature${ft.suggested ? " is-suggested" : ""}`}>
              <div className="row spread" style={{ margin: 0 }}>
                <span className="journey-feature-icon" aria-hidden="true"><Icon name={FEATURE_ICON[ft.key]} size={18} /></span>
                <span className={`badge ${ft.suggested ? "accent" : ""}`}>{ft.suggested ? t("journey.goodNow") : t("journey.later")}</span>
              </div>
              <b>{t(FEATURE_NAME[ft.key])}</b>
              <span className="sub">{t(`journey.feature.${ft.key}`)}</span>
            </Link>
          ))}
        </div>
      </section>
    </Layout>
  );
}
