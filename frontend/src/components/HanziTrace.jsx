import HanziWriter from "hanzi-writer";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../api.js";

// Real stroke-order practice: HanziWriter validates every drawn stroke
// against the character's actual stroke path/median data (fetched from
// /api/hanzi/{id}/stroke-data, sourced from skishore/makemeahanzi) -- it is
// not a fake completion button. onComplete only fires after every real
// stroke has been traced and matched correctly by HanziWriter's own
// hit-testing.
//
// The server doesn't take the browser's word for it: "Try writing" opens a
// tracing attempt (/write/start), every stroke drawn is recorded with
// HanziWriter's drawnPath.points (character space), and "Save" sends them so
// the server re-matches each stroke against the same stroke data
// (backend services/stroke_match.py) and counts the mistakes itself.
//
// Flow: watch the real stroke-order animation first (HanziWriter's own
// animateCharacter(), stroke by stroke from the same real data) -> replay
// as many times as wanted -> "Try writing" switches the SAME writer
// instance into its quiz mode -> validate -> save. This is one component
// because the watch step and the write step share one HanziWriter instance
// and one loaded stroke dataset -- no reason to split them into two
// separately-loading pieces.
//
// mode="memory" (like Skritter's writing from memory): no outline and no
// stroke-order animation first -- the learner sees only the pinyin and the
// meaning and writes the character unaided. HanziWriter still checks every
// stroke; a stroke's hint appears after 3 misses (they count as mistakes).
// The server fixes the mode when it opens the attempt.
export default function HanziTrace({ hanzi, onClose, onSaved, mode = "trace" }) {
  const memory = mode === "memory";
  const { t } = useTranslation();
  const mountRef = useRef(null);
  const writerRef = useRef(null);
  const attemptRef = useRef(null); // server-issued tracing attempt id
  const strokesRef = useRef([]); // [{points: [[x, y], ...], matched}] in drawing order
  const [phase, setPhase] = useState("loading"); // loading | watch | quiz | done
  const [mistakes, setMistakes] = useState(0);
  const [done, setDone] = useState(null);
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setPhase("loading");
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
          showOutline: !memory,
          showCharacter: false,
          strokeAnimationSpeed: 1,
          delayBetweenStrokes: 250,
          charDataLoader: (_char, onLoad) => onLoad(data.stroke_data),
        });
        writerRef.current = writer;
        if (memory) {
          setPhase("watch"); // nothing is shown first: the character is the answer
          return;
        }
        writer.animateCharacter({
          onComplete: () => {
            if (!cancelled) setPhase("watch");
          },
        });
      })
      .catch((e) => setError(e.message));

    return () => {
      cancelled = true;
      writerRef.current = null;
    };
  }, [hanzi.id, memory]); // eslint-disable-line react-hooks/exhaustive-deps

  function watchAgain() {
    writerRef.current?.hideCharacter({ duration: 0 });
    writerRef.current?.animateCharacter({ onComplete: () => setPhase("watch") });
  }

  function record(strokeData, matched) {
    const points = (strokeData?.drawnPath?.points || []).map((p) => [p.x, p.y]);
    strokesRef.current.push({ points, matched });
  }

  async function startWriting() {
    setError(null);
    setDone(null);
    setMistakes(0);
    strokesRef.current = [];
    attemptRef.current = null;
    try {
      attemptRef.current = (await api.post(`/hanzi/${hanzi.id}/write/start`, { mode })).attempt_id;
    } catch (e) {
      setError(e.message);
      return;
    }
    setPhase("quiz");
    writerRef.current?.quiz({
      showHintAfterMisses: 3,
      onMistake: (s) => {
        record(s, false);
        setMistakes((m) => m + 1);
      },
      onCorrectStroke: (s) => record(s, true),
      onComplete: (summary) => setDone({ totalMistakes: summary.totalMistakes }),
    });
  }

  async function save() {
    if (!done) return;
    setSaving(true);
    try {
      const res = await api.post(`/hanzi/${hanzi.id}/write`, {
        attempt_id: attemptRef.current,
        strokes: strokesRef.current,
      });
      onSaved?.(res);
      onClose();
    } catch (e) {
      setError(e.message);
      setSaving(false);
    }
  }

  return (
    <div className={`modal modal-backdrop${memory ? " trace-memory-backdrop" : ""}`} onClick={onClose}>
      <div className="card" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 340, textAlign: "center" }}>
        {memory && !done ? (
          <>
            <p className="side-title">{t("pages.hanzi.memoryPrompt")}</p>
            <h2 className="h2">{hanzi.pinyin}</h2>
          </>
        ) : (
          <h2 className="h2" lang="zh-CN">{hanzi.character}</h2>
        )}
        <p className="sub">{memory && !done ? hanzi.meaning : `${hanzi.pinyin} · ${hanzi.meaning}`}</p>

        {error && <p className="sub" style={{ color: "var(--bad, #e55)" }}>{error}</p>}

        <div ref={mountRef} style={{ width: 260, height: 260, margin: "12px auto", border: "1px solid var(--border, #333)" }} />

        {phase === "loading" && <p className="sub">{t("pages.hanzi.watchingStrokeOrder")}</p>}

        {phase === "watch" && memory && (
          <div>
            <p className="sub">{t("pages.hanzi.memoryHint")}</p>
            <div className="row" style={{ marginTop: 10, justifyContent: "center" }}>
              <button className="btn small primary" onClick={startWriting}>{t("pages.hanzi.memoryStart")}</button>
            </div>
          </div>
        )}
        {phase === "watch" && !memory && (
          <div>
            <p className="sub">{t("pages.hanzi.strokeOrderShown")}</p>
            <div className="row" style={{ marginTop: 10, justifyContent: "center" }}>
              <button className="btn small ghost" onClick={watchAgain}>{t("pages.hanzi.watchAgain")}</button>
              <button className="btn small primary" onClick={startWriting}>{t("pages.hanzi.tryWriting")}</button>
            </div>
          </div>
        )}

        {phase === "quiz" && (
          <>
            <p className="sub">{t("pages.hanzi.mistakes", { count: mistakes })}</p>
            {done ? (
              <div>
                <p className="badge good">{t("pages.hanzi.traceComplete", { count: done.totalMistakes })}</p>
                <div className="row" style={{ marginTop: 10, justifyContent: "center" }}>
                  <button className="btn small ghost" onClick={startWriting} disabled={saving}>{t("pages.hanzi.retry")}</button>
                  <button className="btn small primary" onClick={save} disabled={saving}>{t("pages.hanzi.saveProgress")}</button>
                </div>
              </div>
            ) : (
              // From memory, watching it would show the answer.
              !memory && <button className="btn small ghost" onClick={watchAgain} style={{ marginTop: 6 }}>{t("pages.hanzi.watchAgain")}</button>
            )}
          </>
        )}

        <button className="btn small ghost" onClick={onClose} style={{ marginTop: 10 }}>{t("pages.hanzi.cancel")}</button>
      </div>
    </div>
  );
}
