import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api.js";
import Icon from "../components/Icon.jsx";
import FeatureIntro from "../components/FeatureIntro.jsx";
import Layout from "../components/Layout.jsx";
import { Empty, Loading } from "../components/ui.jsx";
import { useApi } from "../hooks/useApi.js";
import { speakChinese } from "../zhSpeech.js";

// One Sentence -> Complete Lesson. The breakdown comes from
// POST /api/sentence/analyze (real curriculum words, characters, grammar,
// the learner's own status for each); the graded activities are a practice
// round (/practice?source=sentence&text=...), so grading stays server-side.

function Hear({ text, label }) {
  return (
    <button type="button" className="btn small ghost" onClick={() => speakChinese(text)} aria-label={label} title={label}>
      <Icon name="ear" size={14} style={{ verticalAlign: -2 }} />
    </button>
  );
}

function StatusBadge({ status }) {
  const { t } = useTranslation();
  if (!status) return null;
  const tone = status === "mastered" ? "good" : status === "new" ? "" : "accent";
  return <span className={`badge ${tone}`}>{t(`sentenceLesson.status.${status}`)}</span>;
}

function FlashCard({ token }) {
  const { t } = useTranslation();
  const [flipped, setFlipped] = useState(false);
  return (
    <button
      type="button"
      className={`card flat flashcard${flipped ? " is-flipped" : ""}`}
      onClick={() => setFlipped((f) => !f)}
      aria-pressed={flipped}
      aria-label={t("sentenceLesson.flip")}
    >
      {flipped ? (
        <>
          <span className="sub">{token.pinyin}</span>
          <span>{token.meaning}</span>
        </>
      ) : (
        <span className="scene-line-zh" lang="zh-CN">{token.text}</span>
      )}
    </button>
  );
}

// The sentence as something to read, not a label: each word sits with its
// pinyin above it and an underline for where the learner stands with it
// (new / learning / mastered, from the analysis); tapping a word says it
// and opens what is known about it right under the line -- its meaning,
// level, the characters it is written with, and "save to review".
function SentenceReader({ analysis, gloss }) {
  const { t } = useTranslation();
  const [sel, setSel] = useState(null);
  const [showPy, setShowPy] = useState(true);
  const [showTr, setShowTr] = useState(true);
  const [saved, setSaved] = useState({});
  const [saveError, setSaveError] = useState("");
  const [playing, setPlaying] = useState(false);
  const tk = sel !== null ? analysis.tokens[sel] : null;
  const charInfo = Object.fromEntries(analysis.characters.map((c) => [c.char, c]));
  const tkChars = tk ? Array.from(tk.text).filter((c) => charInfo[c]) : [];

  function pick(i) {
    setSel(i === sel ? null : i);
    setSaveError("");
    if (i !== sel) speakChinese(analysis.tokens[i].text);
  }

  async function save(id) {
    setSaveError("");
    try {
      await api.post(`/vocab/${id}/track`);
    } catch (err) {
      // 409: already being reviewed or mastered -- it IS in their review.
      if (!/409|already/i.test(err.message)) return setSaveError(err.message);
    }
    setSaved((s) => ({ ...s, [id]: true }));
  }

  const inReview = tk?.word_id && (saved[tk.word_id] || ["learning", "reviewing", "mastered"].includes(tk.status));
  return (
    <section className="card sentence-hero sr" aria-labelledby="sr-title">
      <div className="sr-tools">
        <h2 className="side-title" id="sr-title" style={{ margin: 0 }}>{t("sentenceLesson.readTitle")}</h2>
        <div className="sr-toggles">
          <button type="button" className={`rp-chip${showPy ? " is-on" : ""}`} aria-pressed={showPy} onClick={() => setShowPy((v) => !v)}>
            {t("roleplay.showPinyin")}
          </button>
          <button type="button" className={`rp-chip${showTr ? " is-on" : ""}`} aria-pressed={showTr} onClick={() => setShowTr((v) => !v)}>
            {t("roleplay.showTranslation")}
          </button>
          <button type="button" className={`icon-btn rp-speak${playing ? " is-playing" : ""}`} aria-label={t("companionReact.hear")}
                  title={t("companionReact.hear")}
                  onClick={() => speakChinese(analysis.text, { onStart: () => setPlaying(true), onEnd: () => setPlaying(false) })}>
            <Icon name="volume" size={16} />
          </button>
        </div>
      </div>

      <p className="sr-line" lang="zh-CN">
        {analysis.tokens.map((x, i) =>
          x.kind === "other" ? (
            <span key={i} className="sr-punct">{x.text}</span>
          ) : (
            <button key={i} type="button" className={`sr-word is-${x.status || "unknown"}${sel === i ? " is-open" : ""}${x.above_level ? " is-stretch" : ""}`}
                    onClick={() => pick(i)} aria-pressed={sel === i} aria-label={`${x.text} ${x.pinyin || ""}`}>
              {showPy && <span className="sr-py" aria-hidden="true">{x.pinyin}</span>}
              <span className="sr-zh" aria-hidden="true">{x.text}</span>
            </button>
          )
        )}
      </p>
      {!showPy && <p className="sub sentence-pinyin sr-full-py">{analysis.pinyin}</p>}

      <ul className="sr-legend" aria-label={t("sentenceLesson.legend")}>
        {["new", "learning", "reviewing", "mastered"].map((s) => (
          <li key={s}><i className={`sr-key is-${s}`} aria-hidden="true" /> {t(`sentenceLesson.status.${s}`)}</li>
        ))}
      </ul>

      {tk && (
        <div className="sr-detail" aria-live="polite">
          <div className="sr-detail-head">
            <b className="sr-detail-zh" lang="zh-CN">{tk.text}</b>
            <span className="sr-detail-py">{tk.pinyin}</span>
            <button type="button" className="icon-btn rp-speak" onClick={() => speakChinese(tk.text)} aria-label={t("companionReact.hear")}>
              <Icon name="volume" size={15} />
            </button>
            <button type="button" className="icon-btn nb-close" onClick={() => setSel(null)} aria-label={t("pages.mistakes.focusClose")}>
              <Icon name="x" size={15} />
            </button>
          </div>
          {tk.meaning && <p className="sr-detail-meaning">{tk.meaning}</p>}
          <div className="row" style={{ gap: 6, margin: 0, flexWrap: "wrap" }}>
            {tk.level && <span className="badge">HSK {tk.level}</span>}
            <StatusBadge status={tk.status} />
            {tk.above_level && <span className="badge accent">{t("sentenceLesson.stretch")}</span>}
          </div>
          {tkChars.length > 0 && (
            <div className="dict-chars" style={{ marginTop: 12 }}>
              {tkChars.map((c) => (
                <Link key={c} to={`/hanzi/${encodeURIComponent(c)}`} className="dict-char" lang="zh-CN"
                      aria-label={t("charDna.openFor", { char: c })}>
                  {c} <span className="sub sr-char-py">{charInfo[c].pinyin}</span>
                </Link>
              ))}
            </div>
          )}
          {tk.word_id && (
            <button type="button" className="btn small" style={{ marginTop: 12 }} disabled={inReview} onClick={() => save(tk.word_id)}>
              <Icon name={inReview ? "check" : "bookmark"} size={13} /> {inReview ? t("roleplay.saved") : t("roleplay.save")}
            </button>
          )}
          {saveError && <p className="formerr" role="alert">{saveError}</p>}
        </div>
      )}

      {showTr && (
        <div className="sr-translation">
          <p className="side-title">{t("sentenceLesson.translation")}</p>
          {analysis.translation ? (
            <p>{analysis.translation}</p>
          ) : (
            <p>
              <span className="sub">{t("sentenceLesson.wordByWord")} </span>
              {gloss.join(" · ")}
            </p>
          )}
        </div>
      )}
    </section>
  );
}

export default function SentenceLesson() {
  const { t, i18n } = useTranslation();
  const [params, setParams] = useSearchParams();
  const initial = params.get("text") || "";
  const [text, setText] = useState(initial);
  const [analysis, setAnalysis] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const { data: sug, error: sugError } = useApi("/sentence/suggestions");

  const analyze = useCallback(
    async (value) => {
      const v = (value || "").trim();
      if (!v) return;
      setBusy(true);
      setError("");
      try {
        const a = await api.post("/sentence/analyze", { text: v });
        setAnalysis(a);
        setParams({ text: a.text }, { replace: true });
      } catch (e) {
        setAnalysis(null);
        setError(e.message);
      } finally {
        setBusy(false);
      }
    },
    [setParams]
  );

  // Meanings, grammar titles and the translation follow the UI language.
  useEffect(() => {
    if (initial) analyze(initial);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [i18n.language]);

  const words = analysis ? analysis.tokens.filter((tk) => tk.kind === "word") : [];
  const gloss = analysis
    ? analysis.tokens.filter((tk) => tk.kind !== "other" && tk.meaning).map((tk) => tk.meaning.split(/[;,]/)[0].trim())
    : [];

  return (
    <Layout>
      <header className="page-head">
        <div>
          <div className="page-eyebrow"><Icon name="sparkles" size={13} /> {t("nav.sentence")}</div>
          <h1 className="h1">{t("sentenceLesson.title")}</h1>
          <p className="sub">{t("sentenceLesson.subtitle")}</p>
        </div>
        {analysis && (
          <div className="kpi-row">
            <div className="kpi">
              <span className="kpi-value">{words.length}</span>
              <span className="kpi-label">{t("sentenceLesson.wordsLabel")}</span>
            </div>
            <div className="kpi">
              <span className="kpi-value">{analysis.counts.new}</span>
              <span className="kpi-label">{t("sentenceLesson.newForYou")}</span>
            </div>
          </div>
        )}
      </header>
      <FeatureIntro feature="sentence" />

      <div className="ws">
        <div className="ws-main">
          {/* Once there is a sentence it leads the page; the box to change it follows. */}
          {analysis && <SentenceReader key={`${analysis.text}-${i18n.language}`} analysis={analysis} gloss={gloss} />}

          <form
            className={`card sentence-compose${analysis ? " is-compact" : ""}`}
            onSubmit={(e) => {
              e.preventDefault();
              analyze(text);
            }}
          >
            <div className="field">
              <label htmlFor="sentence-input">{t("sentenceLesson.inputLabel")}</label>
              <input
                id="sentence-input"
                className="input sentence-input"
                lang="zh-CN"
                value={text}
                maxLength={60}
                placeholder={t("sentenceLesson.placeholder")}
                onChange={(e) => setText(e.target.value)}
              />
            </div>
            {error && <p className="formerr">{error}</p>}
            <button type="submit" className="btn primary" disabled={busy || !text.trim()}>
              {busy ? t("sentenceLesson.analyzing") : t("sentenceLesson.analyze")}
            </button>
            <div style={{ marginTop: 16 }}>
              <p className="side-title">{t("sentenceLesson.orPick")}</p>
              {sugError ? (
                <p className="sub">{sugError}</p>
              ) : !sug ? (
                <Loading />
              ) : sug.suggestions.length === 0 ? (
                <p className="sub">{t("sentenceLesson.noSuggestions")}</p>
              ) : (
                <div className="sentence-suggestions">
                  {sug.suggestions.map((s) => (
                    <button
                      key={s.text}
                      type="button"
                      className="btn small ghost sentence-suggestion"
                      onClick={() => {
                        setText(s.text);
                        analyze(s.text);
                      }}
                    >
                      <span lang="zh-CN">{s.text}</span>
                      <span className="sub">{t("sentenceLesson.forWord", { word: s.word.hanzi })}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </form>

          {busy && !analysis && <Loading />}

          {analysis && (
            <>
              <h2 className="h2 section-title">{t("sentenceLesson.vocabulary")}</h2>
              <div className="card">
                <div className="sentence-tokens">
                  {analysis.tokens
                    .filter((tk) => tk.kind !== "other")
                    .map((tk, i) => (
                      <div key={i} className={`sentence-token${tk.above_level ? " is-stretch" : ""}`}>
                        <div className="row spread" style={{ margin: 0 }}>
                          <span className="scene-line-zh" lang="zh-CN">{tk.text}</span>
                          <Hear text={tk.text} label={t("companionReact.hear")} />
                        </div>
                        <div className="sub">{tk.pinyin}</div>
                        <div className="sentence-token-meaning">{tk.meaning}</div>
                        <div className="row" style={{ gap: 6, margin: "8px 0 0", flexWrap: "wrap" }}>
                          {tk.level && <span className="badge">HSK {tk.level}</span>}
                          <StatusBadge status={tk.status} />
                          {tk.above_level && <span className="badge accent">{t("sentenceLesson.stretch")}</span>}
                        </div>
                      </div>
                    ))}
                </div>
              </div>

              <h2 className="h2 section-title">{t("sentenceLesson.characters")}</h2>
              <div className="grid cards">
                {analysis.characters.map((c) => (
                  <div key={c.char} className="card flat sentence-char">
                    <div className="row spread" style={{ margin: 0 }}>
                      <Link to={`/hanzi/${encodeURIComponent(c.char)}`} className="sentence-char-glyph" lang="zh-CN"
                            aria-label={t("charDna.openFor", { char: c.char })}>{c.char}</Link>
                      <StatusBadge status={c.status} />
                    </div>
                    <div className="sub">{c.pinyin} · {c.meaning}</div>
                    <div className="sub">
                      {c.radical && t("sentenceLesson.radical", { radical: c.radical })}
                      {c.stroke_count ? ` · ${t("sentenceLesson.strokes", { count: c.stroke_count })}` : ""}
                    </div>
                  </div>
                ))}
              </div>

              <h2 className="h2 section-title">{t("sentenceLesson.grammar")}</h2>
              {analysis.grammar.length === 0 ? (
                <Empty>{t("sentenceLesson.noGrammar")}</Empty>
              ) : (
                <div className="col">
                  {analysis.grammar.map((g) => (
                    <div key={g.id} className="card flat">
                      <div className="row spread" style={{ margin: 0, flexWrap: "wrap" }}>
                        <b>{g.title}</b>
                        <div className="row" style={{ gap: 6, margin: 0 }}>
                          {g.level && <span className="badge">HSK {g.level}</span>}
                          {g.above_level && <span className="badge accent">{t("sentenceLesson.stretch")}</span>}
                        </div>
                      </div>
                      {g.pattern && <div className="sub" lang="zh-CN">{g.pattern}</div>}
                      {g.explanation && <p className="sub" style={{ marginTop: 8 }}>{g.explanation}</p>}
                    </div>
                  ))}
                </div>
              )}

              <h2 className="h2 section-title">{t("sentenceLesson.flashcards")}</h2>
              <p className="sub">{t("sentenceLesson.flashcardsHint")}</p>
              <div className="flashcards">
                {words.map((w, i) => (
                  <FlashCard key={`${w.text}-${i}`} token={w} />
                ))}
              </div>
            </>
          )}
        </div>

        <aside className="ws-side">
          {analysis ? (
            <>
              <div className="card side-card">
                <p className="side-title">{t("sentenceLesson.forYourLevel")}</p>
                <span className={`badge ${analysis.level.fit === "above" ? "accent" : "good"}`}>
                  {t(`sentenceLesson.fit.${analysis.level.fit}`, { level: analysis.level.user })}
                </span>
                <p className="sub" style={{ marginTop: 8 }}>
                  {t("sentenceLesson.countsLine", {
                    fresh: analysis.counts.new,
                    learning: analysis.counts.learning,
                    mastered: analysis.counts.mastered,
                  })}
                </p>
              </div>
              <div className="card side-card">
                <p className="side-title">{t("sentenceLesson.practiceTitle")}</p>
                <ul className="scene-rules">
                  <li>{t("sentenceLesson.activity.vocab")}</li>
                  <li>{t("sentenceLesson.activity.characters")}</li>
                  <li>{t("sentenceLesson.activity.listening")}</li>
                  <li>{t("sentenceLesson.activity.order")}</li>
                  <li>{t("sentenceLesson.activity.reading")}</li>
                  <li>{t("sentenceLesson.activity.speaking")}</li>
                </ul>
                <Link
                  to={`/practice?source=sentence&text=${encodeURIComponent(analysis.text)}`}
                  className="btn primary"
                  style={{ marginTop: 12 }}
                >
                  <Icon name="play" size={15} /> {t("sentenceLesson.start")}
                </Link>
                <p className="sub" style={{ marginTop: 8 }}>{t("sentenceLesson.reviewNote")}</p>
              </div>
            </>
          ) : (
            <div className="card side-card">
              <p className="side-title">{t("sentenceLesson.howTitle")}</p>
              <p className="sub">{t("sentenceLesson.how")}</p>
            </div>
          )}
        </aside>
      </div>
    </Layout>
  );
}
