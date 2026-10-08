import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import { Bar, Empty, Loading } from "../components/ui.jsx";
import { useApi } from "../hooks/useApi.js";

// The first example sentence (the syllabus text can open with a numbered
// sub-heading or hold several examples on one line).
function firstExample(examples) {
  for (const line of (examples || "").split("\n")) {
    const part = line.split(/\s*\/\s*/)[0].trim();
    if (part && !/^[（(]\d|^[①-⑳]|见【/.test(part) && /[㐀-鿿]/.test(part)) return part;
  }
  return null;
}

export default function Grammar() {
  const { t } = useTranslation();
  const [level, setLevel] = useState(1);
  const { data, error } = useApi(`/grammar?hsk_level=${level}`);
  const { data: roadmap } = useApi("/hsk/roadmap");
  const topics = data || [];

  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  if (!data) return <Layout><Loading /></Layout>;

  const counts = {};
  for (const lv of roadmap?.levels || []) counts[lv.level] = lv.grammar_total;

  // A level holds up to ~90 points; one undifferentiated grid of them was
  // hard to scan. They are grouped by syllabus category (localized by the
  // API), in curriculum order, the hand-written core points first.
  const groups = [];
  const byKey = new Map();
  for (const topic of topics) {
    const key = topic.category || "";
    if (!byKey.has(key)) {
      const g = { key, label: key || t("pages.grammar.core"), items: [] };
      byKey.set(key, g);
      groups.push(g);
    }
    byKey.get(key).items.push(topic);
  }
  groups.sort((a, b) => (a.key === "" ? -1 : b.key === "" ? 1 : 0));

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

      {topics.length > 0 && (
        <div className="row" style={{ marginTop: 14 }}>
          <Link to={`/practice?source=grammar&level=${level}`}>
            <button className="btn primary">{t("practice.startLevel", { level })}</button>
          </Link>
        </div>
      )}

      {groups.length > 2 && (
        <nav className="grammar-jump" aria-label={t("pages.grammar.jump")}>
          {groups.map((g, i) => (
            <a key={g.key || "core"} href={`#grammar-group-${i}`} className="btn small ghost">
              {g.label} <span className="grammar-count">{g.items.length}</span>
            </a>
          ))}
        </nav>
      )}

      {groups.map((g, i) => (
        <section key={g.key || "core"} id={`grammar-group-${i}`} className="grammar-group">
          <h2 className="h2 section-title">
            {g.label} <span className="grammar-count">{g.items.length}</span>
          </h2>
          <div className="grid cards">
            {g.items.map((topic) => (
              <Link
                key={topic.id}
                to={`/grammar/${topic.id}`}
                className="card hover gt-card"
                style={topic.due_for_review ? { borderColor: "var(--accent-border)" } : undefined}
              >
                <div className="row spread" style={{ alignItems: "flex-start", gap: 8 }}>
                  <div style={{ minWidth: 0 }}>
                    {topic.name ? (
                      <>
                        <div className="gt-card-title">{topic.name}</div>
                        <div className="sub" lang="zh-CN">{topic.title}</div>
                      </>
                    ) : (
                      <>
                        <div className="gt-card-title" lang="zh-CN">{topic.title}</div>
                        {topic.pattern && topic.pattern !== topic.title && <div className="sub" lang="zh-CN">{topic.pattern}</div>}
                      </>
                    )}
                  </div>
                  {topic.due_for_review && <span className="badge accent">{t("pages.vocabulary.due")}</span>}
                </div>
                {topic.explanation && <p className="sub" style={{ marginTop: 8 }}>{topic.explanation}</p>}
                {firstExample(topic.examples) && <p className="gt-card-ex" lang="zh-CN">{firstExample(topic.examples)}</p>}
                <div style={{ marginTop: 12 }}>
                  <Bar value={topic.mastery ?? 0} alt />
                </div>
                <span className="gt-card-open">{t("pages.grammar.open")} <Icon name="chevronRight" size={13} /></span>
              </Link>
            ))}
          </div>
        </section>
      ))}
      {topics.length === 0 && <Empty>{t("pages.grammar.empty")}</Empty>}
    </Layout>
  );
}
