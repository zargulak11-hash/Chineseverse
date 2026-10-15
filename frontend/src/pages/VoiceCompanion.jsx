import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../api.js";
import { useAuth } from "../auth.js";
import AnimalAvatar from "../components/AnimalAvatar.jsx";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import MicRecorder from "../components/MicRecorder.jsx";
import UserAvatar from "../components/UserAvatar.jsx";
import { Empty, Loading } from "../components/ui.jsx";
import VoiceFeedbackCard from "../components/VoiceFeedbackCard.jsx";
import { useDashboard } from "../context/DashboardContext.jsx";
import { deriveVoiceProfile, voiceTone } from "../voiceProfile.js";
import { speakChinese } from "../zhSpeech.js";

// The Daily Voice Companion: pick an animal for today's spoken chat, then
// talk. The picker is a roster with one animal previewed large (its voice
// can be heard before choosing); the chat is the same room as Roleplay --
// the animal on the left, the learner's own avatar on the right, the mic
// docked at the foot.

export default function VoiceCompanion() {
  const { t, i18n } = useTranslation();
  const { user } = useAuth();
  const { dashboard } = useDashboard();
  const [animals, setAnimals] = useState(null);
  const [error, setError] = useState("");
  // Session-only choice. This never reads or writes user.animal_id / the
  // dashboard's main companion -- picking a different animal here never
  // touches the permanent Learning Companion selected during onboarding.
  const [session, setSession] = useState(null); // the chosen Animal object, or null while picking
  const [preview, setPreview] = useState(null); // the animal shown large in the picker
  const [chat, setChat] = useState([]);
  const [history, setHistory] = useState([]); // role/content pairs sent to the AI for context
  const [msg, setMsg] = useState("");
  const [sending, setSending] = useState(false);
  const [speaking, setSpeaking] = useState(false); // true while TTS is actually voicing the reply
  const threadEnd = useRef(null);

  // Refetch on language change: description/personality are localized.
  useEffect(() => {
    api.get("/animals").then(setAnimals).catch((e) => setError(e.message));
  }, [i18n.language]);

  useEffect(() => {
    threadEnd.current?.scrollIntoView?.({ block: "nearest" });
  }, [chat.length]);

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

  // The preview's "hear the voice": the same voice profile the chat uses.
  function sample(animal) {
    speakChinese(t("voice.sampleLine"), {
      profile: deriveVoiceProfile(animal.personality_row),
      onStart: () => setSpeaking(true),
      onEnd: () => setSpeaking(false),
    });
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
  if (!animals) return <Layout><Loading>{t("voice.loading")}</Loading></Layout>;

  if (!session) {
    const p = preview || animals[0];
    return (
      <Layout>
        <header className="page-head">
          <div>
            <div className="page-eyebrow"><Icon name="mic" size={13} /> {t("nav.groupPlay")}</div>
            <h1 className="h1">{t("voice.title")}</h1>
            <p className="sub">{t("voice.subtitle")}</p>
          </div>
        </header>

        <div className="vc-pick">
          <ul className="vc-roster" aria-label={t("voice.title")}>
            {animals.map((a) => (
              <li key={a.id}>
                <button type="button" className={`vc-tile${p?.id === a.id ? " is-on" : ""}`} onClick={() => setPreview(a)}
                        aria-pressed={p?.id === a.id} onDoubleClick={() => chooseCompanion(a)}>
                  <AnimalAvatar slug={a.slug} size={56} />
                  <span className="vc-tile-name">{a.name}</span>
                </button>
              </li>
            ))}
          </ul>

          {p && (
            <section className="card vc-preview" aria-live="polite" key={p.id}>
              <div className="vc-preview-face">
                <AnimalAvatar slug={p.slug} size={140} state={speaking ? "speaking" : "idle"} />
              </div>
              <h2 className="vc-preview-name">{p.name}</h2>
              <p className="vc-preview-species">{p.species}</p>
              <span className="badge accent">{t(`voice.tone.${voiceTone(p.personality_row)}`)}</span>
              {p.personality && <p className="vc-preview-text">{p.personality}</p>}
              <div className="vc-preview-actions">
                <button type="button" className="btn" onClick={() => sample(p)}>
                  <Icon name="volume" size={15} /> {t("voice.hearVoice")}
                </button>
                <button type="button" className="btn primary" onClick={() => chooseCompanion(p)}>
                  <Icon name="mic" size={15} /> {t("voice.talkTo", { name: p.name })}
                </button>
              </div>
              <p className="sub vc-preview-note">{t("voice.sessionOnly")}</p>
            </section>
          )}
        </div>
      </Layout>
    );
  }

  const me = { avatar: dashboard?.avatar_url, name: user?.username };
  return (
    <Layout>
      <header className="card rp-room-head">
        <button type="button" className="icon-btn" onClick={endSession} aria-label={t("voice.change")} title={t("voice.change")}>
          <Icon name="arrowLeft" size={18} />
        </button>
        <span className="rp-avatar vc-head-avatar">
          <AnimalAvatar slug={session.slug} size={64} state={speaking ? "speaking" : sending ? "listening" : "idle"} />
        </span>
        <div className="rp-room-id">
          <div className="page-eyebrow"><Icon name="mic" size={13} /> {t("voice.title")}</div>
          <h1 className="h1 rp-room-title">{session.name}</h1>
          <p className="sub">{t("voice.sessionLabel", { voice: t(`voice.tone.${voiceTone(session.personality_row)}`) })}</p>
        </div>
        <button type="button" className="btn ghost small" onClick={endSession}>
          <Icon name="x" size={13} /> {t("voice.change")}
        </button>
      </header>

      <section className="card rp-chat vc-chat" aria-label={session.name}>
        <div className="rp-thread" aria-live="polite">
          {chat.length === 0 && (
            <div className="vc-empty">
              <AnimalAvatar slug={session.slug} size={88} state="idle" />
              <p className="sub">{t("voice.empty", { name: session.name })}</p>
            </div>
          )}
          {chat.map((c, i) =>
            c.from === "me" ? (
              <div key={i} className="rp-msg is-learner">
                <div className="rp-line is-learner"><p className="rp-zh" lang="zh-CN">{c.text}</p></div>
                <UserAvatar url={me.avatar} name={me.name} size={36} className="rp-me" />
              </div>
            ) : c.error ? (
              <div key={i} className="rp-msg is-partner" role="alert">
                <span className="rp-avatar"><AnimalAvatar slug={session.slug} size={40} state="confused" /></span>
                <div className="rp-line is-partner vc-error"><Icon name="alert" size={14} /> {c.error}</div>
              </div>
            ) : (
              <div key={i} className="rp-msg is-partner vc-reply">
                <span className="rp-avatar"><AnimalAvatar slug={session.slug} size={40} /></span>
                <div className="rp-line-stack vc-reply-stack">
                  <div className="rp-line is-partner">
                    <span className="rp-who">{session.name}</span>
                    <div className="rp-line-main">
                      <p className="rp-zh" lang="zh-CN">{c.reply}</p>
                      <button type="button" className="icon-btn rp-speak" aria-label={t("roleplay.listen")} title={t("roleplay.listen")}
                              onClick={() => speakChinese(c.reply, {
                                profile: deriveVoiceProfile(session.personality_row),
                                onStart: () => setSpeaking(true),
                                onEnd: () => setSpeaking(false),
                              })}>
                        <Icon name="volume" size={16} />
                      </button>
                    </div>
                  </div>
                  <VoiceFeedbackCard
                    attempt={c.attempt}
                    reaction={null}
                    companionSlug={session.slug}
                    companionName={session.name}
                  />
                </div>
              </div>
            )
          )}
          {sending && (
            <div className="rp-msg is-partner" role="status">
              <span className="rp-avatar"><AnimalAvatar slug={session.slug} size={40} state="thinking" /></span>
              <div className="rp-line is-partner rp-typing"><span className="rp-dots" aria-hidden="true"><i /><i /><i /></span></div>
            </div>
          )}
          <div ref={threadEnd} />
        </div>

        <div className="rp-compose">
          <div className="rp-compose-row">
            <input
              className="input"
              lang="zh-CN"
              placeholder={t("pages.conversation.micPlaceholder")}
              aria-label={t("pages.conversation.micPlaceholder")}
              value={msg}
              onChange={(e) => setMsg(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && send()}
              disabled={sending}
            />
            <span className="rp-mic">
              <MicRecorder onTranscript={(text) => send(text)} disabled={sending} lang="zh-CN" showStatus />
            </span>
            <button type="button" className="btn primary rp-send" onClick={() => send()} disabled={sending || !msg.trim()}>
              <Icon name="send" size={16} /> {sending ? "…" : t("pages.companion.send")}
            </button>
          </div>
        </div>
      </section>
    </Layout>
  );
}
