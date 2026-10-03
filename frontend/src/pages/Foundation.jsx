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

const TONES = [
  { zh: "妈", py: "mā", key: "1", mean: "ma1", path: "M4 8 H36" },
  { zh: "麻", py: "má", key: "2", mean: "ma2", path: "M4 22 L36 6" },
  { zh: "马", py: "mǎ", key: "3", mean: "ma3", path: "M4 14 Q16 30 26 22 T36 8" },
  { zh: "骂", py: "mà", key: "4", mean: "ma4", path: "M4 6 L36 26" },
  { zh: "吗", py: "ma", key: "0", mean: "ma0", path: null },
];
const PAIRS = [["是", "shì", "四", "sì"], ["十", "shí", "四", "sì"], ["买", "mǎi", "卖", "mài"], ["汤", "tāng", "糖", "táng"]];

function Say({ zh, py, children }) {
  const { t } = useTranslation();
  return (
    <button type="button" className="tone-say" onClick={() => speakChinese(zh)} aria-label={`${t("foundation.hear")}: ${zh} ${py}`}>
      {children}
    </button>
  );
}

export default function Foundation() {
  const { t } = useTranslation();
  const { data: journey } = useApi("/journey");
  const step = journey?.foundation?.steps?.find((s) => s.key === "tones");
  const voice = canSpeakChinese();
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
        <div className="ws-main">
          <section className="card">
            <h2 className="h2">{t("foundation.pinyinTitle")}</h2>
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
          </section>

          <section className="card">
            <h2 className="h2">{t("foundation.tonesTitle")}</h2>
            <p className="sub">{t("foundation.tonesBody")}</p>
            {!voice && <p className="sub">{t("foundation.noVoice")}</p>}
            <div className="tone-grid">
              {TONES.map((tn) => (
                <Say key={tn.key} zh={tn.zh} py={tn.py}>
                  <svg viewBox="0 0 40 32" className="tone-contour" aria-hidden="true">
                    {tn.path ? <path d={tn.path} /> : <circle cx="20" cy="22" r="3" />}
                  </svg>
                  <span className="tone-zh" lang="zh-CN">{tn.zh}</span>
                  <span className="tone-py">{tn.py}</span>
                  <span className="tone-name">{t(`foundation.tone${tn.key}`)}</span>
                  <span className="sub">{t(`foundation.mean.${tn.mean}`)}</span>
                </Say>
              ))}
            </div>
          </section>

          <section className="card">
            <h2 className="h2">{t("foundation.pairsTitle")}</h2>
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
          </section>
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
