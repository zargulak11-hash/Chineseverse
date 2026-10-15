import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../auth.js";
import AnimalAvatar from "../components/AnimalAvatar.jsx";
import CompanionMemory from "../components/CompanionMemory.jsx";
import Layout from "../components/Layout.jsx";
import MicRecorder from "../components/MicRecorder.jsx";
import UserAvatar from "../components/UserAvatar.jsx";
import { Bar, Empty, Loading } from "../components/ui.jsx";
import VoiceFeedbackCard from "../components/VoiceFeedbackCard.jsx";
import { useDashboard } from "../context/DashboardContext.jsx";
import Icon from "../components/Icon.jsx";

// The learner's permanent companion (user.animal_id / dashboard.animal):
// on stage with the free chat beside it in the same room as Roleplay, its
// journal of what really happened below, and its traits and the recent
// voice sessions at the side.

const PHRASES = [
  "你好，加油！",
  "我要一杯咖啡",
  "谢谢您，再见",
  "我的狗叫小白",
  "请问火车站在哪里？",
  "今天天气很好",
];

export default function Companion() {
  const { t } = useTranslation();
  const { dashboard, error } = useDashboard();
  const { user } = useAuth();
  const [chat, setChat] = useState([]);
  const [msg, setMsg] = useState("");
  const [sending, setSending] = useState(false);

  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  if (!dashboard) return <Layout><Loading>{t("pages.companion.waking")}</Loading></Layout>;

  const animal = dashboard.animal;
  if (!animal) {
    return (
      <Layout>
        <Empty>
          {t("pages.companion.needCompanion")}{" "}
          <Link to="/animals"><button className="btn primary">{t("pages.companion.chooseOne")}</button></Link>
        </Empty>
      </Layout>
    );
  }

  async function send(text) {
    const trimmed = (text || msg).trim();
    if (!trimmed || sending) return;
    setMsg("");
    setSending(true);
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
    } finally {
      setSending(false);
    }
  }

  const me = { avatar: dashboard.avatar_url, name: user?.username };
  return (
    <Layout>
      <header className="page-head">
        <div>
          <div className="page-eyebrow"><Icon name="heart" size={13} /> {t("nav.groupYou")}</div>
          <h1 className="h1">{t("pages.companion.title")}</h1>
          <p className="sub">{t("pages.companion.subtitle", { name: animal.name })}</p>
        </div>
        <div className="kpi-row">
          <div className="kpi"><span className="kpi-value">{dashboard.streak.current_streak}d</span><span className="kpi-label">{t("pages.companion.streak")}</span></div>
          <div className="kpi"><span className="kpi-value">{dashboard.daily_goal.daily_goal_minutes}m</span><span className="kpi-label">{t("pages.profile.dailyGoal")}</span></div>
          <div className="kpi"><span className="kpi-value">HSK {dashboard.hsk_level}</span><span className="kpi-label">{t("dashboard.level")}</span></div>
        </div>
      </header>

      <div className="ws">
        <div className="ws-main">
          {/* The companion on stage, and the free chat with it. */}
          <section className="card rp-chat cp-room" aria-labelledby="cp-chat-title">
            <div className="cp-stage">
              <AnimalAvatar slug={animal.slug} size={132} state={sending ? "listening" : "idle"} />
              <div className="cp-stage-id">
                <h2 className="cp-name" id="cp-chat-title">{animal.name}</h2>
                <p className="cp-species">{animal.species}</p>
                {animal.personality && <span className="badge accent">{animal.personality}</span>}
                <p className="sub cp-hint">{t("pages.companion.sayInChinese")}</p>
              </div>
            </div>
            <div className="rp-thread cp-thread" aria-live="polite">
              {chat.map((c, i) =>
                c.from === "me" ? (
                  <div key={i} className="rp-msg is-learner">
                    <div className="rp-line is-learner"><p className="rp-zh" lang="zh-CN">{c.text}</p></div>
                    <UserAvatar url={me.avatar} name={me.name} size={36} className="rp-me" />
                  </div>
                ) : c.error ? (
                  <div key={i} className="rp-msg is-partner" role="alert">
                    <span className="rp-avatar"><AnimalAvatar slug={animal.slug} size={40} state="confused" /></span>
                    <div className="rp-line is-partner vc-error"><Icon name="alert" size={14} /> {c.error}</div>
                  </div>
                ) : (
                  <div key={i} className="rp-msg is-partner cp-feedback">
                    <VoiceFeedbackCard
                      attempt={c.attempt}
                      reaction={c.reaction}
                      companionSlug={animal.slug}
                      companionName={animal.name}
                    />
                  </div>
                )
              )}
              {sending && (
                <div className="rp-msg is-partner" role="status">
                  <span className="rp-avatar"><AnimalAvatar slug={animal.slug} size={40} state="thinking" /></span>
                  <div className="rp-line is-partner rp-typing"><span className="rp-dots" aria-hidden="true"><i /><i /><i /></span></div>
                </div>
              )}
            </div>
            <div className="rp-compose">
              <div className="cp-phrases" role="group" aria-label={t("pages.companion.tryPhrase")}>
                {PHRASES.map((ph) => (
                  <button key={ph} type="button" className="rp-chip cp-phrase" lang="zh-CN" onClick={() => send(ph)} disabled={sending}>{ph}</button>
                ))}
              </div>
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
                <span className="rp-mic"><MicRecorder onTranscript={(txt) => send(txt)} disabled={sending} showStatus /></span>
                <button type="button" className="btn primary rp-send" onClick={() => send()} disabled={sending || !msg.trim()}>
                  <Icon name="send" size={16} /> {t("pages.companion.send")}
                </button>
              </div>
            </div>
          </section>

          <section className="card" aria-labelledby="cp-journal">
            <h2 className="h2" id="cp-journal">{t("companionMemory.journal")}</h2>
            <p className="sub">{t("companionMemory.journalHint", { name: animal.name })}</p>
            <CompanionMemory animal={animal} full />
          </section>
        </div>

        <aside className="ws-side">
          <div className="card side-card">
            <p className="side-title">{t("pages.companion.yourRhythm")}</p>
            <ul className="cp-traits">
              <li><Icon name="sparkles" size={14} /> <span>{animal.special_ability}</span></li>
              <li><Icon name="chat" size={14} /> <span>{animal.tone_style}</span></li>
              <li><Icon name="target" size={14} /> <span>{animal.preferred_mechanics}</span></li>
            </ul>
            <Link to="/pet-teacher" className="btn small" style={{ marginTop: 12 }}>
              <Icon name="teach" size={14} /> {t("pages.companion.catchMistake", { name: animal.name })}
            </Link>
          </div>
          <div className="card side-card">
            <p className="side-title">{t("pages.companion.recentSessions")}</p>
            <VoiceHistory />
          </div>
        </aside>
      </div>
    </Layout>
  );
}

function VoiceHistory() {
  const { t } = useTranslation();
  const [rows, setRows] = useState(null);
  useEffect(() => {
    api.get("/voice/history").then(setRows).catch(() => setRows([]));
  }, []);
  if (!rows) return <Loading />;
  if (rows.length === 0) return <Empty>{t("pages.companion.noSessions")}</Empty>;
  return (
    <ul className="cp-sessions">
      {rows.slice(0, 5).map((v) => (
        <li key={v.id}>
          <span className="cp-session-text" lang="zh-CN">{v.spoken_text?.slice(0, 40) || "—"}</span>
          <span className="cp-session-score">
            <Bar value={v.overall} />
            <b>{v.overall.toFixed(0)}</b>
          </span>
        </li>
      ))}
    </ul>
  );
}
