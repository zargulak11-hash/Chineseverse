import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api.js";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import { Empty, Loading } from "../components/ui.jsx";

export default function CaseSolve() {
  const { t, i18n } = useTranslation();
  const { scenarioId } = useParams();
  const navigate = useNavigate();
  const [sc, setSc] = useState(null);
  const [conclusion, setConclusion] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [sent, setSent] = useState(false);

  useEffect(() => {
    api.get(`/world/scenarios/${scenarioId}`).then(setSc).catch((e) => setError(e.message));
  }, [scenarioId, i18n.language]);

  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  if (!sc) return <Layout><Loading>{t("pages.caseSolve.opening")}</Loading></Layout>;

  const dialogs = sc.dialogues || [];

  async function solve() {
    if (!conclusion.trim() || sent) return;
    setSent(true);
    setResult(null);
    try {
      const r = await api.post(`/world/scenarios/${sc.slug}/solve`, { conclusion: conclusion.trim() });
      setResult(r);
    } catch (e) {
      setResult({ error: e.message });
    } finally {
      setSent(false);
    }
  }

  return (
    <Layout>
      <button className="btn ghost small" onClick={() => navigate(-1)}>← {t("common.back")}</button>
      <div className="row spread" style={{ marginTop: 10 }}>
        <div>
          <h1 className="h1"><Icon name="search" size={20} style={{ verticalAlign: -3, marginRight: 6 }} />{sc.title}</h1>
          <p className="sub">{sc.description}</p>
        </div>
        <span className="ilb">{t("pages.caseSolve.caseFile")}</span>
      </div>

      {sc.case_data?.clues?.length > 0 && (
        <div className="card" style={{ marginTop: 16 }}>
          <h2 className="h2">🔍 {t("pages.caseSolve.clues")}</h2>
          <ul style={{ marginTop: 8, paddingLeft: 18 }}>
            {sc.case_data.clues.map((clue, i) => (
              <li key={i} className="sub" style={{ marginTop: 4 }}>{clue}</li>
            ))}
          </ul>
        </div>
      )}

      {sc.case_data?.contradiction_text && (
        <div className="card" style={{ marginTop: 16, borderColor: "var(--bad)" }}>
          <h2 className="h2" style={{ color: "var(--bad)" }}>⚠️ {t("pages.caseSolve.contradiction")}</h2>
          <p className="sub" style={{ marginTop: 8 }}>{sc.case_data.contradiction_text}</p>
        </div>
      )}

      <div className="card" style={{ marginTop: 16 }}>
        <h2 className="h2">{t("pages.caseSolve.witnessStatements")}</h2>
        {dialogs.map((d) => (
          <div key={d.id} className="bubble npc" style={{ marginTop: 10 }}>
            <span className="speaker">🧑 {d.speaker}</span>
            {d.text}
            {d.pinyin && <span className="pinyin">{d.pinyin}</span>}
            {d.english && <span className="english">{d.english}</span>}
          </div>
        ))}
        {dialogs.length === 0 && <p className="sub">{t("pages.caseSolve.noStatements")}</p>}
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <h2 className="h2">{t("pages.caseSolve.yourVerdict")}</h2>
        <p className="sub">{t("pages.caseSolve.verdictPrompt")}</p>
        <textarea
          className="input"
          rows={3}
          value={conclusion}
          onChange={(e) => setConclusion(e.target.value)}
          placeholder="e.g. 小王忘了锁门"
        />
        <button className="btn primary" style={{ marginTop: 12 }} onClick={solve} disabled={sent || !conclusion.trim()}>
          {sent ? t("pages.caseSolve.checking") : t("pages.caseSolve.submitVerdict")}
        </button>
      </div>

      {result && (
        <div className="card" style={{ marginTop: 16, borderColor: result.solved ? "var(--good)" : "var(--bad)" }}>
          <b className="sub" style={{ color: result.solved ? "var(--good)" : "var(--bad)" }}>
            <Icon name={result.solved ? "check" : "x"} size={14} style={{ verticalAlign: -2, marginRight: 4 }} />
            {result.solved ? t("pages.caseSolve.caseSolved") : t("pages.caseSolve.notQuiteRight")}
          </b>
          <p className="sub" style={{ marginTop: 8, whiteSpace: "pre-wrap" }}>
            {typeof result.feedback === "string" ? result.feedback : JSON.stringify(result.feedback)}
          </p>
          {!result.solved && result.correct_answer && (
            <p className="sub" style={{ marginTop: 6 }}>{t("pages.caseSolve.hint")}: {result.correct_answer}</p>
          )}
        </div>
      )}
    </Layout>
  );
}