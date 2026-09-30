import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import AnimalAvatar from "../components/AnimalAvatar.jsx";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import { MotionButton } from "../components/ui.jsx";
import { useDashboard } from "../context/DashboardContext.jsx";
import { popIn } from "../motion.js";

const SUGGESTIONS = ["suggestion1", "suggestion2", "suggestion3"];

export default function Assistant() {
  const { t } = useTranslation();
  const { dashboard } = useDashboard() || {};
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const endRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, busy]);

  async function send(e) {
    e.preventDefault();
    const content = input.trim();
    if (!content || busy) return;
    const next = [...messages, { role: "user", content }];
    setMessages(next);
    setInput("");
    setError("");
    setBusy(true);
    try {
      const res = await api.post("/assistant/chat", { messages: next });
      setMessages((m) => [...m, { role: "assistant", content: res.reply }]);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  // A suggestion only fills the box; the learner still sends it themselves,
  // through exactly the same send() path.
  function applySuggestion(text) {
    setInput(text);
    inputRef.current?.focus();
  }

  const animal = dashboard?.animal;
  const animalSlug = animal?.slug;
  const weak = dashboard?.dna?.weak_areas || [];

  return (
    <Layout>
      <header className="page-head">
        <div>
          <div className="page-eyebrow">
            <Icon name="chat" size={13} /> {animal?.name || t("nav.assistant")}
          </div>
          <h1 className="h1">{t("pages.assistant.title")}</h1>
          <p className="sub">{t("pages.assistant.subtitle")}</p>
        </div>
        {dashboard && (
          <div className="kpi-row">
            <div className="kpi">
              <span className="kpi-value">HSK {dashboard.hsk_level}</span>
              <span className="kpi-label">{t("dashboard.level")}</span>
            </div>
            <div className="kpi">
              <span className="kpi-value">{dashboard.review_due ?? 0}</span>
              <span className="kpi-label">{t("nav.review")}</span>
            </div>
            <div className="kpi">
              <span className="kpi-value">{Math.round(dashboard.dna?.overall ?? 0)}%</span>
              <span className="kpi-label">{t("dashboard.learningDnaOverall")}</span>
            </div>
          </div>
        )}
      </header>

      <div className="ws">
        <div className="ws-main">
          <div className="card assistant-panel ws-chat">
            <div className="assistant-head">
              {animalSlug ? <AnimalAvatar slug={animalSlug} size={36} state={busy ? "thinking" : "idle"} /> : <Icon name="chat" size={22} />}
              <div style={{ minWidth: 0 }}>
                <b style={{ display: "block" }}>{animal?.name || t("nav.assistant")}</b>
                <span className="sub" style={{ fontSize: 12 }}>
                  {busy ? t("pages.assistant.thinking") : t("pages.assistant.scopeHint")}
                </span>
              </div>
            </div>

            <div className="assistant-log">
              {messages.length === 0 && (
                <div className="assistant-empty">
                  {animalSlug ? <AnimalAvatar slug={animalSlug} size={56} /> : <Icon name="chat" size={28} />}
                  <p className="sub" style={{ marginTop: 10 }}>{t("pages.assistant.scopeHint")}</p>
                </div>
              )}
              <AnimatePresence initial={false}>
                {messages.map((m, i) => (
                  <motion.div
                    key={i}
                    variants={popIn}
                    initial="initial"
                    animate="animate"
                    className={`bubble ${m.role === "user" ? "me" : "npc"}`}
                    style={{ alignSelf: m.role === "user" ? "flex-end" : "flex-start" }}
                  >
                    {m.content}
                  </motion.div>
                ))}
              </AnimatePresence>
              {busy && (
                <div className="bubble npc assistant-thinking">
                  <span className="dot" /><span className="dot" /><span className="dot" />
                </div>
              )}
              <div ref={endRef} />
            </div>

            {error && <p className="formerr" style={{ margin: "0 0 8px" }}>{error}</p>}

            <form onSubmit={send} className="assistant-input-row">
              <input
                ref={inputRef}
                className="input"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={t("pages.assistant.placeholder")}
                disabled={busy}
              />
              <MotionButton type="submit" className="btn primary" disabled={busy || !input.trim()}>
                <Icon name="arrowRight" size={15} /> {t("pages.assistant.send")}
              </MotionButton>
            </form>
          </div>
        </div>

        <aside className="ws-side">
          <div className="card side-card">
            <p className="side-title">{t("pages.assistant.tryAsking")}</p>
            <div className="prompt-chips">
              {SUGGESTIONS.map((key) => (
                <button key={key} type="button" className="prompt-chip" disabled={busy} onClick={() => applySuggestion(t(`pages.assistant.${key}`))}>
                  {t(`pages.assistant.${key}`)}
                </button>
              ))}
            </div>
          </div>

          <div className="card side-card">
            <p className="side-title">{t("dashboard.needsWork")}</p>
            {weak.length > 0 ? (
              <div className="row" style={{ gap: 6, flexWrap: "wrap" }}>
                {weak.map((w) => (
                  <span key={w} className="badge warn">{w}</span>
                ))}
              </div>
            ) : (
              <p className="sub">{t("pages.dna.none")}</p>
            )}
            <div className="side-links" style={{ marginTop: 14 }}>
              <Link to="/review"><button className="btn"><Icon name="clock" size={15} /> {t("nav.review")}</button></Link>
              <Link to="/dna"><button className="btn ghost"><Icon name="dna" size={15} /> {t("nav.dna")}</button></Link>
            </div>
          </div>
        </aside>
      </div>
    </Layout>
  );
}
