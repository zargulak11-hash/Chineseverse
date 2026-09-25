import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import AnimalAvatar from "../components/AnimalAvatar.jsx";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import MicRecorder from "../components/MicRecorder.jsx";
import { Empty, Loading } from "../components/ui.jsx";
import VoiceFeedbackCard from "../components/VoiceFeedbackCard.jsx";
import { deriveVoiceProfile, voiceLabel } from "../voiceProfile.js";
import { speakChinese } from "../zhSpeech.js";

export default function VoiceCompanion() {
  const [animals, setAnimals] = useState(null);
  const [error, setError] = useState("");
  // Session-only choice. This never reads or writes user.animal_id / the
  // dashboard's main companion -- picking a different animal here never
  // touches the permanent Learning Companion selected during onboarding.
  const [session, setSession] = useState(null); // the chosen Animal object, or null while picking
  const [chat, setChat] = useState([]);
  const [history, setHistory] = useState([]); // role/content pairs sent to the AI for context
  const [msg, setMsg] = useState("");
  const [sending, setSending] = useState(false);
  const [speaking, setSpeaking] = useState(false); // true while TTS is actually voicing the reply

  useEffect(() => {
    api.get("/animals").then(setAnimals).catch((e) => setError(e.message));
  }, []);

  function chooseCompanion(animal) {
    setSession(animal);
    setChat([]);
    setHistory([]);
  }

  function endSession() {
    window.speechSynthesis?.cancel();
    setSession(null);
    setChat([]);
    setHistory([]);
    setSpeaking(false);
  }

  async function send(text) {
    const trimmed = (text || msg).trim();
    if (!trimmed || sending || !session) return;
    setMsg("");
    setSending(true);
    setChat((c) => [...c, { from: "me", text: trimmed }]);
    try {
      const res = await api.post("/voice/companion-chat", {
        animal_id: session.id,
        spoken_text: trimmed,
        history,
      });
      setHistory((h) => [
        ...h,
        { role: "user", content: trimmed },
        { role: "assistant", content: res.companion_reply },
      ]);
      setChat((c) => [
        ...c,
        {
          from: "npc",
          reply: res.companion_reply,
          attempt: { ...res.attempt, feedback: res.attempt.feedback },
        },
      ]);
      speakChinese(res.companion_reply, {
        profile: deriveVoiceProfile(session.personality_row),
        onStart: () => setSpeaking(true),
        onEnd: () => setSpeaking(false),
      });
    } catch (e) {
      setChat((c) => [...c, { from: "npc", error: e.message }]);
    } finally {
      setSending(false);
    }
  }

  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  if (!animals) return <Layout><Loading>Gathering companions…</Loading></Layout>;

  if (!session) {
    return (
      <Layout>
        <h1 className="h1">Daily Voice Companion</h1>
        <p className="sub">
          Choose your animal companion for today's conversation. This is just for this voice
          session — it never changes your main Learning Companion.
        </p>

        <div className="grid cards" style={{ marginTop: 18 }}>
          {animals.map((a) => (
            <div key={a.id} className="card hover animal" onClick={() => chooseCompanion(a)}>
              <div className="face">
                <AnimalAvatar slug={a.slug} size={76} />
              </div>
              <div className="name">{a.name}</div>
              <div className="species">{a.species}</div>
              <div className="statsrow">
                <span className="statpill">{voiceLabel(a.personality_row)}</span>
              </div>
              <button className="btn small primary" style={{ marginTop: 10 }}>
                Talk to {a.name}
              </button>
            </div>
          ))}
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="row spread">
        <div className="row">
          <AnimalAvatar
            slug={session.slug}
            size={56}
            state={speaking ? "speaking" : sending ? "listening" : "idle"}
          />
          <div>
            <h1 className="h1" style={{ marginBottom: 0 }}>{session.name}</h1>
            <p className="sub">{voiceLabel(session.personality_row)} · today's voice session</p>
          </div>
        </div>
        <button className="btn ghost small" onClick={endSession}>
          <Icon name="x" size={13} /> Change companion
        </button>
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <div className="chat" style={{ marginTop: 4 }}>
          {chat.length === 0 && (
            <p className="sub center">Say something in Chinese to start talking with {session.name}.</p>
          )}
          {chat.map((c, i) =>
            c.from === "me" ? (
              <div key={i} className="bubble me">{c.text}</div>
            ) : c.error ? (
              <div key={i} className="bubble reaction">⚠️ {c.error}</div>
            ) : (
              <div key={i}>
                <div className="bubble npc">
                  <span className="speaker">{session.name}</span>
                  {c.reply}
                </div>
                <VoiceFeedbackCard
                  attempt={c.attempt}
                  reaction={null}
                  companionSlug={session.slug}
                  companionName={session.name}
                />
              </div>
            )
          )}
        </div>
        <div className="row" style={{ marginTop: 14, alignItems: "stretch" }}>
          <MicRecorder onTranscript={(t) => send(t)} disabled={sending} lang="zh-CN" />
          <input
            className="input"
            style={{ flex: 1 }}
            placeholder="Tap the mic and speak, or type in Chinese…"
            value={msg}
            onChange={(e) => setMsg(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send()}
            disabled={sending}
          />
          <button className="btn primary" onClick={() => send()} disabled={sending}>
            {sending ? "…" : "Send"}
          </button>
        </div>
      </div>
    </Layout>
  );
}
