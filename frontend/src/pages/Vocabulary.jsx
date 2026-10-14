import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import Layout from "../components/Layout.jsx";
import { Bar, Empty, Loading } from "../components/ui.jsx";
import { useApi } from "../hooks/useApi.js";
import { speakChinese } from "../zhSpeech.js";
import Icon from "../components/Icon.jsx";

// The vocabulary of one HSK level as a dictionary: search first, a dense
// list of entries, and one entry open beside it with everything the API
// really has for that word -- its example sentence, the characters it is
// written with (each a door to that character's page), other words of the
// level that share a character, and where the learner stands with it.
// Mastery is earned in the graded practice round (/practice), never here;
// "save to review" only puts the word on the review schedule.

// Tone marks and spacing never decide a match: "nihao", "ni3hao3" and
// "nǐ hǎo" all find 你好.
function fold(s) {
  return String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/ü/g, "v")
    .replace(/[\s\d'·-]+/g, "").toLowerCase();
}
const CJK = /[㐀-鿿]/;

function statusKey(w) {
  if (w.due_for_review) return w.slipping ? "slipping" : "due";
  return w.status || "new";
}

export default function Vocabulary() {
  const { t } = useTranslation();
  const [level, setLevel] = useState(1);
  const { data, error } = useApi(`/vocab?hsk_level=${level}`);
  const { data: roadmap } = useApi("/hsk/roadmap");
  const words = data || [];
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState(null);
  const [playing, setPlaying] = useState(null);
  const [saved, setSaved] = useState({});
  const [saveError, setSaveError] = useState("");
  const entryRef = useRef(null);

  // A new level starts from its first (most due) word.
  useEffect(() => {
    setSelectedId(null);
    setQuery("");
  }, [level]);

  const found = useMemo(() => {
    const q = query.trim();
    if (!q) return words;
    const fq = fold(q);
    return words.filter((w) =>
      (CJK.test(q) && ((w.simplified || "").includes(q) || (w.traditional || "").includes(q))) ||
      (fq && fold(w.pinyin).includes(fq)) ||
      (w.meanings || "").toLowerCase().includes(q.toLowerCase()));
  }, [words, query]);

  // Clicking an entry only plays it: mastery is earned in the graded
  // practice round (/practice), never by clicking a card.
  function hear(text, id) {
    speakChinese(text, {
      onStart: () => setPlaying(id),
      onEnd: () => setPlaying(null),
    });
  }

  function open(w) {
    setSelectedId(w.id);
    hear(w.simplified, w.id);
    // On a phone the entry sits above the list: bring it into view.
    if (window.matchMedia?.("(max-width: 1080px)").matches) entryRef.current?.scrollIntoView?.({ behavior: "smooth", block: "start" });
  }

  async function save(w) {
    setSaveError("");
    try {
      await api.post(`/vocab/${w.id}/track`);
    } catch (err) {
      // 409: already being reviewed or mastered -- it IS in their review.
      if (!/409|already/i.test(err.message)) return setSaveError(err.message);
    }
    setSaved((s) => ({ ...s, [w.id]: true }));
  }

  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  if (!data) return <Layout><Loading /></Layout>;

  const counts = {};
  for (const lv of roadmap?.levels || []) counts[lv.level] = lv.vocab_total;
  const due = words.filter((w) => w.due_for_review);
  const slipping = words.filter((w) => w.slipping);
  const known = words.filter((w) => w.status === "reviewing" || w.status === "mastered").length;
  const sel = words.find((w) => w.id === selectedId) || found[0] || null;
  const chars = sel ? Array.from(new Set(Array.from(sel.simplified).filter((c) => CJK.test(c)))) : [];
  // Other words of this level written with one of the same characters.
  const related = sel ? words.filter((w) => w.id !== sel.id && chars.some((c) => w.simplified.includes(c))).slice(0, 12) : [];
  const inReview = sel && (saved[sel.id] || ["learning", "reviewing", "mastered"].includes(sel.status));

  return (
    <Layout>
      <header className="page-head">
        <div>
          <div className="page-eyebrow"><Icon name="book" size={13} /> HSK {level}</div>
          <h1 className="h1">{t("pages.vocabulary.title")}</h1>
          <p className="sub">{t("pages.vocabulary.subtitle")}</p>
        </div>
        <div className="kpi-row">
          <div className="kpi"><span className="kpi-value">{words.length}</span><span className="kpi-label">{t("pages.vocabulary.kpiWords")}</span></div>
          <div className="kpi"><span className="kpi-value">{known}</span><span className="kpi-label">{t("pages.vocabulary.kpiKnown")}</span></div>
          <div className="kpi"><span className="kpi-value">{due.length}</span><span className="kpi-label">{t("pages.vocabulary.due")}</span></div>
        </div>
      </header>

      <div className="dict-bar">
        <label className="dict-search">
          <Icon name="search" size={18} />
          <input
            className="input"
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t("pages.vocabulary.searchPlaceholder")}
            aria-label={t("pages.vocabulary.searchLabel", { level })}
          />
        </label>
        <div className="dict-levels" role="group" aria-label={t("pages.vocabulary.levelLabel")}>
          {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((lv) => (
            <button
              key={lv}
              type="button"
              className={`btn small${level === lv ? " primary" : " ghost"}`}
              aria-pressed={level === lv}
              onClick={() => setLevel(lv)}
            >
              HSK {lv} {counts[lv] > 0 ? <span className="dict-level-n">{counts[lv]}</span> : ""}
            </button>
          ))}
        </div>
      </div>

      {words.length > 0 && (
        <div className="dict-meta">
          <Link to={`/practice?source=vocab&level=${level}`} className="btn primary">{t("practice.startLevel", { level })}</Link>
          {due.length > 0 && (
            <span className="sub">
              <Icon name="clock" size={13} style={{ verticalAlign: -2 }} /> {t("pages.vocabulary.dueForReview", { count: due.length })}
              {slipping.length > 0 && <> · {t("pages.vocabulary.slippingCount", { count: slipping.length })}</>}
            </span>
          )}
        </div>
      )}

      {words.length === 0 ? (
        <Empty>{t("pages.vocabulary.empty")}</Empty>
      ) : (
        <div className="dict">
          <section className="card dict-list" aria-label={t("pages.vocabulary.listLabel")}>
            <p className="dict-list-head sub" aria-live="polite">
              {query.trim() ? t("pages.vocabulary.found", { count: found.length }) : t("pages.vocabulary.tapToHear")}
            </p>
            {found.length === 0 ? (
              <p className="sub dict-none">{t("pages.vocabulary.noMatch")}</p>
            ) : (
              <ul>
                {found.map((w) => {
                  const st = statusKey(w);
                  return (
                    <li key={w.id}>
                      <button type="button" className={`dict-row${sel?.id === w.id ? " is-open" : ""}`}
                              onClick={() => open(w)} aria-pressed={sel?.id === w.id}>
                        <span className="dict-row-zh" lang="zh-CN">{w.simplified}</span>
                        <span className="dict-row-py">{w.pinyin}</span>
                        <span className="dict-row-meaning">{w.meanings}</span>
                        <span className={`dict-dot is-${st}`} title={t(`pages.vocabulary.st_${st}`, { defaultValue: st })} aria-hidden="true" />
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </section>

          <div className="dict-entry-wrap" ref={entryRef}>
            {sel && (
              <article className="card dict-entry" aria-labelledby="dict-word" key={sel.id}>
                <div className="dict-head">
                  <div className="dict-head-word">
                    <h2 className="dict-word" id="dict-word" lang="zh-CN">{sel.simplified}</h2>
                    {sel.traditional && sel.traditional !== sel.simplified && (
                      <span className="dict-trad" lang="zh-TW">{t("pages.vocabulary.traditional")}: {sel.traditional}</span>
                    )}
                  </div>
                  <button type="button" className={`dict-say${playing === sel.id ? " is-playing" : ""}`}
                          onClick={() => hear(sel.simplified, sel.id)} aria-label={t("pages.mistakes.listen")}>
                    <Icon name="volume" size={22} />
                  </button>
                </div>
                <p className="dict-py">{sel.pinyin}</p>
                <div className="dict-tags">
                  {sel.word_type && (
                    <span className="ilb">
                      {/* English part-of-speech labels are UI text; raw dictionary
                          POS codes (r, g, nz, ...) have no translation and show as-is. */}
                      {t(`wordType.${sel.word_type.replace(/[\s-]+/g, "_")}`, { defaultValue: sel.word_type })}
                    </span>
                  )}
                  {sel.due_for_review && (
                    <span className={`badge ${sel.slipping ? "bad" : "accent"}`}>
                      {t(sel.slipping ? "pages.vocabulary.slipping" : "pages.vocabulary.due")}
                    </span>
                  )}
                </div>
                <p className="dict-meaning">{sel.meanings}</p>

                {sel.example && (
                  <section className="dict-block">
                    <p className="side-title">{t("pages.vocabulary.example")}</p>
                    <div className="dict-example">
                      <div>
                        <p className="dict-ex-zh" lang="zh-CN">{sel.example}</p>
                        {sel.example_pinyin && <p className="dict-ex-py">{sel.example_pinyin}</p>}
                      </div>
                      <button type="button" className={`icon-btn dict-ex-say${playing === `ex${sel.id}` ? " is-playing" : ""}`}
                              onClick={() => hear(sel.example, `ex${sel.id}`)} aria-label={t("pages.mistakes.listen")}>
                        <Icon name="volume" size={16} />
                      </button>
                    </div>
                  </section>
                )}

                {chars.length > 0 && (
                  <section className="dict-block">
                    <p className="side-title">{t("pages.vocabulary.characters")}</p>
                    <div className="dict-chars">
                      {chars.map((c) => (
                        <Link key={c} to={`/hanzi/${encodeURIComponent(c)}`} className="dict-char" lang="zh-CN"
                              aria-label={t("pages.vocabulary.openChar", { char: c })}>
                          {c}
                          <Icon name="arrowRight" size={13} />
                        </Link>
                      ))}
                    </div>
                  </section>
                )}

                {related.length > 0 && (
                  <section className="dict-block">
                    <p className="side-title">{t("pages.vocabulary.related")}</p>
                    <div className="dict-related">
                      {related.map((w) => (
                        <button key={w.id} type="button" className="dict-rel" onClick={() => open(w)}>
                          <b lang="zh-CN">{w.simplified}</b> <span className="sub">{w.pinyin}</span>
                        </button>
                      ))}
                    </div>
                  </section>
                )}

                <section className="dict-block dict-me">
                  <div className="row spread" style={{ margin: 0 }}>
                    <p className="side-title" style={{ margin: 0 }}>{t("pages.vocabulary.yourMastery")}</p>
                    <span className="sub">{Math.round(sel.mastery ?? 0)}% · {t(`pages.vocabulary.st_${statusKey(sel)}`, { defaultValue: statusKey(sel) })}</span>
                  </div>
                  <Bar value={sel.mastery ?? 0} alt />
                  {/* A full bar from choosing alone: it isn't mastered until it is
                      produced from memory (services/srs.py). */}
                  {(sel.status === "reviewing" || sel.status === "mastered") && !sel.recalled && (
                    <span className="sub word-recall-pending">{t("pages.vocabulary.recallPending")}</span>
                  )}
                </section>

                <div className="dict-actions">
                  <button type="button" className="btn" disabled={inReview} onClick={() => save(sel)}>
                    <Icon name={inReview ? "check" : "bookmark"} size={15} /> {inReview ? t("roleplay.saved") : t("roleplay.save")}
                  </button>
                  <Link to={`/practice?source=vocab&level=${level}`} className="btn ghost">{t("practice.startLevel", { level })}</Link>
                </div>
                {saveError && <p className="formerr" role="alert">{saveError}</p>}
              </article>
            )}
          </div>
        </div>
      )}
    </Layout>
  );
}
