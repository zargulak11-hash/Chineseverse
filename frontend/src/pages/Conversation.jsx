import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api.js";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import MicRecorder from "../components/MicRecorder.jsx";
import { Empty, Loading } from "../components/ui.jsx";

export default function Conversation() {
  const { scenarioId } = useParams();
  const [sc, setSc] = useState(null);
  const [turnIndex, setTurnIndex] = useState(0);
  const [history, setHistory] = useState([0]); // turn_index values actually visited, in order
  const [error, setError] = useState("");
  const [text, setText] = useState("");
  const [result, setResult] = useState(null);
  const [chosen, setChosen] = useState(null); // the DialogueChoice the user picked at the current turn
  const [sent, setSent] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    api.get(`/world/scenarios/${scenarioId}`).then((data) => {
      setSc(data);
      setTurnIndex(0);
      setHistory([0]);
    }).catch((e) => setError(e.message));
  }, [scenarioId]);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turnIndex, result, chosen]);

  const dialogues = sc?.dialogues || [];
  // Branching means the next turn isn't necessarily "index + 1 in the
  // array" — a DialogueChoice's next_turn can jump anywhere (or past the
  // end, ending the conversation early), so turns are looked up by their
  // real turn_index, and the visited path is tracked separately from the
  // authored array order.
  const dialoguesByTurn = useMemo(() => {
    const map = {};
    for (const d of dialogues) map[d.turn_index] = d;
    return map;
  }, [dialogues]);

  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  if (!sc) return <Layout><Loading>Entering conversation…</Loading></Layout>;

  const current = dialoguesByTurn[turnIndex];
  const done = !current;

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

  function advanceTo(nextTurn) {
    setResult(null);
    setChosen(null);
    setText("");
    setTurnIndex(nextTurn);
    setHistory((h) => [...h, nextTurn]);
  }

  function pickChoice(choice) {
    setChosen(choice);
  }

  return (
    <Layout>
      <Link to="/world" className="sub">← Leave {sc.scenario_type === "case" ? "the case" : "the conversation"}</Link>
      <div className="row spread" style={{ marginTop: 10 }}>
        <div>
          <h1 className="h1">
            <Icon name={sc.is_case ? "search" : "chat"} size={20} style={{ verticalAlign: -3, marginRight: 6 }} />
            {sc.title}
          </h1>
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
          {history.map((turn, i) => {
            const d = dialoguesByTurn[turn];
            if (!d) return null;
            const isCurrent = turn === turnIndex;
            const hasChoices = d.choices && d.choices.length > 0;
            return (
              <div key={d.id}>
                <div className="bubble npc">
                  <span className="speaker">🧑 {d.speaker}</span>
                  {d.text}
                  {d.pinyin && <span className="pinyin">{d.pinyin}</span>}
                  {d.english && <span className="english">{d.english}</span>}
                </div>

                {hasChoices && isCurrent && !chosen && (
                  <div className="col" style={{ marginTop: 10, gap: 8 }}>
                    <p className="sub">What do you say?</p>
                    {d.choices.map((c) => (
                      <button key={c.id} className="option" onClick={() => pickChoice(c)}>
                        {c.label}
                      </button>
                    ))}
                  </div>
                )}
                {hasChoices && isCurrent && chosen && (
                  <>
                    <div className="bubble me">{chosen.label}</div>
                    {chosen.response_text && (
                      <div className="bubble npc">{chosen.response_text}</div>
                    )}
                    <div
                      className="bubble reaction"
                      style={
                        chosen.is_best
                          ? { borderColor: "var(--good)", color: "var(--good)" }
                          : undefined
                      }
                    >
                      <Icon name={chosen.is_best ? "check" : "chat"} size={13} style={{ verticalAlign: -2, marginRight: 4 }} />
                      {chosen.feedback}
                    </div>
                    <div className="row center" style={{ justifyContent: "center" }}>
                      <button
                        className="btn"
                        onClick={() => advanceTo(chosen.next_turn ?? d.turn_index + 1)}
                      >
                        Continue
                      </button>
                    </div>
                  </>
                )}

                {!hasChoices && d.requires_voice && isCurrent && !result && (
                  <div className="microw">
                    <MicRecorder onTranscript={(t) => setText(t)} disabled={sent} />
                    <div style={{ flex: 1, minWidth: 280 }}>
                      <p className="sub" style={{ marginBottom: 6 }}>{d.prompt}</p>
                      <textarea
                        className="input"
                        rows={2}
                        placeholder="Tap the mic and speak, or type what you would say in Chinese…"
                        value={text}
                        onChange={(e) => setText(e.target.value)}
                      />
                      <div className="row" style={{ marginTop: 8 }}>
                        <button className="btn primary" onClick={submit} disabled={sent || !text.trim()}>
                          {sent ? "Checking…" : "Speak"}
                        </button>
                        <button className="btn ghost" onClick={() => advanceTo(d.turn_index + 1)}>
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
                {!hasChoices && d.requires_voice && !isCurrent && <div className="bubble me" />}
                {!hasChoices && !d.requires_voice && isCurrent && (
                  <div className="microw">
                    <button className="btn primary" onClick={() => advanceTo(d.turn_index + 1)}>
                      Continue
                    </button>
                  </div>
                )}
                {!hasChoices && isCurrent && result && (
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
                        <button className="btn" onClick={() => advanceTo(d.turn_index + 1)}>Continue</button>
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
