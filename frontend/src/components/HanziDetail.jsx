import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { useDashboard } from "../context/DashboardContext.jsx";
import CompanionReaction from "./CompanionReaction.jsx";
import { Bar, useBackdropClose } from "./ui.jsx";
import Icon from "./Icon.jsx";
import HanziTrace from "./HanziTrace.jsx";
import { speakChinese } from "../zhSpeech.js";
import { formatDate } from "../dates.js";

// The full "SEE -> pronunciation -> hear -> meaning -> examples -> progress"
// hub for one character. Writing practice (watch stroke order -> try
// writing -> validate -> save) is launched from here but stays its own
// component (HanziTrace) since it already owns that whole flow end to end
// -- this view is the overview/reference screen around it, not a second
// writing implementation.
//
// `inline` (the Hanzi page) renders the same card docked in the page beside
// the character table instead of over a backdrop; everything in it is the same.
export default function HanziDetail({ hanzi, level, onClose, onUpdated, inline = false }) {
  const { t, i18n } = useTranslation();
  const [current, setCurrent] = useState(hanzi);
  const [examples, setExamples] = useState(null);
  const [examplesError, setExamplesError] = useState(null);
  const [tracing, setTracing] = useState(false);
  const [reviewing, setReviewing] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  // The permanent companion's reaction to the last real self-check or
  // completed trace on this character (server-decided, see the API).
  const [reaction, setReaction] = useState(null);
  const [notDue, setNotDue] = useState(null);
  const { dashboard, refresh } = useDashboard() || {};

  useEffect(() => {
    setCurrent(hanzi);
    setExamples(null);
    setExamplesError(null);
    setReaction(null);
    setNotDue(null);
    api
      .get(`/hanzi/${hanzi.id}/examples`)
      .then(setExamples)
      .catch((e) => setExamplesError(e.message));
  }, [hanzi.id]);

  function hear() {
    speakChinese(current.character, {
      onStart: () => setSpeaking(true),
      onEnd: () => setSpeaking(false),
    });
  }

  async function review(correct) {
    if (reviewing) return;
    setReviewing(true);
    try {
      const res = await api.post(`/hanzi/${current.id}/review`, { correct });
      const updated = { ...current, mastery: res.mastery, status: res.status };
      setCurrent(updated);
      onUpdated?.(updated);
      setReaction(res.reaction || null);
      // An early "got it" is recorded as a visit only (the server's schedule
      // decides when a self-check counts) -- say so instead of looking broken.
      setNotDue(res.counted === false ? res.next_review_at : null);
      refresh?.(); // XP/streak/DNA changed
    } catch {
      // stays on-screen; the button simply re-enables for another try
    } finally {
      setReviewing(false);
    }
  }

  const Wrap = inline ? InlineWrap : ModalWrap;
  return (
    <Wrap onClose={onClose}>
        {/* SEE + PRONUNCIATION + HEAR */}
        <div style={{ textAlign: "center" }}>
          <div className="hz-detail-char" lang="zh-CN">{current.character}</div>
          <div className="row" style={{ justifyContent: "center", gap: 8, marginTop: 6 }}>
            <span className="sub" style={{ color: "var(--accent2)", fontSize: 18 }}>{current.pinyin}</span>
            <button
              type="button"
              className="btn small ghost"
              onClick={hear}
              disabled={speaking}
              aria-label={t("pages.hanzi.hear")}
              title={t("pages.hanzi.hear")}
            >
              <Icon name="volume" size={14} style={{ verticalAlign: -2, marginRight: 4 }} />
              {t("pages.hanzi.hear")}
            </button>
          </div>
        </div>

        {/* MEANING + HSK + STROKE COUNT */}
        <div className="statsrow" style={{ justifyContent: "center", marginTop: 12 }}>
          {current.meaning && <span className="statpill">{current.meaning}</span>}
          {level != null && <span className="statpill">HSK {level}</span>}
          {current.stroke_count != null && (
            <span className="statpill">{t("pages.hanzi.strokes", { count: current.stroke_count })}</span>
          )}
          {current.handwriting_tier && <span className="statpill">{t("pages.hanzi.handwriting")}</span>}
        </div>
        <div style={{ textAlign: "center", marginTop: 12 }}>
          <Link to={`/hanzi/${encodeURIComponent(current.character)}`} className="btn small">
            <Icon name="dna" size={13} /> {t("charDna.open")}
          </Link>
        </div>

        {/* PROGRESS */}
        <div style={{ marginTop: 16 }}>
          <div className="row spread">
            <span className="sub" style={{ fontSize: 12 }}>{t("pages.hanzi.recognitionProgress")}</span>
            <span className="sub" style={{ fontSize: 12 }}>{Math.round(current.mastery ?? 0)}%</span>
          </div>
          <Bar value={current.mastery ?? 0} alt />
          {current.handwriting_tier && (
            <>
              <div className="row spread" style={{ marginTop: 8 }}>
                <span className="sub" style={{ fontSize: 12 }}>{t("pages.hanzi.writingProgress")}</span>
                <span className="sub" style={{ fontSize: 12 }}>{Math.round(current.writing_mastery ?? 0)}%</span>
              </div>
              <Bar value={current.writing_mastery ?? 0} />
            </>
          )}
        </div>

        {/* Recognition self-report — genuine engagement (opened the detail,
            saw the pronunciation/meaning/examples) rather than a single
            accidental click on a list card. */}
        <div className="row" style={{ marginTop: 12, justifyContent: "center" }}>
          <button className="btn small ghost" onClick={() => review(false)} disabled={reviewing}>
            {t("pages.hanzi.stillLearning")}
          </button>
          <button className="btn small primary" onClick={() => review(true)} disabled={reviewing}>
            {t("pages.hanzi.gotIt")}
          </button>
        </div>

        {notDue && (
          <p className="sub" role="status" style={{ textAlign: "center", marginTop: 8, fontSize: "var(--text-xs)" }}>
            {t("pages.hanzi.notDueYet", {
              date: formatDate(notDue, i18n.language),
            })}
          </p>
        )}

        {reaction && (
          <CompanionReaction animal={dashboard?.animal} reaction={reaction} context="hanzi" compact size={60} focusMode="none" settleAfter={9000} />
        )}

        {/* WRITE entry point (real stroke data required, gated to the
            characters the real HSK 3.0 syllabus requires handwriting for) */}
        {current.handwriting_tier && (
          <>
            <div className="row" style={{ marginTop: 10, gap: 8, flexWrap: "wrap" }}>
              <button type="button" className="btn small ghost" style={{ flex: "1 1 140px" }} onClick={() => setTracing("trace")}>
                {t("pages.hanzi.practiceWriting")}
              </button>
              <button type="button" className="btn small" style={{ flex: "1 1 140px" }} onClick={() => setTracing("memory")}>
                {t("pages.hanzi.writeFromMemory")}
              </button>
            </div>
            <p className="sub" style={{ marginTop: 6, fontSize: "var(--text-xs)" }}>
              {t("pages.hanzi.memoryCount", { count: current.times_written_memory ?? 0 })} · {t("pages.hanzi.memoryWhy")}
            </p>
          </>
        )}

        {/* EXAMPLES */}
        <div style={{ marginTop: 16 }}>
          <h3 className="h3" style={{ fontSize: 14 }}>{t("pages.hanzi.examples")}</h3>
          {examples === null && !examplesError && <p className="sub">…</p>}
          {examplesError && <p className="sub">{examplesError}</p>}
          {examples && examples.length === 0 && <p className="sub">{t("pages.hanzi.noExamples")}</p>}
          {examples && examples.length > 0 && (
            <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 6 }}>
              {examples.map((w) => (
                <div key={w.id} className="row spread" style={{ fontSize: 13 }}>
                  <span>
                    <b>{w.simplified}</b> <span className="sub">{w.pinyin}</span>
                  </span>
                  <span className="sub">{w.meanings}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <button className="btn small ghost" onClick={onClose} style={{ marginTop: 16, width: "100%" }}>
          {t("pages.hanzi.close")}
        </button>

      {tracing && (
        <HanziTrace
          hanzi={current}
          mode={tracing === "memory" ? "memory" : "trace"}
          onClose={() => setTracing(false)}
          onSaved={(res) => {
            const updated = {
              ...current, writing_mastery: res.writing_mastery, writing_status: res.writing_status,
              times_written_memory: res.hanzi?.times_written_memory ?? current.times_written_memory,
            };
            setCurrent(updated);
            onUpdated?.(updated);
            setReaction(res.reaction || null);
            refresh?.();
          }}
        />
      )}
    </Wrap>
  );
}

// The trace dialog renders inside the card too; it is a fixed overlay of its
// own and stops its own clicks.
function ModalWrap({ onClose, children }) {
  const backdrop = useBackdropClose(onClose);
  return (
    <div className="modal modal-backdrop" {...backdrop}>
      <div
        className="card"
        onClick={(e) => e.stopPropagation()}
        style={{ maxWidth: 420, width: "100%", maxHeight: "90vh", overflowY: "auto" }}
      >
        {children}
      </div>
    </div>
  );
}

function InlineWrap({ children }) {
  return <article className="card hz-detail">{children}</article>;
}
