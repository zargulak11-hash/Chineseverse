import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api.js";
import Layout from "../components/Layout.jsx";
import { Empty } from "../components/ui.jsx";

export default function Conversation() {
  const { scenarioId } = useParams();
  const [sc, setSc] = useState(null);
  const [step, setStep] = useState(0);
  const [error, setError] = useState("");
  const [text, setText] = useState("");
  const [starting, setStarting] = useState(false);
  const [result, setResult] = useState(null);
  const [sent, setSent] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    api.get(`/world/scenarios/${scenarioId}`).then(setSc).catch((e) => setError(e.message));
  }, [scenarioId]);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [step, result]);

  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  if (!sc) return <Layout><Empty>Entering conversation…</Empty></Layout>;

  const dialogues = sc.dialogues || [];
  const current = dialogues[step];

  async function submit() {
    if (!text.trim() || sent) return;
    setSent(true);
    setResult(null);
    try {
      const res = await api.post("/voice/attempt", {
        spoken_text: text.trim(),
        scenario_id: sc.id,
        dialogue_id: current?.id,
        prompt_text: current?.prompt,
        expected_keywords: current?.expected_keywords || [],
        response_time_ms: 1500,
      });
      setResult(res);
    } catch (e) {
      setResult({ error: e.message });
    } finally {
      setSent(false);
    }
  }

  function advance() {
    setResult(null);
    setText("");
    setStep((s) => s + 1);
  }

  const done = step >= dialogues.length;

  return (
    <Layout>
      <Link to="/world" className="sub">← Leave {sc.scenario_type === "case" ? "the case" : "the conversation"}</Link>
      <div className="row spread" style={{ marginTop: 10 }}>
        <div>
          <h1 className="h1">{sc.is_case ? "🕵️ " : "💬 "}{sc.title}</h1>
          <p className="sub">{sc.description}</p>
        </div>
        <span className="ilb">HSK {sc.min_hsk_level} · ★{sc.difficulty}</span>
      </div>

      {done ? (
        <div className="card center" style={{ marginTop: 20 }}>
          <div style={{ fontSize: 40 }}>🎉</div>
          <p>You made it through the whole conversation. That counts toward your DNA.</p>
          <Link to={`/world/${sc.slug}`}>
            <button className="btn primary">Back to the world</button>
          </Link>
        </div>
      ) : (
        <div className="chat" style={{ marginTop: 18 }}>
          {dialogues.slice(0, step + 1).map((d, i) => {
            const isCurrent = i === step;
            return (
              <div key={d.id}>
                <div className="bubble npc">
                  <span className="speaker">🧑 {d.speaker}</span>
                  {d.text}
                  {d.pinyin && <span className="pinyin">{d.pinyin}</span>}
                  {d.english && <span className="english">{d.english}</span>}
                </div>
                {d.requires_voice && isCurrent && (
                  <div className="microw">
                    <div style={{ flex: 1, minWidth: 280 }}>
                      <p className="sub" style={{ marginBottom: 6 }}>{d.prompt}</p>
                      <textarea
                        className="input"
                        rows={2}
                        placeholder="Type what you would say in Chinese…"
                        value={text}
                        onChange={(e) => setText(e.target.value)}
                      />
                      <div className="row" style={{ marginTop: 8 }}>
                        <button className="btn primary" onClick={submit} disabled={sent || !text.trim()}>
                          {sent ? "Checking…" : "Speak"}
                        </button>
                        <button className="btn ghost" onClick={advance}>
                          Skip for now
                        </button>
                          {d.expected_keywords?.length > 0 && (
                            <span className="muted" style={{ fontSize: 11 }}>
                              hint: {d.expected_keywords.join(" · ")}
                            </span>
                          )}
                      </div>
                    </div>
                  </div>
                )}
                {d.requires_voice && !isCurrent && <div className="bubble me" />}
                {!d.requires_voice && isCurrent && (
                  <div className="microw">
                    <button className="btn primary" onClick={advance}>
                      Continue
                    </button>
                  </div>
                )}
                {isCurrent && result && (
                  result.error ? (
                    <div className="bubble reaction">⚠️ {result.error}</div>
                  ) : (
                    <>
                      <div className="bubble me">
                        {text}
                      </div>
                      <div className="bubble reaction">
                        {result.reaction} · {result.attempt.overall.toFixed(0)}/100
                      </div>
                      {result.improvement && (
                        <div className="bubble reaction" style={{ borderColor: "var(--accent)", color: "var(--accent)" }}>
                          ✨ {result.improvement}
                        </div>
                      )}
                      <div className="row center" style={{ justifyContent: "center" }}>
                        <button className="btn" onClick={advance}>Continue</button>
                      </div>
                    </>
                  )
                )}
              </div>
            );
          })}
          <div ref={scrollRef} />
        </div>
      )}
    </Layout>
  );
}