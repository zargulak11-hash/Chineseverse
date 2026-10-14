import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import { useApi } from "../hooks/useApi.js";
import { canSpeakChinese, speakChinese } from "../zhSpeech.js";

// Step 1 of the journey (/foundation): how pinyin spells a syllable, the four
// tones (and the light one) on the classic mā/má/mǎ/mà/ma, and the pairs
// beginners confuse -- then a real graded round (practice source "tones":
// HSK 1 characters' pinyin among the same syllable in other tones, and words
// by ear). Passing that round is what completes the step (services/journey.py).
//
// Laid out as a short lesson: understand -> meet each tone -> compare and
// test your ear -> practise. The ear test is a warm-up on this page only:
// nothing is graded or saved; the round on the side is what counts.

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

function Say({ zh, py, children, className = "tone-say" }) {
  const { t } = useTranslation();
  return (
    <button type="button" className={className} onClick={() => speakChinese(zh)} aria-label={`${t("foundation.hear")}: ${zh} ${py}`}>
      {children}
    </button>
  );
}

function Step({ n, title, children, done }) {
  return (
    <section className={`card fd-step${done ? " is-done" : ""}`} aria-labelledby={`fd-step-${n}`}>
      <span className="fd-step-n" aria-hidden="true">{n}</span>
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

export default function Foundation() {
  const { t } = useTranslation();
  const { data: journey } = useApi("/journey");
  const step = journey?.foundation?.steps?.find((s) => s.key === "tones");
  const voice = canSpeakChinese();
  const [focus, setFocus] = useState(TONES[0]);

  function meet(tn) {
    setFocus(tn);
    speakChinese(tn.zh);
  }

  return (
    <Layout>
      <header className="page-head">
        <div>
          <div className="page-eyebrow"><Icon name="ear" size={13} /> {t("foundation.eyebrow")}</div>
          <h1 className="h1">{t("foundation.title")}</h1>
          <p className="sub">{t("foundation.subtitle")}</p>
        </div>
        {step && (
          <div className="kpi-row">
            <div className="kpi">
              <span className="kpi-value">
                {step.status === "done" ? <Icon name="check" size={18} /> : "1/8"}
              </span>
              <span className="kpi-label">{t(`journey.status.${step.status}`)}</span>
            </div>
          </div>
        )}
      </header>

      <div className="ws">
        <div className="ws-main fd-path">
          <Step n={1} title={t("foundation.pinyinTitle")}>
            <p>{t("foundation.pinyinBody")}</p>
            <div className="pinyin-parts" aria-hidden="true">
              <span className="pinyin-part"><b>m</b><small>{t("foundation.partInitial")}</small></span>
              <span className="pinyin-plus">+</span>
              <span className="pinyin-part"><b>a</b><small>{t("foundation.partFinal")}</small></span>
              <span className="pinyin-plus">+</span>
              <span className="pinyin-part"><b>ˉ</b><small>{t("foundation.partTone")}</small></span>
              <span className="pinyin-plus">=</span>
              <span className="pinyin-part is-result"><b lang="zh-CN">妈 mā</b></span>
            </div>
          </Step>

          <Step n={2} title={t("foundation.tonesTitle")}>
            <p className="sub">{t("foundation.tonesBody")}</p>
            {!voice && <p className="sub">{t("foundation.noVoice")}</p>}
            {/* The tone in focus, large: its contour drawn over the syllable. */}
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
          </Step>

          <Step n={3} title={t("foundation.pairsTitle")}>
            <p className="sub">{t("foundation.pairsBody")}</p>
            <ul className="tone-pairs">
              {PAIRS.map(([a, ap, b, bp]) => (
                <li key={a + b}>
                  <Say zh={a} py={ap}><span lang="zh-CN">{a}</span> <small>{ap}</small></Say>
                  <span aria-hidden="true">·</span>
                  <Say zh={b} py={bp}><span lang="zh-CN">{b}</span> <small>{bp}</small></Say>
                </li>
              ))}
            </ul>
            {voice && (
              <div className="fd-ear-test">
                <p className="side-title">{t("foundation.earTitle")}</p>
                <p className="sub">{t("foundation.earBody")}</p>
                <ul className="fd-ears">
                  {PAIRS.map((p) => <EarTest key={p[0] + p[2]} pair={p} />)}
                </ul>
              </div>
            )}
          </Step>

          <Step n={4} title={t("foundation.roundTitle")} done={step?.status === "done"}>
            <p className="sub">{t("foundation.roundBody")}</p>
            <div className="row" style={{ flexWrap: "wrap", gap: 8, margin: 0 }}>
              <Link to="/practice?source=tones" className="btn primary">
                <Icon name="play" size={15} /> {t("foundation.startRound")}
              </Link>
              <Link to="/tone-coach" className="btn">
                <Icon name="mic" size={15} /> {t("nav.toneCoach")}
              </Link>
            </div>
          </Step>
        </div>

        <aside className="ws-side">
          <div className="card side-card foundation-round">
            <p className="side-title">{t("foundation.roundTitle")}</p>
            <p className="sub">{t("foundation.roundBody")}</p>
            <Link to="/practice?source=tones" className="btn primary">
              <Icon name="play" size={15} /> {t("foundation.startRound")}
            </Link>
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
