import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import Icon from "../components/Icon.jsx";
import FeatureIntro from "../components/FeatureIntro.jsx";
import Layout from "../components/Layout.jsx";
import { Empty, Loading } from "../components/ui.jsx";
import { useApi } from "../hooks/useApi.js";
import { speakChinese } from "../zhSpeech.js";

// Chinese Sound World (services/sound_world.py). The speed stages and what
// unlocks them come from the learner's real Sound World rounds and Learning
// DNA; a place is played as a server-graded round
// (/practice?source=sound&env=...&stage=...). The pronunciation course
// (services/pronunciation.py) is played the same way with
// source=pronunciation; its sounds are the browser's Chinese voice reading
// real text, never recordings.
function PronunciationLesson({ lesson, next }) {
  const { t } = useTranslation();
  return (
    <article className={`card pron-lesson${next ? " is-next" : ""}`}>
      <div className="row spread" style={{ margin: 0 }}>
        <span className="scene-icon" aria-hidden="true">{lesson.icon}</span>
        {lesson.passed ? (
          <span className="badge good"><Icon name="check" size={11} /> {t("realLife.best", { score: Math.round(lesson.best) })}</span>
        ) : lesson.played > 0 ? (
          <span className="badge">{t("realLife.best", { score: Math.round(lesson.best) })}</span>
        ) : next ? (
          <span className="badge accent">{t("soundWorld.pron.next")}</span>
        ) : null}
      </div>
      <h3 className="h2" style={{ marginTop: 12 }}>{lesson.n}. {lesson.title}</h3>
      <p className="sub" lang="zh-CN">{lesson.title_zh}</p>
      <p className="sub">{lesson.how}</p>
      <div className="pron-examples" role="group" aria-label={t("soundWorld.pron.listen")}>
        {lesson.examples.map((e, i) => (
          <button key={i} type="button" className="btn small ghost" onClick={() => speakChinese(e.zh)}
                  aria-label={t("soundWorld.pron.hear", { text: e.zh })}>
            <span lang="zh-CN">{e.zh}</span> <span className="sub">{e.py}{e.note ? ` · ${e.note}` : ""}</span>
          </button>
        ))}
      </div>
      <Link to={`/practice?source=pronunciation&env=${lesson.key}`} className={`btn small ${next ? "primary" : ""}`}
            style={{ marginTop: 12, alignSelf: "flex-start" }}>
        <Icon name="play" size={13} /> {t(lesson.played ? "soundWorld.pron.again" : "soundWorld.pron.start")}
      </Link>
    </article>
  );
}

export default function SoundWorld() {
  const { t } = useTranslation();
  const { data, error } = useApi("/sound-world/places");
  const { data: pron } = useApi("/sound-world/pronunciation");
  const [stage, setStage] = useState(null);

  useEffect(() => {
    if (data && stage === null) setStage(data.recommended);
  }, [data, stage]);

  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  if (!data) return <Layout><Loading /></Layout>;

  const chosen = stage || data.recommended;
  return (
    <Layout>
      <header className="page-head">
        <div>
          <div className="page-eyebrow"><Icon name="ear" size={13} /> {t("nav.soundWorld")}</div>
          <h1 className="h1">{t("soundWorld.title")}</h1>
          <p className="sub">{t("soundWorld.subtitle")}</p>
        </div>
        <div className="kpi-row">
          <div className="kpi">
            <span className="kpi-value">{data.unlocked}/4</span>
            <span className="kpi-label">{t("soundWorld.speedsOpen")}</span>
          </div>
          <div className="kpi">
            <span className="kpi-value">{Math.round(data.listening)}</span>
            <span className="kpi-label">{t("companionReact.skill.listening")}</span>
          </div>
        </div>
      </header>
      <FeatureIntro feature="sound-world" />

      <div className="ws">
        <div className="ws-main">
          <div className="card">
            <p className="side-title">{t("soundWorld.speed")}</p>
            <div className="row" style={{ gap: 8, flexWrap: "wrap", margin: 0 }} role="group" aria-label={t("soundWorld.speed")}>
              {data.stages.map((s) => (
                <button
                  key={s.stage}
                  type="button"
                  className={`btn small ${chosen === s.stage ? "primary" : "ghost"}`}
                  disabled={!s.unlocked}
                  aria-pressed={chosen === s.stage}
                  onClick={() => setStage(s.stage)}
                >
                  {!s.unlocked && <Icon name="lock" size={12} />} {t(`soundWorld.stage.${s.stage}`)}
                </button>
              ))}
            </div>
            <ul className="scene-rules">
              {data.stages.map((s) => (
                <li key={s.stage}>
                  <b>{t(`soundWorld.stage.${s.stage}`)}</b>{" "}
                  {s.unlocked
                    ? s.rounds > 0
                      ? t("soundWorld.stageBest", { best: Math.round(s.best), count: s.rounds })
                      : t("soundWorld.stageOpen")
                    : s.locked_reason === "level"
                      ? t("soundWorld.needLevel", { level: s.min_level })
                      : t("soundWorld.needPass", { score: Math.round(data.pass_score), prev: s.stage - 1 })}
                </li>
              ))}
            </ul>
          </div>

          <h2 className="h2 section-title">{t("soundWorld.places")}</h2>
          <div className="grid cards">
            {data.envs.map((e) => (
              <Link key={e.key} to={`/practice?source=sound&env=${e.key}&stage=${chosen}`} className="card hover scene-card">
                <div className="row spread" style={{ margin: 0 }}>
                  <span className="scene-icon" aria-hidden="true">{e.icon}</span>
                  {e.rounds > 0 && <span className="badge good">{t("realLife.best", { score: Math.round(e.best) })}</span>}
                </div>
                <h3 className="h2" style={{ marginTop: 12 }}>{t(`soundWorld.env.${e.key}`)}</h3>
                <p className="sub" lang="zh-CN">{e.zh}</p>
                <p className="sub">
                  {e.speakers.map((s) => t(`soundWorld.speaker.${s}`)).join(" · ")}
                </p>
              </Link>
            ))}
          </div>

          <h2 className="h2 section-title" style={{ marginTop: 24 }}>{t("soundWorld.pron.title")}</h2>
          <p className="sub" style={{ marginBottom: 16 }}>
            {t("soundWorld.pron.sub")}
            {pron && <> · {t("soundWorld.pron.progress", { passed: pron.passed, total: pron.lessons.length })}</>}
          </p>
          {pron ? (
            <div className="pron-grid">
              {pron.lessons.map((l) => <PronunciationLesson key={l.key} lesson={l} next={l.key === pron.next} />)}
            </div>
          ) : <Loading />}
        </div>
        <aside className="ws-side">
          <div className="card side-card">
            <p className="side-title">{t("soundWorld.howTitle")}</p>
            <ul className="scene-rules">
              <li>{t("soundWorld.how.identify")}</li>
              <li>{t("soundWorld.how.info")}</li>
              <li>{t("soundWorld.how.respond")}</li>
              <li>{t("soundWorld.how.find")}</li>
              <li>{t("soundWorld.how.conversation")}</li>
              <li>{t("soundWorld.how.memory")}</li>
            </ul>
          </div>
          <div className="card side-card">
            <p className="side-title">{t("realLife.yourTier")}</p>
            <span className="badge accent">{t(`realLife.tier.${data.tier}`)}</span>
            <p className="sub" style={{ marginTop: 8 }}>{t("soundWorld.tierNote", { level: data.level })}</p>
          </div>
        </aside>
      </div>
    </Layout>
  );
}
