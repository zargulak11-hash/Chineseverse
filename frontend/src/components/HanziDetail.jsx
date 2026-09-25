import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../api.js";
import { Bar } from "./ui.jsx";
import Icon from "./Icon.jsx";
import HanziTrace from "./HanziTrace.jsx";
import { speakChinese } from "../zhSpeech.js";

// The full "SEE -> pronunciation -> hear -> meaning -> examples -> progress"
// hub for one character. Writing practice (watch stroke order -> try
// writing -> validate -> save) is launched from here but stays its own
// component (HanziTrace) since it already owns that whole flow end to end
// -- this view is the overview/reference screen around it, not a second
// writing implementation.
export default function HanziDetail({ hanzi, level, onClose, onUpdated }) {
  const { t } = useTranslation();
  const [current, setCurrent] = useState(hanzi);
  const [examples, setExamples] = useState(null);
  const [examplesError, setExamplesError] = useState(null);
  const [tracing, setTracing] = useState(false);
  const [reviewing, setReviewing] = useState(false);
  const [speaking, setSpeaking] = useState(false);

  useEffect(() => {
    setCurrent(hanzi);
    setExamples(null);
    setExamplesError(null);
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
    } catch {
      // stays on-screen; the button simply re-enables for another try
    } finally {
      setReviewing(false);
    }
  }

  return (
    <div
      className="modal-backdrop"
      onClick={onClose}
      style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 100, padding: 16 }}
    >
      <div
        className="card"
        onClick={(e) => e.stopPropagation()}
        style={{ maxWidth: 420, width: "100%", maxHeight: "90vh", overflowY: "auto" }}
      >
        {/* SEE + PRONUNCIATION + HEAR */}
        <div style={{ textAlign: "center" }}>
          <div style={{ fontSize: 56, fontWeight: 800, lineHeight: 1 }}>{current.character}</div>
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
              <Icon name="mic" size={14} style={{ verticalAlign: -2, marginRight: 4 }} />
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

        {/* WRITE entry point (real stroke data required, gated to the
            characters the real HSK 3.0 syllabus requires handwriting for) */}
        {current.handwriting_tier && (
          <button
            type="button"
            className="btn small ghost"
            style={{ marginTop: 10, width: "100%" }}
            onClick={() => setTracing(true)}
          >
            {t("pages.hanzi.practiceWriting")}
          </button>
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
      </div>

      {tracing && (
        <HanziTrace
          hanzi={current}
          onClose={() => setTracing(false)}
          onSaved={(res) => {
            const updated = { ...current, writing_mastery: res.writing_mastery, writing_status: res.writing_status };
            setCurrent(updated);
            onUpdated?.(updated);
          }}
        />
      )}
    </div>
  );
}
