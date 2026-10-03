import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { useDashboard } from "../context/DashboardContext.jsx";
import { speakChinese } from "../zhSpeech.js";
import Icon from "./Icon.jsx";
import WordHelper from "./WordHelper.jsx";
import { Loading } from "./ui.jsx";

// Help while reading a Chinese Stories chapter. A side panel on wide
// screens, a bottom sheet on phones (CSS decides; same element).
//
//   word   a tapped word: the curriculum's own entry (WordHelper -- meaning,
//          characters, "add to review"), plus its sentence to explain/hear.
//   text   a selected sentence or passage: POST /stories/:slug/explain.
//          Pinyin, word-by-word, grammar and (for whole sentences) the
//          book's translation come from ChineseVerse's own data; the AI
//          explanation is only requested for "explain"/"grammar" (or the
//          "Explain with AI" button), and its absence never empties the panel.

export const HELP_ACTIONS = ["explain", "pinyin", "translate", "words", "grammar"];

function Words({ words }) {
  const { t } = useTranslation();
  return (
    <ul className="help-words">
      {words.map((w, i) => (
        <li key={`${w.text}-${i}`}>
          <b lang="zh-CN">{w.text}</b>
          <span className="help-py">{w.pinyin}</span>
          <span className="help-meaning">{w.name ? t("stories.help.name") : w.meaning || "—"}</span>
          {w.level ? <span className="badge">HSK {w.level}</span> : null}
        </li>
      ))}
    </ul>
  );
}

function TextHelp({ slug, chapter, text, focus, onListen }) {
  const { t, i18n } = useTranslation();
  const { refresh } = useDashboard() || {};
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [ask, setAsk] = useState(focus);
  const [saved, setSaved] = useState(null);

  useEffect(() => setAsk(focus), [focus, text]);
  useEffect(() => {
    let cancelled = false;
    setData(null);
    setError("");
    setSaved(null);
    api.post(`/stories/${slug}/explain`, { chapter, text, focus: ask })
      .then((d) => !cancelled && setData(d))
      .catch((e) => !cancelled && setError(e.message));
    return () => {
      cancelled = true;
    };
  }, [slug, chapter, text, ask, i18n.language]);

  async function saveWords() {
    const fresh = [...new Map(data.words.filter((w) => w.word_id && w.state === "new").map((w) => [w.word_id, w])).values()];
    let added = 0;
    for (const w of fresh) {
      try {
        await api.post(`/vocab/${w.word_id}/track`);
        added += 1;
      } catch {
        // already scheduled or not trackable: the server decides
      }
    }
    setSaved(added);
    if (added) refresh?.();
  }

  if (error) return <p className="formerr">{error}</p>;
  if (!data) return <Loading>{t("stories.help.loading")}</Loading>;
  const tr = data.translation;
  const newWords = data.words.some((w) => w.word_id && w.state === "new");
  return (
    <div className="help-body">
      <p className="help-zh" lang="zh-CN">{data.text}</p>
      <p className="help-pinyin">{data.pinyin}</p>

      {i18n.language !== "zh" && (tr.text ? (
        <section className="help-section">
          <h3 className="help-h">{t("stories.help.translation")} <span className="badge">{t(tr.source === "book" ? "stories.help.fromBook" : "stories.help.fromAi")}</span></h3>
          <p>{tr.text}</p>
        </section>
      ) : (ask === "translate" || ask === "explain") && (
        <p className="sub">{t("stories.help.noTranslation")}</p>
      ))}

      {data.ai && (
        <section className="help-section help-ai">
          {data.ai.meaning && (<><h3 className="help-h">{t("stories.help.meaning")}</h3><p>{data.ai.meaning}</p></>)}
          {data.ai.points?.length > 0 && (
            <>
              <h3 className="help-h">{t("stories.help.points")}</h3>
              <ul className="help-points">
                {data.ai.points.map((p, i) => <li key={i}><b>{p.title}</b> — {p.body}</li>)}
              </ul>
            </>
          )}
          {data.ai.example && (
            <>
              <h3 className="help-h">{t("stories.help.example")}</h3>
              <p lang="zh-CN">{data.ai.example.zh}</p>
              {data.ai.example.translation && <p className="sub">{data.ai.example.translation}</p>}
            </>
          )}
          <p className="help-note">{t("stories.help.aiNote")}</p>
        </section>
      )}
      {!data.ai && (data.ai_status === "offline" || data.ai_status === "limit") && (
        <p className="sub help-note">{t(data.ai_status === "limit" ? "stories.help.aiLimit" : "stories.help.aiOffline")}</p>
      )}

      <section className="help-section">
        <h3 className="help-h">{t("stories.help.wordList")}</h3>
        <Words words={data.words} />
      </section>

      {data.grammar.length > 0 && (
        <section className="help-section">
          <h3 className="help-h">{t("stories.help.grammarApp")}</h3>
          <ul className="help-points">
            {data.grammar.map((g, i) => (
              <li key={i}><b>{g.title}</b>{g.pattern ? <span className="sub"> · {g.pattern}</span> : null}{g.level ? <span className="badge" style={{ marginLeft: 6 }}>HSK {g.level}</span> : null}
                {g.explanation && <p className="sub">{g.explanation}</p>}
              </li>
            ))}
          </ul>
        </section>
      )}

      <div className="row help-actions">
        <button type="button" className="btn small" onClick={() => onListen(data.text)}>
          <Icon name="ear" size={13} /> {t("stories.help.listen")}
        </button>
        {!data.ai && ask !== "explain" && data.ai_status !== "limit" && (
          <button type="button" className="btn small" onClick={() => setAsk("explain")}>
            <Icon name="sparkles" size={13} /> {t("stories.help.askAi")}
          </button>
        )}
        {newWords && saved === null && (
          <button type="button" className="btn small" onClick={saveWords}>
            <Icon name="plus" size={13} /> {t("stories.help.save")}
          </button>
        )}
        <Link to={`/practice?source=story&story=${slug}&chapter=${chapter}`} className="btn small ghost">
          {t("stories.help.practice")}
        </Link>
      </div>
      {saved !== null && <p className="sub" role="status">{t("stories.help.saved", { count: saved })}</p>}
    </div>
  );
}

export default function ReadingHelp({ slug, chapter, help, rate, onClose, onExplain }) {
  const { t } = useTranslation();
  if (!help) return null;

  function listen(text) {
    speakChinese(text, { profile: { rate, pitch: 1, volume: 1 }, whole: true });
    api.post(`/stories/${slug}/listen`, { chapter }).catch(() => {});
  }

  return (
    <aside className="card read-help" aria-label={t("stories.help.title")}>
      <div className="row spread read-help-head">
        <p className="side-title">{t("stories.help.title")}</p>
        <button type="button" className="icon-btn" aria-label={t("stories.help.close")} onClick={onClose}>
          <Icon name="x" size={16} />
        </button>
      </div>
      <div className="read-help-scroll">
        {help.mode === "word" ? (
          <>
            {/* The panel has its own close button; no second one inside. */}
            <WordHelper wordId={help.wordId} />
            {help.sentence && (
              <section className="help-section">
                <h3 className="help-h">{t("stories.help.sentence")}</h3>
                <p className="help-zh-sm" lang="zh-CN">{help.sentence}</p>
                <div className="row help-actions">
                  <button type="button" className="btn small primary" onClick={() => onExplain(help.sentence, "explain")}>
                    <Icon name="sparkles" size={13} /> {t("stories.help.explainSentence")}
                  </button>
                  <button type="button" className="btn small" onClick={() => listen(help.sentence)}>
                    <Icon name="ear" size={13} /> {t("stories.help.listen")}
                  </button>
                </div>
              </section>
            )}
          </>
        ) : (
          <TextHelp slug={slug} chapter={chapter} text={help.text} focus={help.focus} onListen={listen} />
        )}
      </div>
    </aside>
  );
}
