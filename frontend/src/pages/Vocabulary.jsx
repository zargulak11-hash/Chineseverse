import { useEffect, useState } from "react";
import { api } from "../api.js";
import Layout from "../components/Layout.jsx";
import { Bar, Empty } from "../components/ui.jsx";
import { useApi } from "../hooks/useApi.js";

export default function Vocabulary() {
  const { data, setData, error } = useApi("/vocab");
  const words = data || [];
  const [level, setLevel] = useState(1);
  const [flash, setFlash] = useState(null);

  useEffect(() => {
    if (!flash) return;
    const t = setTimeout(() => setFlash(null), 2200);
    return () => clearTimeout(t);
  }, [flash]);

  const filtered = words.filter((w) => w.hsk_level_id === level);

  async function review(w) {
    try {
      const res = await api.post(`/vocab/${w.id}/review`, { correct: true });
      setFlash({ word: w.simplified, mastery: res.mastery, status: res.status });
      setData((ws) =>
        (ws || []).map((x) =>
          x.id === w.id ? { ...x, mastery: res.mastery, status: res.status } : x
        )
      );
    } catch (e) {
      setFlash({ word: w.simplified, mastery: null, status: e.message });
    }
  }

  if (error) return <Layout><Empty>{error}</Empty></Layout>;

  const counts = {};
  for (const lv of [1, 2, 3, 4, 5, 6]) counts[lv] = words.filter((w) => w.hsk_level_id === lv).length;

  return (
    <Layout>
      <h1 className="h1">Vocabulary</h1>
      <p className="sub">Tap a card to self-review. Reviews feed your DNA and daily quests.</p>

      <div className="row" style={{ marginTop: 14 }}>
        {[1, 2, 3, 4, 5, 6].map((lv) => (
          <button
            key={lv}
            className={`btn small${level === lv ? " primary" : ""}`}
            onClick={() => setLevel(lv)}
          >
            HSK {lv} {counts[lv] > 0 ? `(${counts[lv]})` : ""}
          </button>
        ))}
      </div>

      {flash && (
        <div className="card" style={{ marginTop: 14, borderColor: "var(--good)" }}>
          <b>{flash.word}</b> — {flash.mastery != null ? `${flash.mastery.toFixed(0)}% · ${flash.status}` : flash.status}
        </div>
      )}

      {filtered.some((w) => w.due_for_review) && (
        <p className="sub" style={{ marginTop: 14 }}>
          ⏰ {filtered.filter((w) => w.due_for_review).length} word(s) due for review — surfaced first below.
        </p>
      )}

      <div className="grid cards" style={{ marginTop: 16 }}>
        {filtered.map((w) => (
          <button
            key={w.id}
            className="card hover animal"
            style={{ border: w.due_for_review ? "1px solid var(--accent)" : 0, textAlign: "center", position: "relative" }}
            onClick={() => review(w)}
          >
            {w.due_for_review && (
              <span className="badge accent" style={{ position: "absolute", top: 8, right: 8, fontSize: 10 }}>
                due
              </span>
            )}
            <div style={{ fontSize: 24, fontWeight: 800 }}>{w.simplified}</div>
            {w.traditional && w.traditional !== w.simplified && (
              <div className="muted" style={{ fontSize: 13 }}>{w.traditional}</div>
            )}
            <div className="sub" style={{ color: "var(--accent2)" }}>{w.pinyin}</div>
            <div className="sub">{w.meanings}</div>
            {w.word_type && <span className="ilb" style={{ marginTop: 6 }}>{w.word_type}</span>}
            <div style={{ marginTop: 8, width: "100%" }}>
              <Bar value={w.mastery ?? 0} alt />
            </div>
          </button>
        ))}
      </div>
      {filtered.length === 0 && <Empty>No words at this level yet.</Empty>}
    </Layout>
  );
}