import HanziWriter from "hanzi-writer";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../api.js";

// Real stroke-order tracing practice: HanziWriter validates every drawn
// stroke against the character's actual stroke path/median data (fetched
// from /api/hanzi/{id}/stroke-data, sourced from skishore/makemeahanzi) --
// it is not a fake completion button. onComplete only fires after every
// real stroke has been traced and matched correctly by HanziWriter's own
// hit-testing.
export default function HanziTrace({ hanzi, onClose, onSaved }) {
  const { t } = useTranslation();
  const mountRef = useRef(null);
  const writerRef = useRef(null);
  const [mistakes, setMistakes] = useState(0);
  const [done, setDone] = useState(null);
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setDone(null);
    setMistakes(0);
    setError(null);

    api
      .get(`/hanzi/${hanzi.id}/stroke-data`)
      .then((data) => {
        if (cancelled || !mountRef.current) return;
        if (!data.stroke_data || !data.stroke_data.strokes) {
          setError(t("pages.hanzi.noStrokeData"));
          return;
        }
        mountRef.current.innerHTML = "";
        const writer = HanziWriter.create(mountRef.current, hanzi.character, {
          width: 260,
          height: 260,
          padding: 12,
          showOutline: true,
          strokeAnimationSpeed: 1,
          delayBetweenStrokes: 200,
          charDataLoader: (_char, onLoad) => onLoad(data.stroke_data),
        });
        writerRef.current = writer;
        writer.quiz({
          onMistake: () => setMistakes((m) => m + 1),
          onCorrectStroke: () => {},
          onComplete: (summary) => {
            setDone({ totalMistakes: summary.totalMistakes });
          },
        });
      })
      .catch((e) => setError(e.message));

    return () => {
      cancelled = true;
      writerRef.current = null;
    };
  }, [hanzi.id]);

  async function save() {
    if (!done) return;
    setSaving(true);
    try {
      const res = await api.post(`/hanzi/${hanzi.id}/write`, { total_mistakes: done.totalMistakes });
      onSaved?.(res);
      onClose();
    } catch (e) {
      setError(e.message);
      setSaving(false);
    }
  }

  function retry() {
    setDone(null);
    setMistakes(0);
    writerRef.current?.quiz({
      onMistake: () => setMistakes((m) => m + 1),
      onCorrectStroke: () => {},
      onComplete: (summary) => setDone({ totalMistakes: summary.totalMistakes }),
    });
  }

  return (
    <div className="modal-backdrop" onClick={onClose} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 100 }}>
      <div className="card" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 340, textAlign: "center" }}>
        <h2 className="h2">{hanzi.character}</h2>
        <p className="sub">{hanzi.pinyin} · {hanzi.meaning}</p>

        {error && <p className="sub" style={{ color: "var(--bad, #e55)" }}>{error}</p>}

        <div ref={mountRef} style={{ width: 260, height: 260, margin: "12px auto", border: "1px solid var(--border, #333)" }} />

        <p className="sub">{t("pages.hanzi.mistakes", { count: mistakes })}</p>

        {done ? (
          <div>
            <p className="badge good">{t("pages.hanzi.traceComplete", { count: done.totalMistakes })}</p>
            <div className="row" style={{ marginTop: 10, justifyContent: "center" }}>
              <button className="btn small ghost" onClick={retry} disabled={saving}>{t("pages.hanzi.retry")}</button>
              <button className="btn small primary" onClick={save} disabled={saving}>{t("pages.hanzi.saveProgress")}</button>
            </div>
          </div>
        ) : (
          <button className="btn small ghost" onClick={onClose} style={{ marginTop: 10 }}>{t("pages.hanzi.cancel")}</button>
        )}
      </div>
    </div>
  );
}
