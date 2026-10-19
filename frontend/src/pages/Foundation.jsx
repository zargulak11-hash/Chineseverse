import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router-dom";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import { pinyinWhyLines } from "../components/PinyinWhy.jsx";
import { Empty, Loading } from "../components/ui.jsx";
import { useApi } from "../hooks/useApi.js";
import { canSpeakChinese, speakChinese } from "../zhSpeech.js";

// Step 1 of the journey (/foundation): the pinyin course
// (services/pinyin_course.py). A beginner used to get one page of
// mā/má/mǎ/mà and then a graded round of characters never taught -- a
// guess. Now each unit, in order, is a short lesson: understand (the
// explanation), listen and repeat (real syllables), try it with help (three
// questions answered with WHY, nothing graded or saved), then the mastery
// check -- a server-graded round (practice source "pronunciation", env =
// the unit). Passing every unit, or the tones round on real HSK 1
// characters at the end, completes the step (services/journey.py).

const TONES = [
  { zh: "妈", py: "mā", key: "1", mean: "ma1", path: "M4 8 H36" },
  { zh: "麻", py: "má", key: "2", mean: "ma2", path: "M4 22 L36 6" },
  { zh: "马", py: "mǎ", key: "3", mean: "ma3", path: "M4 14 Q16 30 26 22 T36 8" },
  { zh: "骂", py: "mà", key: "4", mean: "ma4", path: "M4 6 L36 26" },
  { zh: "吗", py: "ma", key: "0", mean: "ma0", path: null },
];
const PAIRS = [["是", "shì", "四", "sì"], ["十", "shí", "四", "sì"], ["买", "mǎi", "卖", "mài"], ["汤", "tāng", "糖", "táng"]];

function Contour({ path, className = "tone-contour" }) {
  return (
    <svg viewBox="0 0 40 32" className={className} aria-hidden="true">
      {path ? <path d={path} /> : <circle cx="20" cy="22" r="3" />}
    </svg>
  );
}

function Step({ n, title, children, done = false, now = false }) {
  return (
    <section className={`card fd-step${done ? " is-done" : ""}${now ? " is-now" : ""}`} aria-labelledby={`fd-step-${n}`}>
      <span className="fd-step-n" aria-hidden="true">{done ? <Icon name="check" size={16} /> : n}</span>
      <div className="fd-step-body">
        <h2 className="h2" id={`fd-step-${n}`}>{title}</h2>
        {children}
      </div>
    </section>
  );
}

// "Which one did you hear?" over one confusable pair.
function EarTest({ pair }) {
  const { t } = useTranslation();
  const [a, ap, b, bp] = pair;
  const [played, setPlayed] = useState(null); // index 0|1 of what was played
  const [picked, setPicked] = useState(null);

  function play() {
    // A warm-up, not a score: which of the two plays is simply a coin toss.
    const i = Math.random() < 0.5 ? 0 : 1;
    setPlayed(i);
    setPicked(null);
    speakChinese(i === 0 ? a : b);
  }

  return (
    <li className="fd-ear">
      <button type="button" className="btn small" onClick={play}>
        <Icon name="volume" size={14} /> {played === null ? t("foundation.earPlay") : t("foundation.earAgain")}
      </button>
      <div className="fd-ear-choices" role="group" aria-label={t("foundation.earWhich")}>
        {[[a, ap], [b, bp]].map(([zh, py], i) => {
          const state = picked === null ? "" : i === played ? " is-right" : i === picked ? " is-wrong" : "";
          return (
            <button key={zh} type="button" className={`fd-ear-choice${state}`} disabled={played === null || picked !== null}
                    onClick={() => setPicked(i)}>
              <b lang="zh-CN">{zh}</b> <small>{py}</small>
            </button>
          );
        })}
      </div>
      <span className="fd-ear-result" aria-live="polite">
        {picked !== null && (picked === played
          ? <><Icon name="check" size={13} /> {t("foundation.earRight")}</>
          : <><Icon name="x" size={13} /> {t("foundation.earWrong", { zh: played === 0 ? a : b })}</>)}
      </span>
    </li>
  );
}

// The tones unit's explanation: each tone's shape over the classic mā/má/mǎ/mà.
function ToneShapes() {
  const { t } = useTranslation();
  const [focus, setFocus] = useState(TONES[0]);
  function meet(tn) {
    setFocus(tn);
    speakChinese(tn.zh);
  }
  return (
    <>
      <div className="fd-focus" aria-live="polite">
        <Contour path={focus.path} className="fd-focus-contour" />
        <span className="fd-focus-zh" lang="zh-CN">{focus.zh}</span>
        <span className="fd-focus-py">{focus.py}</span>
        <span className="fd-focus-name">{t(`foundation.tone${focus.key}`)}</span>
        <span className="sub">{t(`foundation.mean.${focus.mean}`)}</span>
        <button type="button" className="btn small" onClick={() => speakChinese(focus.zh)}>
          <Icon name="volume" size={14} /> {t("foundation.hear")}
        </button>
      </div>
      <div className="tone-grid">
        {TONES.map((tn) => (
          <button key={tn.key} type="button" className={`tone-say${focus.key === tn.key ? " is-on" : ""}`}
                  onClick={() => meet(tn)} aria-pressed={focus.key === tn.key}
                  aria-label={`${t("foundation.hear")}: ${tn.zh} ${tn.py}`}>
            <Contour path={tn.path} />
            <span className="tone-zh" lang="zh-CN">{tn.zh}</span>
            <span className="tone-py">{tn.py}</span>
            <span className="tone-name">{t(`foundation.tone${tn.key}`)}</span>
          </button>
        ))}
      </div>
    </>
  );
}

// The words a guided question asks in, the same as the graded round's.
function guidedAsk(t, g) {
  if (g.type === "pinyin_part") return t(`soundWorld.ask.pinyin_part_${g.part}`, { item: g.ask });
  if (g.type.startsWith("pinyin_")) return t(`soundWorld.ask.${g.type}`, { item: g.ask });
  return t(`soundWorld.ask.${g.type}`);
}

// One guided question: pick until it is right, each pick explained.
function Guided({ g, n }) {
  const { t } = useTranslation();
  const [picks, setPicks] = useState([]);
  const solved = picks.includes(g.answer);
  const last = picks[picks.length - 1];
  const why = last === undefined ? [] : pinyinWhyLines(t, g.why[last]);
  return (
    <li className="py-guided">
      <p className="side-title">{t("pinyinCourse.question", { n })}</p>
      <p className="py-guided-ask">{guidedAsk(t, g)}</p>
      <div className="row" style={{ flexWrap: "wrap", gap: 8, margin: 0 }}>
        {(g.heard || solved) && (
          <button type="button" className="btn small" onClick={() => speakChinese(g.zh)}>
            <Icon name="volume" size={14} /> {t("pinyinCourse.play")}
          </button>
        )}
        {!g.heard && <span className="py-guided-item">{g.ask}</span>}
        {g.heard && !canSpeakChinese() && <span className="sub">{g.py}</span>}
      </div>
      <div className="fd-ear-choices py-guided-options" role="group" aria-label={guidedAsk(t, g)}>
        {g.options.map((o) => {
          const state = picks.includes(o.id) ? (o.id === g.answer ? " is-right" : " is-wrong") : "";
          return (
            <button key={o.id} type="button" className={`fd-ear-choice${state}`}
                    disabled={solved || picks.includes(o.id)} onClick={() => setPicks((p) => [...p, o.id])}>
              {o.label}
            </button>
          );
        })}
      </div>
      {last !== undefined && (
        <div className="practice-why" aria-live="polite">
          <p><b>{solved ? t("pinyinCourse.right") : t("pinyinCourse.wrong")}</b>{" "}
            {solved && <span lang="zh-CN">{g.zh} {g.py}</span>}
          </p>
          {why.map((line, i) => <p key={i}>{line}</p>)}
          {!solved && <p className="sub">{t("pinyinCourse.tryAgain")}</p>}
        </div>
      )}
    </li>
  );
}

function Examples({ unit }) {
  const { t } = useTranslation();
  if (unit.key === "py_syllable") {
    return (
      <ul className="py-split-list">
        {unit.examples.map((e) => (
          <li key={e.zh}>
            <button type="button" className="pinyin-parts py-split" onClick={() => speakChinese(e.zh)}
                    aria-label={`${t("foundation.hear")}: ${e.zh} ${e.py}`}>
              <span className="pinyin-part"><b>{e.initial || "—"}</b><small>{t("pinyinCourse.initial")}</small></span>
              <span className="pinyin-plus">+</span>
              <span className="pinyin-part"><b>{e.final}</b><small>{t("pinyinCourse.final")}</small></span>
              <span className="pinyin-plus">+</span>
              <span className="pinyin-part"><b>{e.tone || "·"}</b><small>{t("pinyinCourse.tone")}</small></span>
              <span className="pinyin-plus">=</span>
              <span className="pinyin-part is-result"><b lang="zh-CN">{e.zh} {e.py}</b></span>
            </button>
          </li>
        ))}
      </ul>
    );
  }
  return (
    <>
      <div className="tone-grid">
        {unit.examples.map((e) => (
          <button key={e.zh + e.py} type="button" className="tone-say" onClick={() => speakChinese(e.zh)}
                  aria-label={`${t("foundation.hear")}: ${e.zh} ${e.py}`}>
            <span className="tone-zh" lang="zh-CN">{e.zh}</span>
            <span className="tone-py">{e.py}</span>
            {e.parts && <span className="tone-name">{e.parts}</span>}
          </button>
        ))}
      </div>
      {unit.key === "py_tones" && canSpeakChinese() && (
        <div className="fd-ear-test">
          <p className="side-title">{t("foundation.earTitle")}</p>
          <p className="sub">{t("foundation.earBody")}</p>
          <ul className="fd-ears">
            {PAIRS.map((p) => <EarTest key={p[0] + p[2]} pair={p} />)}
          </ul>
        </div>
      )}
    </>
  );
}

function unitStatus(t, u, next) {
  if (u.passed) return { cls: "good", text: t("pinyinCourse.statusPassed", { score: Math.round(u.best) }) };
  if (u.played) return { cls: "", text: t("pinyinCourse.statusBest", { score: Math.round(u.best) }) };
  if (u.key === next) return { cls: "accent", text: t("pinyinCourse.statusNext") };
  return { cls: "", text: t("pinyinCourse.statusNew") };
}

export default function Foundation() {
  const { t } = useTranslation();
  const [params, setParams] = useSearchParams();
  const { data: course, error } = useApi("/sound-world/pinyin-course");
  const { data: journey } = useApi("/journey");
  const step = journey?.foundation?.steps?.find((s) => s.key === "tones");

  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  if (!course) return <Layout><Loading /></Layout>;

  const units = course.units;
  const asked = units.find((u) => u.key === params.get("unit"));
  const unit = asked || units.find((u) => u.key === course.next) || units[0];
  const i = units.indexOf(unit);
  const open = (u) => {
    setParams({ unit: u.key }, { replace: true });
    window.scrollTo({ top: 0, behavior: "smooth" });
  };
  const voice = canSpeakChinese();
  const stepDone = step?.status === "done";

  return (
    <Layout>
      <header className="page-head">
        <div>
          <div className="page-eyebrow"><Icon name="ear" size={13} /> {t("foundation.eyebrow")}</div>
          <h1 className="h1">{t("foundation.title")}</h1>
          <p className="sub">{t("foundation.subtitle")}</p>
        </div>
        <div className="kpi-row">
          <div className="kpi">
            <span className="kpi-value">{course.passed}/{course.total}</span>
            <span className="kpi-label">{t("pinyinCourse.kpiUnits")}</span>
          </div>
          {step && (
            <div className="kpi">
              <span className="kpi-value">{stepDone ? <Icon name="check" size={18} /> : "1/8"}</span>
              <span className="kpi-label">{t(`journey.status.${step.status}`)}</span>
            </div>
          )}
        </div>
      </header>

      <div className="ws">
        <div className="ws-main">
          <nav aria-label={t("pinyinCourse.unitsLabel")}>
            <ol className="py-units">
              {units.map((u) => {
                const st = unitStatus(t, u, course.next);
                return (
                  <li key={u.key}>
                    <button type="button" className={`py-unit${u.key === unit.key ? " is-on" : ""}${u.passed ? " is-passed" : ""}`}
                            aria-current={u.key === unit.key ? "step" : undefined} onClick={() => open(u)}>
                      <span className="py-unit-n" aria-hidden="true">{u.passed ? <Icon name="check" size={14} /> : u.n}</span>
                      <span className="py-unit-text">
                        <b>{u.title}</b>
                        <span className={`badge ${st.cls}`}>{st.text}</span>
                      </span>
                    </button>
                  </li>
                );
              })}
            </ol>
          </nav>

          <div className="fd-path" key={unit.key}>
            <p className="page-eyebrow" style={{ margin: "0 0 8px" }}>{t("pinyinCourse.unitN", { n: unit.n })} · {unit.title}</p>
            <Step n={1} title={t("pinyinCourse.stepLearn")}>
              <p>{unit.intro}</p>
              <ul className="py-points">
                {unit.points.map((p, k) => <li key={k}>{p}</li>)}
              </ul>
              {unit.key === "py_tones" && <ToneShapes />}
            </Step>

            <Step n={2} title={t("pinyinCourse.stepHear")}>
              <p className="sub">{t("pinyinCourse.stepHearBody")}</p>
              {!voice && <p className="sub">{t("foundation.noVoice")}</p>}
              <Examples unit={unit} />
            </Step>

            <Step n={3} title={t("pinyinCourse.stepTry")}>
              <p className="sub">{t("pinyinCourse.stepTryBody")}</p>
              <ol className="py-guided-list">
                {unit.guided.map((g, k) => <Guided key={`${unit.key}-${k}`} g={g} n={k + 1} />)}
              </ol>
            </Step>

            <Step n={4} title={t("pinyinCourse.stepCheck")} done={unit.passed} now={!unit.passed}>
              <p className="sub">{t("pinyinCourse.stepCheckBody", { score: Math.round(course.pass_score) })}</p>
              {unit.played > 0 && (
                <p className="sub">{t("foundation.bestScore", { score: Math.round(unit.best) })}</p>
              )}
              <div className="row" style={{ flexWrap: "wrap", gap: 8, margin: 0 }}>
                <Link to={`/practice?source=pronunciation&env=${unit.key}`} className={`btn${unit.passed ? "" : " primary"}`}>
                  <Icon name="target" size={15} /> {unit.played ? t("pinyinCourse.checkAgain") : t("pinyinCourse.startCheck")}
                </Link>
                {i > 0 && (
                  <button type="button" className="btn ghost" onClick={() => open(units[i - 1])}>
                    <Icon name="arrowLeft" size={15} /> {t("pinyinCourse.prevUnit")}
                  </button>
                )}
                {i + 1 < units.length && (
                  <button type="button" className={`btn${unit.passed ? " primary" : " ghost"}`} onClick={() => open(units[i + 1])}>
                    {t("pinyinCourse.nextUnit")} <Icon name="arrowRight" size={15} />
                  </button>
                )}
              </div>
            </Step>
          </div>
        </div>

        <aside className="ws-side">
          <div className="card side-card">
            <p className="side-title">{t("pinyinCourse.title")}</p>
            <p className="sub">{course.passed === course.total ? t("pinyinCourse.allPassed") : t("pinyinCourse.sideBody")}</p>
          </div>
          <div className={`card side-card foundation-round${stepDone ? " is-done" : ""}`}>
            <p className="side-title">{t("pinyinCourse.finalTitle")}</p>
            <p className="sub">{t("pinyinCourse.finalBody")}</p>
            <div className="side-links">
              <Link to="/practice?source=tones" className={`btn${course.passed === course.total && !stepDone ? " primary" : ""}`}>
                <Icon name="play" size={15} /> {t("foundation.startRound")}
              </Link>
              <Link to="/tone-coach" className="btn ghost">
                <Icon name="mic" size={15} /> {t("nav.toneCoach")}
              </Link>
            </div>
          </div>
          <div className="card side-card">
            <p className="side-title">{t("foundation.alsoTitle")}</p>
            <p className="sub">{t("foundation.alsoBody")}</p>
            <Link to="/sound-world" className="btn small">{t("nav.soundWorld")}</Link>
          </div>
        </aside>
      </div>
    </Layout>
  );
}
