import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { api } from "../api.js";
import Layout from "../components/Layout.jsx";
import { Empty } from "../components/ui.jsx";
import { useApi } from "../hooks/useApi.js";

// Where to actually re-earn mastery of each mistake type — mastery is
// never set by a click here, only by answering correctly again on one of
// these surfaces (see reinforce_mistake() in the backend).
const PRACTICE_ROUTE = {
  word: "/review",
  hanzi: "/review",
  hanzi_write: "/hanzi",
  pinyin: "/duels",
  tone: "/duels",
  character: "/duels",
  grammar: "/review",
};

// Cases log grammar mistakes against the scenario slug (ascii-kebab), which
// only the living world can re-test; grammar-point mistakes go to Review.
function practiceRoute(m) {
  if (m.mistake_type === "grammar" && /^[a-z0-9-]+$/.test(m.reference)) return `/real-chinese/case/${m.reference}`;
  return PRACTICE_ROUTE[m.mistake_type] || "/review";
}

export default function Mistakes() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { data, setData, error, setError } = useApi("/mistakes");
  const mistakes = data || [];

  async function practice(m) {
    try {
      const updated = await api.patch(`/mistakes/${m.id}`, { request_retest: true });
      setData((ms) => (ms || []).map((x) => (x.id === m.id ? updated : x)));
    } catch (e) {
      setError(e.message);
    }
    navigate(practiceRoute(m));
  }

  if (error) return <Layout><Empty>{error}</Empty></Layout>;

  const open = mistakes.filter((m) => !m.mastered);
  const done = mistakes.filter((m) => m.mastered);

  return (
    <Layout>
      <h1 className="h1">{t("pages.mistakes.title")}</h1>
      <p className="sub">{t("pages.mistakes.subtitle")}</p>
      {open.length > 0 && (
        <button className="btn primary" style={{ marginTop: 12 }} onClick={() => navigate("/review")}>
          {t("pages.mistakes.reviewNow")}
        </button>
      )}

      <div className="ranges" style={{ marginTop: 16 }}>
        <h2 className="h2">{t("pages.mistakes.stillWorking")} ({open.length})</h2>
        <div className="col">
          {open.map((m) => (
            <div key={m.id} className="card">
              <div className="row spread">
                <div>
                  <b>{m.question_text || m.reference}</b>
                  <p className="sub" style={{ marginTop: 4, fontSize: 13 }}>
                    {t("pages.mistakes.youSaid")}: <em>{m.answer_given || "—"}</em>
                    {m.correct_answer && <> · {t("pages.mistakes.correct")}: <b>{m.correct_answer}</b></>}
                  </p>
                </div>
                <div className="col" style={{ gap: 6, alignItems: "flex-end" }}>
                  <span className={`badge ${m.due_for_review ? "accent" : "bad"}`}>
                    {m.due_for_review ? t("pages.mistakes.dueNow") : `×${m.occurrences}`}
                  </span>
                  <button className="btn small" onClick={() => practice(m)}>
                    {t("pages.mistakes.practiceThis")} →
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {done.length > 0 && (
        <div style={{ marginTop: 20 }}>
          <h2 className="h2">{t("pages.mistakes.mastered")} ({done.length})</h2>
          <div className="grid cards">
            {done.map((m) => (
              <div key={m.id} className="card" style={{ opacity: 0.7 }}>
                <span className="badge good">✓ {t("pages.mistakes.masteredBadge")}</span>
                <p className="sub" style={{ marginTop: 8 }}>{m.question_text || m.reference}</p>
              </div>
            ))}
          </div>
        </div>
      )}
      {mistakes.length === 0 && <Empty>{t("pages.mistakes.empty")}</Empty>}
    </Layout>
  );
}
