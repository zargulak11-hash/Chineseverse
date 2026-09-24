import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../api.js";
import Layout from "../components/Layout.jsx";
import { Bar, Empty } from "../components/ui.jsx";
import { useApi } from "../hooks/useApi.js";

export default function Grammar() {
  const { t } = useTranslation();
  const [level, setLevel] = useState(1);
  const { data, setData, error } = useApi(`/grammar?hsk_level=${level}`);
  const { data: roadmap } = useApi("/hsk/roadmap");
  const topics = data || [];
  const [flash, setFlash] = useState(null);
  const [open, setOpen] = useState(null);

  useEffect(() => {
    if (!flash) return;
    const timer = setTimeout(() => setFlash(null), 2200);
    return () => clearTimeout(timer);
  }, [flash]);

  async function practice(topicItem, correct) {
    try {
      const res = await api.post(`/grammar/${topicItem.id}/practice`, { correct });
      setFlash({ title: topicItem.title, mastery: res.mastery, status: res.status });
      setData((items) =>
        (items || []).map((x) =>
          x.id === topicItem.id ? { ...x, mastery: res.mastery, status: res.status } : x
        )
      );
    } catch (e) {
      setFlash({ title: topicItem.title, mastery: null, status: e.message });
    }
  }

  if (error) return <Layout><Empty>{error}</Empty></Layout>;

  const counts = {};
  for (const lv of roadmap?.levels || []) counts[lv.level] = lv.grammar_total;

  return (
    <Layout>
      <h1 className="h1">{t("pages.grammar.title")}</h1>
      <p className="sub">{t("pages.grammar.subtitle")}</p>

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
          <b>{flash.title}</b> — {flash.mastery != null ? `${flash.mastery.toFixed(0)}% · ${flash.status}` : flash.status}
        </div>
      )}

      <div className="grid cards" style={{ marginTop: 16 }}>
        {topics.map((topic) => (
          <div key={topic.id} className="card" style={{ border: topic.due_for_review ? "1px solid var(--accent)" : undefined }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start" }}>
              <div>
                {topic.category && <span className="ilb" style={{ marginBottom: 4 }}>{topic.category}</span>}
                <div style={{ fontWeight: 800, fontSize: 16 }}>{topic.title}</div>
                {topic.pattern && <div className="sub" style={{ color: "var(--accent2)" }}>{topic.pattern}</div>}
              </div>
              {topic.due_for_review && <span className="badge accent" style={{ fontSize: 10 }}>{t("pages.vocabulary.due")}</span>}
            </div>

            {topic.explanation && <p className="sub" style={{ marginTop: 8 }}>{topic.explanation}</p>}

            <button
              type="button"
              className="btn small ghost"
              style={{ marginTop: 8 }}
              onClick={() => setOpen(open === topic.id ? null : topic.id)}
            >
              {open === topic.id ? t("pages.grammar.hideExamples") : t("pages.grammar.showExamples")}
            </button>
            {open === topic.id && topic.examples && (
              <pre className="sub" style={{ whiteSpace: "pre-wrap", marginTop: 8, fontFamily: "inherit" }}>
                {topic.examples}
              </pre>
            )}

            <div style={{ marginTop: 10 }}>
              <Bar value={topic.mastery ?? 0} alt />
            </div>
            <div className="row" style={{ marginTop: 10 }}>
              <button className="btn small" onClick={() => practice(topic, true)}>
                {t("pages.grammar.gotIt")}
              </button>
              <button className="btn small ghost" onClick={() => practice(topic, false)}>
                {t("pages.grammar.stillLearning")}
              </button>
            </div>
          </div>
        ))}
      </div>
      {topics.length === 0 && <Empty>{t("pages.grammar.empty")}</Empty>}
    </Layout>
  );
}
