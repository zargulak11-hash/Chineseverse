import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import AnimalAvatar from "../components/AnimalAvatar.jsx";
import Layout from "../components/Layout.jsx";
import MicRecorder from "../components/MicRecorder.jsx";
import { Bar, Empty, Loading, Stat } from "../components/ui.jsx";
import VoiceFeedbackCard from "../components/VoiceFeedbackCard.jsx";
import { useDashboard } from "../context/DashboardContext.jsx";

const PHRASES = [
  "你好，加油！",
  "我要一杯咖啡",
  "谢谢您，再见",
  "我的狗叫小白",
  "请问火车站在哪里？",
  "今天天气很好",
];

export default function Companion() {
  const { dashboard, error } = useDashboard();
  const [chat, setChat] = useState([]);
  const [msg, setMsg] = useState("");

  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  if (!dashboard) return <Layout><Loading>Waking your companion…</Loading></Layout>;

  const animal = dashboard.animal;
  if (!animal) {
    return (
      <Layout>
        <Empty>
          You need a companion first.{" "}
          <Link to="/animals"><button className="btn primary">Choose one</button></Link>
        </Empty>
      </Layout>
    );
  }

  async function send(text) {
    const trimmed = (text || msg).trim();
    if (!trimmed) return;
    setMsg("");
    setChat((c) => [...c, { from: "me", text: trimmed }]);
    try {
      const r = await api.post("/voice/evaluate", {
        prompt_text: "",
        spoken_text: trimmed,
        expected_keywords: [],
      });
      setChat((c) => [
        ...c,
        {
          from: "npc",
          reaction: r.reaction,
          attempt: { ...r.scores, feedback: r.evaluation?.feedback },
        },
      ]);
    } catch (e) {
      setChat((c) => [...c, { from: "npc", reaction: "…", error: e.message }]);
    }
  }

  return (
    <Layout>
      <h1 className="h1">Your companion</h1>
      <p className="sub">Talk to {animal.name}. They react to how you speak their language.</p>

      <div className="grid grid-2" style={{ marginTop: 18 }}>
        <div className="card center">
          <div style={{ filter: "drop-shadow(0 8px 18px rgba(0,0,0,.45))" }}>
            <AnimalAvatar slug={animal.slug} size={104} />
          </div>
          <div className="h2" style={{ marginTop: 4 }}>{animal.name}</div>
          <div className="sub">{animal.species}</div>
          <div className="ilb" style={{ marginTop: 8 }}>{animal.personality}</div>
        </div>
        <div className="card">
          <h2 className="h2">Your rhythm</h2>
          <div className="scores" style={{ marginTop: 10 }}>
            <Stat label="Streak" value={`${dashboard.streak.current_streak}d`} tone="var(--accent)" />
            <Stat label="Daily goal" value={`${dashboard.daily_goal.minutes ?? 20}m`} tone="var(--accent2)" />
            <Stat label="HSK" value={dashboard.hsk_level} />
          </div>
          <p className="sub" style={{ marginTop: 12 }}>✨ {animal.special_ability}</p>
          <p className="sub">🎭 {animal.tone_style}</p>
          <p className="sub">🎯 {animal.preferred_mechanics}</p>
          <Link to="/pet-teacher">
            <button className="btn small ghost" style={{ marginTop: 10 }}>
              🧑‍🏫 {animal.name} wants you to catch its mistake
            </button>
          </Link>
        </div>
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <h2 className="h2">Free chat</h2>
        <div className="chat" style={{ marginTop: 8 }}>
          {chat.length === 0 && (
            <p className="sub center">Say something in Chinese — try one of these:</p>
          )}
          {chat.map((c, i) =>
            c.from === "me" ? (
              <div key={i} className="bubble me">{c.text}</div>
            ) : c.error ? (
              <div key={i} className="bubble reaction">⚠️ {c.error}</div>
            ) : (
              <VoiceFeedbackCard
                key={i}
                attempt={c.attempt}
                reaction={c.reaction}
                companionSlug={animal.slug}
                companionName={animal.name}
              />
            )
          )}
        </div>
        <div className="row" style={{ marginTop: 14, alignItems: "stretch" }}>
          <MicRecorder onTranscript={(t) => send(t)} />
          <input
            className="input"
            style={{ flex: 1 }}
            placeholder="Tap the mic and speak, or type in Chinese…"
            value={msg}
            onChange={(e) => setMsg(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send()}
          />
          <button className="btn primary" onClick={() => send()}>Send</button>
        </div>
        <div className="row" style={{ marginTop: 10 }}>
          {PHRASES.map((p) => (
            <button key={p} className="btn small ghost" onClick={() => send(p)}>{p}</button>
          ))}
        </div>
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <h2 className="h2">Recent voice sessions</h2>
        <VoiceHistory />
      </div>
    </Layout>
  );
}

function VoiceHistory() {
  const [rows, setRows] = useState(null);
  useEffect(() => {
    api.get("/voice/history").then(setRows).catch(() => setRows([]));
  }, []);
  if (!rows) return <Loading />;
  if (rows.length === 0) return <Empty>No sessions yet.</Empty>;
  return (
    <div className="col">
      {rows.slice(0, 5).map((v) => (
        <div key={v.id} className="row spread">
          <span className="muted">{v.spoken_text?.slice(0, 40) || "—"}</span>
          <div className="hbar" style={{ flex: 1, maxWidth: 240 }}>
            <Bar value={v.overall} />
            <span style={{ width: 34, textAlign: "right" }}>{v.overall.toFixed(0)}</span>
          </div>
        </div>
      ))}
    </div>
  );
}