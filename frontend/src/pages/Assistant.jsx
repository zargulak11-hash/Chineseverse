import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../api.js";
import AnimalAvatar from "../components/AnimalAvatar.jsx";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import { MotionButton } from "../components/ui.jsx";
import { useDashboard } from "../context/DashboardContext.jsx";
import { popIn } from "../motion.js";

export default function Assistant() {
  const { t } = useTranslation();
  const { dashboard } = useDashboard() || {};
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const endRef = useRef(null);

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

  const animalSlug = dashboard?.animal?.slug;

  return (
    <Layout>
      <h1 className="h1">{t("pages.assistant.title")}</h1>
      <p className="sub">{t("pages.assistant.subtitle")}</p>

      <div className="card assistant-panel" style={{ marginTop: 16 }}>
        <div className="assistant-log">
          {messages.length === 0 && (
            <div className="assistant-empty">
              {animalSlug ? <AnimalAvatar slug={animalSlug} size={44} /> : <Icon name="chat" size={28} />}
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
    </Layout>
  );
}
