import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import { NextStepHero } from "../components/NextStep.jsx";
import SkillCheckCard from "../components/SkillCheck.jsx";
import { Bar, Empty, Loading } from "../components/ui.jsx";
import { useApi } from "../hooks/useApi.js";

// "Your Chinese journey" (/journey): where the learner is, the one next step,
// the foundation in order, HSK 1-9 as stages, and the special places worth
// opening now. Everything comes from GET /api/journey (services/journey.py),
// i.e. from the learner's own records -- nothing here is marked done for them.
//
// Drawn as a road: the foundation as a path of steps on a rail, HSK 1-9 as
// a ladder with a track on top, and the places to explore -- the ones that
// suit the learner now first.

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
  const features = [...data.features].sort((a, b) => Number(b.suggested) - Number(a.suggested));
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

      {/* Where do I stand, skill by skill? (services/diagnostic.py) -- for a
          learner past the first steps; a beginner's foundation comes first. */}
      {(f.complete || f.past) && <SkillCheckCard level={data.level} check={data.skill_check} />}

      <section className="journey-section">
        <div className="jr-section-head">
          <div>
            <h2 className="h2 section-title">{t("journey.foundationTitle")}</h2>
            <p className="sub">{f.past ? t("journey.foundationPast") : t("journey.foundationSub")}</p>
          </div>
          <span className="jr-count">{f.done}/{f.total}</span>
        </div>
        <Bar value={f.done} max={f.total} />
        <ol className="jr-path">
          {f.steps.map((s, i) => (
            <li key={s.key} className={`jr-step is-${s.status}`}>
              <span className="jr-node" aria-hidden="true">
                {s.status === "done" ? <Icon name="check" size={14} /> : i + 1}
              </span>
              <div className="jr-step-body">
                <div className="jr-step-head">
                  <h3 className="jr-step-title">{t(`journey.step.${s.key}.title`)}</h3>
                  <span className={`badge ${s.status === "done" ? "good" : s.status === "current" ? "accent" : ""}`}>
                    {t(`journey.status.${s.status}`)}
                  </span>
                </div>
                <p className="sub jr-step-what">{t(`journey.step.${s.key}.what`)}</p>
              </div>
              <Link to={s.to} className={`btn small${s.status === "current" ? " primary" : " ghost"}`}>
                {s.status === "done" ? t("journey.continue") : t("journey.go")} <Icon name="arrowRight" size={13} />
              </Link>
            </li>
          ))}
        </ol>
      </section>

      <section className="journey-section">
        <h2 className="h2 section-title">{t("journey.levelsTitle")}</h2>
        <p className="sub">{t("journey.levelsSub")}</p>
        <div className="jr-track" aria-hidden="true">
          {data.levels.map((l) => (
            <span key={l.level} className={`jr-track-seg is-${l.status}`}>{l.level}</span>
          ))}
        </div>
        <ol className="jr-ladder">
          {data.levels.map((l) => (
            <li key={l.level} className={`jr-rung is-${l.status}`}>
              <div className="jr-rung-id">
                <b className="jr-rung-name">HSK {l.level}</b>
                <span className="jr-rung-stage">{t(`journey.stage.${l.stage}`)}</span>
              </div>
              <div className="jr-rung-body">
                <p className="jr-rung-desc">{t(`journey.levelDesc.${l.level}`)}</p>
                <ul className="journey-level-facts">
                  {l.lessons_total > 0 && <li>{t("journey.levelLessons", { done: l.lessons_done, total: l.lessons_total })}</li>}
                  {l.stories_total > 0 && <li>{t("journey.levelStories", { read: l.stories_read, total: l.stories_total })}</li>}
                  {l.exam_passed && <li className="is-good"><Icon name="check" size={12} /> {t("journey.examPassed")}</li>}
                </ul>
              </div>
              <div className="jr-rung-side">
                <span className={`badge ${l.status === "current" ? "accent" : l.status === "done" ? "good" : ""}`}>
                  {t(`journey.levelStatus.${l.status}`)}
                </span>
                <span className="jr-rung-links">
                  <Link to={`/lessons?level=${l.level}`} className="btn small ghost">{t("nav.lessons")}</Link>
                  {l.stories_total > 0 && <Link to={`/stories?level=${l.level}`} className="btn small ghost">{t("nav.stories")}</Link>}
                </span>
              </div>
            </li>
          ))}
        </ol>
        <p className="sub" style={{ marginTop: 8 }}>{t("journey.band79")}</p>
      </section>

      <section className="journey-section">
        <h2 className="h2 section-title">{t("journey.exploreTitle")}</h2>
        <p className="sub">{t("journey.exploreSub")}</p>
        <ul className="jr-explore">
          {features.map((ft) => (
            <li key={ft.key}>
              <Link to={ft.to} className={`jr-place${ft.suggested ? " is-suggested" : ""}`}>
                <span className="journey-feature-icon" aria-hidden="true"><Icon name={FEATURE_ICON[ft.key]} size={18} /></span>
                <span className="jr-place-text">
                  <b>{t(FEATURE_NAME[ft.key])}</b>
                  <span className="sub">{t(`journey.feature.${ft.key}`)}</span>
                </span>
                <span className={`badge ${ft.suggested ? "accent" : ""}`}>{ft.suggested ? t("journey.goodNow") : t("journey.later")}</span>
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </Layout>
  );
}
