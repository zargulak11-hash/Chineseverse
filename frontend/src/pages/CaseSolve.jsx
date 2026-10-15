import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api.js";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import { Empty, Loading } from "../components/ui.jsx";
import { useDashboard } from "../context/DashboardContext.jsx";
import { speakChinese } from "../zhSpeech.js";

// A Real Chinese case (/real-chinese/case/:slug): the clues, the
// contradiction and what the witnesses said, laid out as a case board (the
// Detective dossier's styles), with the verdict written beside it and
// checked by the server (/world/scenarios/:slug/solve).
//
// The scenario's learner turns are speaking prompts with no text of their
// own; they are not statements, so they are not listed (they showed as
// empty bubbles).

export default function CaseSolve() {
  const { t, i18n } = useTranslation();
  const { scenarioId } = useParams();
  const navigate = useNavigate();
  const [sc, setSc] = useState(null);
  const [conclusion, setConclusion] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [sent, setSent] = useState(false);
  const { refresh } = useDashboard() || {};

  useEffect(() => {
    api.get(`/world/scenarios/${scenarioId}`).then(setSc).catch((e) => setError(e.message));
  }, [scenarioId, i18n.language]);

  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  if (!sc) return <Layout><Loading>{t("pages.caseSolve.opening")}</Loading></Layout>;

  const statements = (sc.dialogues || []).filter((d) => (d.text || "").trim());

  async function solve() {
    if (!conclusion.trim() || sent) return;
    setSent(true);
    setResult(null);
    try {
      const r = await api.post(`/world/scenarios/${sc.slug}/solve`, { conclusion: conclusion.trim() });
      setResult(r);
      refresh?.(); // a solved case can complete a mission (and its achievement)
    } catch (e) {
      setResult({ error: e.message });
    } finally {
      setSent(false);
    }
  }

  return (
    <Layout>
      <header className="page-head dossier-head">
        <div>
          <button type="button" className="page-eyebrow ld-back cs-back" onClick={() => navigate(-1)}>
            <Icon name="arrowLeft" size={13} /> {t("common.back")}
          </button>
          <h1 className="h1"><Icon name="search" size={20} style={{ verticalAlign: -3, marginRight: 6 }} />{sc.title}</h1>
          <p className="sub">{sc.description}</p>
        </div>
        <div className="kpi-row">
          <div className="kpi"><span className="kpi-value">{sc.case_data?.clues?.length ?? 0}</span><span className="kpi-label">{t("pages.caseSolve.clues")}</span></div>
          <div className="kpi"><span className="kpi-value">{statements.length}</span><span className="kpi-label">{t("pages.caseSolve.witnessStatements")}</span></div>
        </div>
      </header>

      <div className="ws">
        <div className="ws-main">
          {sc.case_data?.clues?.length > 0 && (
            <section className="card dossier-brief" aria-labelledby="cs-clues">
              <h2 className="h2" id="cs-clues"><Icon name="search" size={16} style={{ verticalAlign: -2 }} /> {t("pages.caseSolve.clues")}</h2>
              <ol className="dossier-exhibits">
                {sc.case_data.clues.map((clue, i) => (
                  <li key={i}>
                    <span className="dossier-tag">{t("detective.exhibit", { n: i + 1 })}</span>
                    <div className="dossier-line">
                      <div className="dossier-zh" lang="zh-CN">{clue}</div>
                      <button type="button" className="icon-btn" onClick={() => speakChinese(clue)} aria-label={t("companionReact.hear")}>
                        <Icon name="ear" size={15} />
                      </button>
                    </div>
                  </li>
                ))}
              </ol>
            </section>
          )}

          {sc.case_data?.contradiction_text && (
            <section className="card cs-contradiction" aria-labelledby="cs-contra">
              <h2 className="h2" id="cs-contra"><Icon name="alert" size={16} style={{ verticalAlign: -2 }} /> {t("pages.caseSolve.contradiction")}</h2>
              <p className="dossier-zh" lang="zh-CN" style={{ marginTop: 8 }}>{sc.case_data.contradiction_text}</p>
            </section>
          )}

          <section className="card" aria-labelledby="cs-witness">
            <h2 className="h2" id="cs-witness">{t("pages.caseSolve.witnessStatements")}</h2>
            {statements.length === 0 ? (
              <p className="sub">{t("pages.caseSolve.noStatements")}</p>
            ) : (
              <div className="dossier-lines">
                {statements.map((d) => (
                  <div key={d.id} className="dossier-quote">
                    <div className="dossier-line">
                      <div style={{ minWidth: 0 }}>
                        <div className="dossier-zh is-big" lang="zh-CN">{d.text}</div>
                        {d.pinyin && <div className="sub">{d.pinyin}</div>}
                        {d.english && <div className="sub dossier-tr">{d.english}</div>}
                      </div>
                      <button type="button" className="icon-btn" onClick={() => speakChinese(d.text)} aria-label={t("companionReact.hear")}>
                        <Icon name="ear" size={15} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>

        <aside className="ws-side">
          <div className="card side-card dossier-ask cs-verdict">
            <p className="side-title">{t("pages.caseSolve.yourVerdict")}</p>
            <p className="sub" style={{ marginTop: 0 }}>{t("pages.caseSolve.verdictPrompt")}</p>
            <label className="sr-only" htmlFor="cs-conclusion">{t("pages.caseSolve.yourVerdict")}</label>
            <textarea
              id="cs-conclusion"
              className="input"
              lang="zh-CN"
              rows={4}
              value={conclusion}
              onChange={(e) => setConclusion(e.target.value)}
              placeholder={t("pages.caseSolve.verdictPlaceholder")}
            />
            <button className="btn primary" style={{ marginTop: 12 }} onClick={solve} disabled={sent || !conclusion.trim()}>
              <Icon name="seal" size={15} /> {sent ? t("pages.caseSolve.checking") : t("pages.caseSolve.submitVerdict")}
            </button>
          </div>

          {result && (
            <div className={`card side-card cs-result ${result.solved ? "is-solved" : "is-wrong"}`} aria-live="polite">
              <b className="cs-result-head">
                <Icon name={result.solved ? "check" : "x"} size={15} />
                {result.error ? result.error : result.solved ? t("pages.caseSolve.caseSolved") : t("pages.caseSolve.notQuiteRight")}
              </b>
              {!result.error && (
                <p className="sub" style={{ marginTop: 8, whiteSpace: "pre-wrap" }}>
                  {typeof result.feedback === "string" ? result.feedback : JSON.stringify(result.feedback)}
                </p>
              )}
              {!result.solved && result.correct_answer && (
                <p className="sub" style={{ marginTop: 6 }}>{t("pages.caseSolve.hint")}: <span lang="zh-CN">{result.correct_answer}</span></p>
              )}
            </div>
          )}
        </aside>
      </div>
    </Layout>
  );
}
