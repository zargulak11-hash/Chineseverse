import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import Art, { pronArt, soundArt } from "../components/Art.jsx";
import { AmbientToggle } from "../components/CaseAndSound.jsx";
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
// real text, never recordings. Each place can be heard before entering it:
// the same ambient noise its round plays (CaseAndSound AmbientToggle).

// A speed drawn as sound: the faster the stage, the denser the bars.
function SpeedGlyph({ stage }) {
  const n = 3 + stage * 2;
  const heights = [10, 18, 12, 22, 14, 20, 9, 16, 21, 11, 17];
  return (
    <svg className="sw-glyph" viewBox="0 0 64 28" aria-hidden="true">
      {Array.from({ length: n }, (_, i) => {
        const h = heights[i % heights.length];
        const x = 4 + (i * 56) / Math.max(n - 1, 1);
        return <line key={i} x1={x} x2={x} y1={14 - h / 2} y2={14 + h / 2} />;
      })}
    </svg>
  );
}

function ExampleChip({ e, playing, onPlay }) {
  const { t } = useTranslation();
  return (
    <button type="button" className={`sw-example${playing ? " is-playing" : ""}`} onClick={onPlay}
            aria-label={t("soundWorld.pron.hear", { text: e.zh })}>
      <span className="sw-eq" aria-hidden="true"><i /><i /><i /></span>
      <span lang="zh-CN" className="sw-example-zh">{e.zh}</span>
      <span className="sub">{e.py}{e.note ? ` · ${e.note}` : ""}</span>
    </button>
  );
}

function PronunciationLesson({ lesson, next, playing, play }) {
  const { t } = useTranslation();
  return (
    <li className={`sw-track${next ? " is-next" : ""}${lesson.passed ? " is-passed" : ""}`}>
      <span className="sw-track-n" aria-hidden="true">{lesson.passed ? <Icon name="check" size={14} /> : lesson.n}</span>
      <div className="sw-track-body">
        <div className="sw-track-head">
          <Art name={pronArt(lesson.key)} size={44} />
          <div style={{ minWidth: 0 }}>
            <h3 className="sw-track-title">{lesson.n}. {lesson.title}</h3>
            <p className="sub" lang="zh-CN" style={{ margin: 0 }}>{lesson.title_zh}</p>
          </div>
          {lesson.passed ? (
            <span className="badge good"><Icon name="check" size={11} /> {t("realLife.best", { score: Math.round(lesson.best) })}</span>
          ) : lesson.played > 0 ? (
            <span className="badge">{t("realLife.best", { score: Math.round(lesson.best) })}</span>
          ) : next ? (
            <span className="badge accent">{t("soundWorld.pron.next")}</span>
          ) : null}
        </div>
        <p className="sub sw-track-how">{lesson.how}</p>
        <div className="sw-examples" role="group" aria-label={t("soundWorld.pron.listen")}>
          {lesson.examples.map((e, i) => {
            const id = `${lesson.key}-${i}`;
            return <ExampleChip key={i} e={e} playing={playing === id} onPlay={() => play(e.zh, id)} />;
          })}
        </div>
        <Link to={`/practice?source=pronunciation&env=${lesson.key}`} className={`btn small ${next ? "primary" : ""}`}
              style={{ marginTop: 12, alignSelf: "flex-start" }}>
          <Icon name="play" size={13} /> {t(lesson.played ? "soundWorld.pron.again" : "soundWorld.pron.start")}
        </Link>
      </div>
    </li>
  );
}

export default function SoundWorld() {
  const { t } = useTranslation();
  const { data, error } = useApi("/sound-world/places");
  const { data: pron } = useApi("/sound-world/pronunciation");
  const [stage, setStage] = useState(null);
  const [playing, setPlaying] = useState(null);

  useEffect(() => {
    if (data && stage === null) setStage(data.recommended);
  }, [data, stage]);

  function play(text, id) {
    speakChinese(text, { onStart: () => setPlaying(id), onEnd: () => setPlaying(null) });
  }

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
          <section className="card sw-desk" aria-labelledby="sw-speed">
            <p className="side-title" id="sw-speed">{t("soundWorld.speed")}</p>
            <div className="sw-speeds" role="group" aria-labelledby="sw-speed">
              {data.stages.map((s) => (
                <button
                  key={s.stage}
                  type="button"
                  className={`sw-speed${chosen === s.stage ? " is-on" : ""}${s.unlocked ? "" : " is-locked"}`}
                  disabled={!s.unlocked}
                  aria-pressed={chosen === s.stage}
                  onClick={() => setStage(s.stage)}
                >
                  <SpeedGlyph stage={s.stage} />
                  <span className="sw-speed-name">
                    {!s.unlocked && <Icon name="lock" size={12} />} {t(`soundWorld.stage.${s.stage}`)}
                  </span>
                  <span className="sw-speed-state">
                    {s.unlocked
                      ? s.rounds > 0
                        ? t("soundWorld.stageBest", { best: Math.round(s.best), count: s.rounds })
                        : t("soundWorld.stageOpen")
                      : s.locked_reason === "level"
                        ? t("soundWorld.needLevel", { level: s.min_level })
                        : t("soundWorld.needPass", { score: Math.round(data.pass_score), prev: s.stage - 1 })}
                  </span>
                </button>
              ))}
            </div>
          </section>

          <h2 className="h2 section-title">{t("soundWorld.places")}</h2>
          <div className="sw-places">
            {data.envs.map((e) => (
              <article key={e.key} className="card sw-place">
                <div className="sw-place-art"><Art name={soundArt(e.key)} size={72} /></div>
                <div className="sw-place-body">
                  <div className="row spread" style={{ margin: 0, gap: 8 }}>
                    <h3 className="h2" style={{ margin: 0 }}>{t(`soundWorld.env.${e.key}`)}</h3>
                    {e.rounds > 0 && <span className="badge good">{t("realLife.best", { score: Math.round(e.best) })}</span>}
                  </div>
                  <p className="sub" lang="zh-CN" style={{ margin: 0 }}>{e.zh}</p>
                  <p className="sw-speakers">
                    <Icon name="users" size={13} /> {e.speakers.map((s) => t(`soundWorld.speaker.${s}`)).join(" · ")}
                  </p>
                  <div className="sw-place-actions">
                    <AmbientToggle env={e.key} />
                    <Link to={`/practice?source=sound&env=${e.key}&stage=${chosen}`} className="btn small primary">
                      <Icon name="ear" size={13} /> {t("soundWorld.enter", { stage: t(`soundWorld.stage.${chosen}`) })}
                    </Link>
                  </div>
                </div>
              </article>
            ))}
          </div>

          <h2 className="h2 section-title" style={{ marginTop: 24 }}>{t("soundWorld.pron.title")}</h2>
          <p className="sub" style={{ marginBottom: 16 }}>
            {t("soundWorld.pron.sub")}
            {pron && <> · {t("soundWorld.pron.progress", { passed: pron.passed, total: pron.lessons.length })}</>}
          </p>
          {pron ? (
            <ol className="sw-tracks">
              {pron.lessons.map((l) => (
                <PronunciationLesson key={l.key} lesson={l} next={l.key === pron.next} playing={playing} play={play} />
              ))}
            </ol>
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
