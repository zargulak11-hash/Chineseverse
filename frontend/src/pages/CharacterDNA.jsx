import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import { Bar, Empty, Loading } from "../components/ui.jsx";
import { useApi } from "../hooks/useApi.js";
import { speakChinese } from "../zhSpeech.js";
import { formatDate } from "../dates.js";

// Character DNA (GET /api/hanzi/character/:char/dna): one character's
// structure, the real words built from it, related characters, curriculum
// examples, and this learner's own history with it. Read-only.


function fmtDate(iso, lang) {
  if (!iso) return null;
  try {
    return formatDate(iso, lang, { dateStyle: "medium" });
  } catch {
    return iso.slice(0, 10);
  }
}

function Hear({ text, label }) {
  return (
    <button type="button" className="btn small ghost" onClick={() => speakChinese(text)} aria-label={label} title={label}>
      <Icon name="ear" size={14} style={{ verticalAlign: -2 }} />
    </button>
  );
}

export function StatusDot({ status, due }) {
  const { t } = useTranslation();
  const key = due ? "due" : status || "new";
  return <span className={`status-dot is-${key}`} title={t(`charDna.status.${key}`)} aria-label={t(`charDna.status.${key}`)} />;
}

function CharChip({ c }) {
  return (
    <Link to={`/hanzi/${encodeURIComponent(c.char)}`} className="char-chip">
      <b lang="zh-CN">{c.char}</b>
      <span className="sub">{c.pinyin}</span>
      {c.meaning && <span className="char-chip-meaning">{c.meaning}</span>}
    </Link>
  );
}

function Branch({ label, words }) {
  if (!words.length) return null;
  return (
    <li>
      <span className="tree-label">{label}</span>
      <ul>
        {words.map((w) => (
          <li key={w.id} className="tree-word">
            <StatusDot status={w.status} due={w.due} />
            <b lang="zh-CN">{w.text}</b>
            <span className="sub"> {w.pinyin}</span>
            <span className="tree-meaning"> — {w.meaning}</span>
            {w.level && <span className="badge">HSK {w.level}</span>}
          </li>
        ))}
      </ul>
    </li>
  );
}

export default function CharacterDNA() {
  const { t, i18n } = useTranslation();
  const { char } = useParams();
  const { data, error } = useApi(`/hanzi/character/${encodeURIComponent(char)}/dna`);

  if (error) {
    return (
      <Layout>
        <Empty>{error}</Empty>
        <Link to="/hanzi" className="btn ghost" style={{ marginTop: 12 }}>{t("practice.back")}</Link>
      </Layout>
    );
  }
  if (!data) return <Layout><Loading /></Layout>;

  const m = data.mine;
  const single = data.words.find((w) => w.text === data.char);
  return (
    <Layout>
      <header className="page-head">
        <div className="char-head">
          <span className="char-glyph" lang="zh-CN">{data.char}</span>
          <div style={{ minWidth: 0 }}>
            <div className="page-eyebrow"><Icon name="dna" size={13} /> {t("charDna.eyebrow")}</div>
            <h1 className="h1">
              {data.pinyin} <Hear text={data.char} label={t("companionReact.hear")} />
            </h1>
            <p className="sub">{data.meaning || single?.meaning}</p>
            <div className="row" style={{ gap: 8, flexWrap: "wrap", marginTop: 8 }}>
              {data.level && <span className="badge">HSK {data.level}</span>}
              {data.stroke_count && <span className="badge">{t("pages.hanzi.strokes", { count: data.stroke_count })}</span>}
              {data.handwriting_tier && <span className="badge accent">{t("pages.hanzi.handwriting")}</span>}
            </div>
          </div>
        </div>
        <div className="kpi-row">
          <div className="kpi">
            <span className="kpi-value">{Math.round(m.mastery)}%</span>
            <span className="kpi-label">{t("charDna.mastery")}</span>
          </div>
          <div className="kpi">
            <span className="kpi-value">{m.words_mastered}/{m.words_total}</span>
            <span className="kpi-label">{t("charDna.wordsMastered")}</span>
          </div>
        </div>
      </header>

      <div className="ws">
        <div className="ws-main">
          <div className="card">
            <h2 className="h2">{t("charDna.structure")}</h2>
            {data.components.length === 0 && !data.radical ? (
              <p className="sub">{t("charDna.noStructure")}</p>
            ) : (
              <div className="char-structure">
                {data.radical && (
                  <div>
                    <p className="side-title">{t("charDna.radical")}</p>
                    <CharChip c={data.radical} />
                  </div>
                )}
                {data.components.length > 0 && (
                  <div>
                    <p className="side-title">{t("charDna.components")}</p>
                    <div className="chip-row">{data.components.map((c, i) => <CharChip key={`${c.char}-${i}`} c={c} />)}</div>
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="card">
            <div className="row spread" style={{ margin: 0, flexWrap: "wrap" }}>
              <h2 className="h2">{t("charDna.family")}</h2>
              <Link to={`/ecosystem?center=${encodeURIComponent(data.char)}`} className="btn small">
                <Icon name="world" size={13} /> {t("charDna.openEcosystem")}
              </Link>
            </div>
            {data.words.filter((w) => w.text.length > 1).length === 0 ? (
              <p className="sub">{t("charDna.noWords")}</p>
            ) : (
              <ul className="word-tree" aria-label={t("charDna.family")}>
                <li>
                  <span className="tree-root" lang="zh-CN">{data.char}</span>
                  <ul>
                    <Branch label={t("charDna.startsWith", { char: data.char })} words={data.tree.starts} />
                    <Branch label={t("charDna.endsWith", { char: data.char })} words={data.tree.ends} />
                    <Branch label={t("charDna.inside", { char: data.char })} words={data.tree.inside} />
                  </ul>
                </li>
              </ul>
            )}
            <p className="sub legend">
              <StatusDot status="mastered" /> {t("charDna.status.mastered")} <StatusDot status="reviewing" /> {t("charDna.status.reviewing")}{" "}
              <StatusDot status="learning" /> {t("charDna.status.learning")} <StatusDot status="new" /> {t("charDna.status.new")}{" "}
              <StatusDot due /> {t("charDna.status.due")}
            </p>
          </div>

          <div className="card">
            <h2 className="h2">{t("charDna.related")}</h2>
            {[["partners", "charDna.partners"], ["same_radical", "charDna.sameRadical"], ["shared_component", "charDna.sharedComponent"]].map(
              ([key, label]) =>
                data.related[key].length > 0 && (
                  <div key={key} style={{ marginTop: 12 }}>
                    <p className="side-title">{t(label)}</p>
                    <div className="chip-row">{data.related[key].map((c) => <CharChip key={c.char} c={c} />)}</div>
                  </div>
                )
            )}
            {!data.related.partners.length && !data.related.same_radical.length && !data.related.shared_component.length && (
              <p className="sub">{t("charDna.noRelated")}</p>
            )}
          </div>

          <div className="card">
            <h2 className="h2">{t("charDna.examples")}</h2>
            {data.examples.length === 0 ? (
              <p className="sub">{t("pages.hanzi.noExamples")}</p>
            ) : (
              <ul className="char-examples">
                {data.examples.map((e) => (
                  <li key={e.text}>
                    <div className="row" style={{ margin: 0, gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                      <span lang="zh-CN" className="scene-line-zh">{e.text}</span>
                      <Hear text={e.text} label={t("companionReact.hear")} />
                      <Link to={`/sentence?text=${encodeURIComponent(e.text)}`} className="btn small ghost">
                        <Icon name="sparkles" size={13} /> {t("charDna.makeLesson")}
                      </Link>
                    </div>
                    {e.pinyin && <div className="sub">{e.pinyin}</div>}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        <aside className="ws-side">
          <div className="card side-card">
            <p className="side-title">{t("charDna.yourHistory")}</p>
            {m.practice_count === 0 && m.status === "new" && !m.traces ? (
              <p className="sub">{t("charDna.notMetYet")}</p>
            ) : (
              <>
                <div className="sub">{t("charDna.recognition")} · {t(`charDna.status.${m.status}`, { defaultValue: m.status })}</div>
                <Bar value={m.mastery} />
                <div className="sub" style={{ marginTop: 8 }}>{t("charDna.writing")} · {t(`charDna.writingStatus.${m.writing_status}`, { defaultValue: m.writing_status })}</div>
                <Bar value={m.writing_mastery} alt />
                <ul className="scene-rules">
                  {m.first_seen_at && <li>{t("charDna.firstMet", { date: fmtDate(m.first_seen_at, i18n.language) })}</li>}
                  <li>{t("charDna.practiced", { count: m.practice_count })}</li>
                  {m.traces > 0 && <li>{t("charDna.traced", { count: m.traces })}</li>}
                  {m.last_reviewed_at && <li>{t("charDna.lastReviewed", { date: fmtDate(m.last_reviewed_at, i18n.language) })}</li>}
                  {m.next_review_at && (
                    <li>{m.due ? t("charDna.dueNow") : t("charDna.nextReview", { date: fmtDate(m.next_review_at, i18n.language) })}</li>
                  )}
                  {m.words_due > 0 && <li>{t("charDna.wordsDue", { count: m.words_due })}</li>}
                </ul>
              </>
            )}
          </div>

          {m.recent.length > 0 && (
            <div className="card side-card">
              <p className="side-title">{t("charDna.recent")}</p>
              <ul className="recent-list">
                {m.recent.map((r, i) => (
                  <li key={i}>
                    <span className={`badge ${r.correct ? "good" : "bad"}`}>
                      <Icon name={r.correct ? "check" : "x"} size={12} />
                    </span>
                    <b lang="zh-CN">{r.item}</b>
                    <span className="sub">{fmtDate(r.at, i18n.language)}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {(m.mistakes.length > 0 || m.confusions.length > 0) && (
            <div className="card side-card">
              <p className="side-title">{t("charDna.trouble")}</p>
              <ul className="scene-rules">
                {m.mistakes.map((x) => (
                  <li key={`${x.type}-${x.reference}`}>
                    {t(x.mastered ? "charDna.mistakeFixed" : "charDna.mistake", { ref: x.reference, count: x.times })}
                  </li>
                ))}
                {m.confusions.map((c) => (
                  <li key={`${c.item}-${c.with}`}>{t("charDna.confusion", { a: c.item, b: c.with, count: c.times })}</li>
                ))}
              </ul>
              <Link to="/review" className="btn small" style={{ marginTop: 8 }}><Icon name="clock" size={13} /> {t("nav.review")}</Link>
            </div>
          )}

          <div className="card side-card">
            <div className="side-links">
              {data.level && (
                <Link to={`/practice?source=hanzi&level=${data.level}`} className="btn"><Icon name="target" size={15} /> {t("charDna.practiceLevel", { level: data.level })}</Link>
              )}
              <Link to="/hanzi" className="btn ghost">{t("nav.hanzi")}</Link>
            </div>
          </div>
        </aside>
      </div>
    </Layout>
  );
}
