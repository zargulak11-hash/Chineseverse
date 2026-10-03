import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { useDashboard } from "../context/DashboardContext.jsx";
import { speakChinese } from "../zhSpeech.js";
import Icon from "./Icon.jsx";
import { GlossList } from "./CaseAndSound.jsx";
import { Loading } from "./ui.jsx";

// Help with one word met in real Chinese (GET /api/internet/words/:id):
// meaning, reading, what the learner's own data says about it, the
// sentence it came from, its characters and related words. "Add to review"
// is offered only for a word that isn't already on their schedule (the
// server refuses duplicates too) -- a mastered or scheduled word is left
// alone, and mastery is never touched here.

const LOCALE = { en: "en-US", ru: "ru-RU", tg: "tg-TJ", zh: "zh-CN" };

export default function WordHelper({ wordId, item, version, onClose }) {
  const { t, i18n } = useTranslation();
  const { refresh } = useDashboard() || {};
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setData(null);
    setError("");
    api
      .get(`/internet/words/${wordId}${item ? `?item=${encodeURIComponent(item)}${version ? `&version=${version}` : ""}` : ""}`)
      .then((d) => !cancelled && setData(d))
      .catch((e) => !cancelled && setError(e.message));
    return () => {
      cancelled = true;
    };
  }, [wordId, item, version, i18n.language]);

  async function add() {
    setBusy(true);
    setError("");
    try {
      const r = await api.post(`/vocab/${wordId}/track`);
      setData((d) => ({ ...d, can_add: false, add_reason: "added", state: { ...d.state, status: r.status, next_review_at: r.next_review_at } }));
      refresh?.(); // the Review count in the sidebar changed
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  if (error && !data) return <p className="formerr">{error}</p>;
  if (!data) return <Loading />;

  const s = data.state;
  const stateKey = s.due ? "due" : s.status;
  const next = s.next_review_at
    ? new Intl.DateTimeFormat(LOCALE[i18n.language] || "en-US", { dateStyle: "medium" }).format(new Date(s.next_review_at))
    : null;
  return (
    <div className="word-helper" aria-live="polite">
      <div className="row spread" style={{ margin: 0 }}>
        <div className="row" style={{ margin: 0, gap: 8, alignItems: "center" }}>
          <span className="sentence-text" lang="zh-CN">{data.text}</span>
          <button type="button" className="btn small ghost" onClick={() => speakChinese(data.text)}
                  aria-label={t("companionReact.hear")} title={t("companionReact.hear")}>
            <Icon name="ear" size={14} />
          </button>
        </div>
        {onClose && (
          <button type="button" className="icon-btn" onClick={onClose} aria-label={t("pages.hanzi.close")}>
            <Icon name="x" size={15} />
          </button>
        )}
      </div>
      <div className="sub">{data.pinyin}</div>
      <p style={{ margin: "8px 0 0" }}>{data.meaning}</p>
      <div className="row" style={{ gap: 6, flexWrap: "wrap", margin: "8px 0 0" }}>
        {data.level && <span className="badge">HSK {data.level}</span>}
        {data.above_level && <span className="badge accent">{t("sentenceLesson.stretch")}</span>}
        <span className={`badge ${stateKey === "mastered" ? "good" : stateKey === "due" ? "accent" : ""}`}>
          {t(`charDna.status.${stateKey}`, { defaultValue: stateKey })}
        </span>
        {s.open_mistakes > 0 && <span className="badge bad">{t("internet.helper.missed", { count: s.open_mistakes })}</span>}
      </div>

      <p className="sub" style={{ marginTop: 12 }}>
        {data.add_reason === "mastered"
          ? t("internet.helper.mastered")
          : data.add_reason === "in_review"
            ? t("internet.helper.inReview", { date: next || "—" })
            : data.add_reason === "added"
              ? t("internet.helper.added")
              : t("internet.helper.notYet")}
      </p>
      {data.can_add && (
        <button type="button" className="btn small primary" onClick={add} disabled={busy}>
          <Icon name="clock" size={13} /> {busy ? t("internet.helper.adding") : t("internet.helper.add")}
        </button>
      )}
      {error && <p className="formerr">{error}</p>}

      {data.context && (
        <div style={{ marginTop: 16 }}>
          <p className="side-title">{t("internet.helper.context")}</p>
          <span lang="zh-CN">{data.context.text}</span>
          <GlossList gloss={data.context.gloss} />
        </div>
      )}

      {data.characters.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <p className="side-title">{t("ecosystem.itsCharacters")}</p>
          <div className="chip-row">
            {data.characters.map((c) =>
              c.has_dna ? (
                <Link key={c.char} to={`/hanzi/${encodeURIComponent(c.char)}`} className="char-chip">
                  <b lang="zh-CN">{c.char}</b>
                  <span className="sub">{c.pinyin}</span>
                  {c.meaning && <span className="char-chip-meaning">{c.meaning}</span>}
                </Link>
              ) : (
                <span key={c.char} className="char-chip"><b lang="zh-CN">{c.char}</b></span>
              )
            )}
          </div>
        </div>
      )}

      {data.related.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <p className="side-title">{t("internet.helper.related")}</p>
          <ul className="scene-rules">
            {data.related.map((r) => (
              <li key={r.id}>
                <b lang="zh-CN">{r.text}</b> <span className="sub">{r.pinyin}</span> — {r.meaning}
              </li>
            ))}
          </ul>
        </div>
      )}

      <p className="sub" style={{ marginTop: 16 }}>
        {t("internet.helper.dna", { vocabulary: Math.round(data.dna.vocabulary), reading: Math.round(data.dna.reading) })}{" "}
        <Link to="/dna">{t("dashboard.fullDna")}</Link>
      </p>
    </div>
  );
}
