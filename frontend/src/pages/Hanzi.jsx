import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../api.js";
import HanziTrace from "../components/HanziTrace.jsx";
import Layout from "../components/Layout.jsx";
import { Bar, Empty } from "../components/ui.jsx";
import { useApi } from "../hooks/useApi.js";

export default function Hanzi() {
  const { t } = useTranslation();
  const [level, setLevel] = useState(1);
  const { data, setData, error } = useApi(`/hanzi?hsk_level=${level}`);
  const { data: roadmap } = useApi("/hsk/roadmap");
  const chars = data || [];
  const [flash, setFlash] = useState(null);
  const [tracing, setTracing] = useState(null);

  useEffect(() => {
    if (!flash) return;
    const timer = setTimeout(() => setFlash(null), 2200);
    return () => clearTimeout(timer);
  }, [flash]);

  async function review(ch) {
    try {
      const res = await api.post(`/hanzi/${ch.id}/review`, { correct: true });
      setFlash({ char: ch.character, mastery: res.mastery, status: res.status });
      setData((items) =>
        (items || []).map((x) =>
          x.id === ch.id ? { ...x, mastery: res.mastery, status: res.status } : x
        )
      );
    } catch (e) {
      setFlash({ char: ch.character, mastery: null, status: e.message });
    }
  }

  if (error) return <Layout><Empty>{error}</Empty></Layout>;

  const counts = {};
  for (const lv of roadmap?.levels || []) counts[lv.level] = lv.hanzi_total;

  return (
    <Layout>
      <h1 className="h1">{t("pages.hanzi.title")}</h1>
      <p className="sub">{t("pages.hanzi.subtitle")}</p>

      <div className="row" style={{ marginTop: 14, flexWrap: "wrap" }}>
        {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((lv) => (
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
          <b>{flash.char}</b> — {flash.mastery != null ? `${flash.mastery.toFixed(0)}% · ${flash.status}` : flash.status}
        </div>
      )}

      <div className="grid cards" style={{ marginTop: 16 }}>
        {chars.map((ch) => (
          <div
            key={ch.id}
            className="card hover animal"
            role="button"
            tabIndex={0}
            style={{ border: ch.due_for_review ? "1px solid var(--accent)" : 0, textAlign: "center", position: "relative", cursor: "pointer" }}
            onClick={() => review(ch)}
          >
            {ch.due_for_review && (
              <span className="badge accent" style={{ position: "absolute", top: 8, right: 8, fontSize: 10 }}>
                {t("pages.vocabulary.due")}
              </span>
            )}
            {ch.handwriting_tier && (
              <span className="badge" style={{ position: "absolute", top: 8, left: 8, fontSize: 10 }}>
                {t("pages.hanzi.handwriting")}
              </span>
            )}
            <div style={{ fontSize: 32, fontWeight: 800 }}>{ch.character}</div>
            <div className="sub" style={{ color: "var(--accent2)" }}>{ch.pinyin}</div>
            <div className="sub">{ch.meaning}</div>
            {ch.stroke_count != null && (
              <span className="ilb" style={{ marginTop: 6 }}>{t("pages.hanzi.strokes", { count: ch.stroke_count })}</span>
            )}
            <div style={{ marginTop: 8, width: "100%" }}>
              <Bar value={ch.mastery ?? 0} alt />
            </div>
            {ch.handwriting_tier && (
              <>
                <div style={{ marginTop: 6, width: "100%" }} title={t("pages.hanzi.writingMastery")}>
                  <Bar value={ch.writing_mastery ?? 0} />
                </div>
                <button
                  type="button"
                  className="btn small ghost"
                  style={{ marginTop: 8, width: "100%" }}
                  onClick={(e) => { e.stopPropagation(); setTracing(ch); }}
                >
                  {t("pages.hanzi.practiceWriting")}
                </button>
              </>
            )}
          </div>
        ))}
      </div>
      {chars.length === 0 && <Empty>{t("pages.hanzi.empty")}</Empty>}

      {tracing && (
        <HanziTrace
          hanzi={tracing}
          onClose={() => setTracing(null)}
          onSaved={(res) => {
            setFlash({ char: tracing.character, mastery: res.writing_mastery, status: res.writing_status });
            setData((items) =>
              (items || []).map((x) =>
                x.id === tracing.id ? { ...x, writing_mastery: res.writing_mastery, writing_status: res.writing_status } : x
              )
            );
          }}
        />
      )}
    </Layout>
  );
}
