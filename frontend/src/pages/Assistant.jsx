import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api.js";
import AnimalAvatar from "../components/AnimalAvatar.jsx";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import MicRecorder, { micSupported } from "../components/MicRecorder.jsx";
import { MotionButton } from "../components/ui.jsx";
import { useDashboard } from "../context/DashboardContext.jsx";
import { popIn } from "../motion.js";
import { canSpeakChinese, canSpeakLocale, speakText, stopSpeaking } from "../zhSpeech.js";

const SUGGESTIONS = ["suggestion1", "suggestion2", "suggestion3", "suggestion4"];
const HISTORY_KEY = "cv_assistant_history";
const MAX_FILES = 3;
const IMAGE_TYPES = ["image/png", "image/jpeg", "image/webp", "image/gif"];
const TEXT_TYPES = ["text/plain", "text/markdown", "text/csv"];
const MAX_PDF = 6 * 1024 * 1024;
const MAX_TEXT = 200 * 1024;
const MAX_IMAGE_SOURCE = 20 * 1024 * 1024;
const IMAGE_EDGE = 1600; // images are scaled down before upload: plenty to read text
const SPEECH_LANG = { en: "en-US", ru: "ru-RU", tg: "tg-TJ", zh: "zh-CN" };

// The model answers in light Markdown (**bold**, "* " bullets, "### " titles).
// Render just those as React elements -- never as HTML, so a reply can't
// inject markup -- instead of showing the raw asterisks.
function renderInline(text, keyBase) {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith("**") && part.endsWith("**") && part.length > 4
      ? <strong key={`${keyBase}-${i}`}>{part.slice(2, -2)}</strong>
      : part.replace(/(^|\s)\*([^*\s][^*]*)\*(?=\s|$|[.,!?;:])/g, "$1$2")
  );
}

function renderReply(text) {
  return text.split("\n").map((line, i, lines) => {
    const bullet = line.match(/^\s*[*-]\s+(.*)$/);
    const heading = line.match(/^\s*#{1,6}\s+(.*)$/);
    const body = bullet ? `• ${bullet[1]}` : heading ? heading[1] : line;
    const content = renderInline(body, i);
    return (
      <span key={i} className={heading ? "assistant-h" : undefined}>
        {heading ? <strong>{content}</strong> : content}
        {i < lines.length - 1 ? "\n" : null}
      </span>
    );
  });
}

function loadHistory() {
  try {
    const saved = JSON.parse(sessionStorage.getItem(HISTORY_KEY) || "[]");
    return Array.isArray(saved) ? saved.filter((m) => m && m.role && typeof m.content === "string") : [];
  } catch {
    return [];
  }
}

function readAsDataUrl(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(blob);
  });
}

// Scale a photo/screenshot down to IMAGE_EDGE on its long side as JPEG, so a
// phone photo becomes a few hundred KB instead of several MB.
async function shrinkImage(file) {
  const url = URL.createObjectURL(file);
  try {
    const img = await new Promise((resolve, reject) => {
      const el = new Image();
      el.onload = () => resolve(el);
      el.onerror = reject;
      el.src = url;
    });
    const scale = Math.min(1, IMAGE_EDGE / Math.max(img.naturalWidth, img.naturalHeight));
    if (scale === 1 && file.size < 900 * 1024 && file.type !== "image/gif") {
      return { mime: file.type, dataUrl: await readAsDataUrl(file) };
    }
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(img.naturalWidth * scale);
    canvas.height = Math.round(img.naturalHeight * scale);
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = "#fff"; // transparent PNG areas become white, not black
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    return { mime: "image/jpeg", dataUrl: canvas.toDataURL("image/jpeg", 0.85) };
  } finally {
    URL.revokeObjectURL(url);
  }
}

export default function Assistant() {
  const { t, i18n } = useTranslation();
  const { dashboard } = useDashboard() || {};
  const [params, setParams] = useSearchParams();
  const [messages, setMessages] = useState(loadHistory);
  const [input, setInput] = useState("");
  const [files, setFiles] = useState([]); // {id, name, mime, size, data, preview}
  const [preparing, setPreparing] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState("");
  const [speaking, setSpeaking] = useState(null);
  const [micLang, setMicLang] = useState("ui");
  const abortRef = useRef(null);
  const endRef = useRef(null);
  const inputRef = useRef(null);
  const fileRef = useRef(null);

  // What the learner opened the assistant from (a grammar page, a story
  // sentence, a lesson). Only ids and the selected sentence go to the
  // server, which reads the rest from the database.
  const pageContext = {
    grammar_id: params.get("grammar") ? Number(params.get("grammar")) : undefined,
    lesson_id: params.get("lesson") ? Number(params.get("lesson")) : undefined,
    story: params.get("story") || undefined,
    chapter: params.get("chapter") ? Number(params.get("chapter")) : undefined,
    text: params.get("text") || undefined,
  };
  const contextKind = pageContext.text ? "sentence" : pageContext.grammar_id ? "grammar"
    : pageContext.story ? "story" : pageContext.lesson_id ? "lesson" : null;

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, streaming]);

  // Text only (never attachment data) is kept for this browser tab, so
  // looking something up on another page doesn't lose the conversation.
  useEffect(() => {
    if (streaming) return;
    try {
      sessionStorage.setItem(HISTORY_KEY, JSON.stringify(messages.slice(-30).map(({ role, content, status, source, fileNames }) =>
        ({ role, content, status, source, fileNames }))));
    } catch {
      /* storage unavailable: the conversation just isn't kept */
    }
  }, [messages, streaming]);

  // Leaving the page stops a running answer and any speech.
  useEffect(() => () => {
    abortRef.current?.abort();
    stopSpeaking();
  }, []);

  async function addFiles(list) {
    setError("");
    const picked = Array.from(list || []);
    if (files.length + picked.length > MAX_FILES) {
      setError(t("pages.assistant.tooManyFiles", { count: MAX_FILES }));
      return;
    }
    setPreparing(true);
    const next = [];
    try {
      for (const file of picked) {
        const id = `${file.name}-${file.size}-${Date.now()}`;
        if (IMAGE_TYPES.includes(file.type)) {
          if (file.size > MAX_IMAGE_SOURCE) throw new Error(t("pages.assistant.fileTooLarge", { name: file.name }));
          const { mime, dataUrl } = await shrinkImage(file);
          next.push({ id, name: file.name, mime, size: file.size, data: dataUrl.split(",")[1], preview: dataUrl });
        } else if (file.type === "application/pdf") {
          if (file.size > MAX_PDF) throw new Error(t("pages.assistant.fileTooLarge", { name: file.name }));
          next.push({ id, name: file.name, mime: file.type, size: file.size, data: (await readAsDataUrl(file)).split(",")[1] });
        } else if (TEXT_TYPES.includes(file.type) || /\.(txt|md|csv)$/i.test(file.name)) {
          if (file.size > MAX_TEXT) throw new Error(t("pages.assistant.fileTooLarge", { name: file.name }));
          next.push({ id, name: file.name, mime: file.type || "text/plain", size: file.size, data: (await readAsDataUrl(file)).split(",")[1] });
        } else {
          throw new Error(t("pages.assistant.fileType", { name: file.name }));
        }
      }
      setFiles((f) => [...f, ...next]);
    } catch (e) {
      setError(e.message || t("pages.assistant.fileRead"));
    } finally {
      setPreparing(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function run(history) {
    const controller = new AbortController();
    abortRef.current = controller;
    setStreaming(true);
    setError("");
    setMessages([...history, { role: "assistant", content: "", status: "streaming" }]);
    const update = (fn) => setMessages((m) => {
      const copy = m.slice();
      copy[copy.length - 1] = fn(copy[copy.length - 1]);
      return copy;
    });
    // Only the last 12 turns go to the model; attachment bytes only for the
    // message that carries them (the server keeps just the latest anyway).
    const payload = history.slice(-12).map((m) => ({
      role: m.role,
      content: m.content,
      attachments: (m.files || []).map(({ name, mime, data }) => ({ name, mime, data })),
    }));
    const context = Object.fromEntries(Object.entries(pageContext).filter(([, v]) => v !== undefined));
    try {
      await api.stream("/assistant/chat/stream", { messages: payload, context: contextKind ? context : undefined }, {
        signal: controller.signal,
        onEvent: (ev) => {
          if (ev.type === "meta") update((m) => ({ ...m, source: ev.source }));
          else if (ev.type === "delta") update((m) => ({ ...m, content: m.content + ev.text }));
          else if (ev.type === "done") update((m) => ({ ...m, status: "done" }));
          else if (ev.type === "error") update((m) => ({ ...m, status: "error" }));
        },
      });
      update((m) => (m.status === "streaming" ? { ...m, status: "done" } : m));
    } catch (err) {
      if (err.name === "AbortError") {
        update((m) => ({ ...m, status: "stopped" }));
      } else {
        // Nothing arrived: drop the empty bubble and show the error with Retry.
        setMessages((m) => (m[m.length - 1]?.content ? m.map((x, i) => (i === m.length - 1 ? { ...x, status: "error" } : x)) : m.slice(0, -1)));
        setError(err.message);
      }
    } finally {
      if (abortRef.current === controller) abortRef.current = null;
      setStreaming(false);
    }
  }

  function send(e) {
    e.preventDefault();
    const content = input.trim() || (files.length ? t("pages.assistant.explainFile") : "");
    if (!content || streaming || preparing) return;
    const userMsg = { role: "user", content, files, fileNames: files.map((f) => f.name), previews: files.map((f) => f.preview).filter(Boolean) };
    setInput("");
    setFiles([]);
    run([...messages.filter((m) => m.status !== "streaming" && m.content), userMsg]);
  }

  function stop() {
    abortRef.current?.abort();
  }

  // Ask the last question again: drop the answer that was stopped or failed.
  function retry() {
    let history = messages.slice();
    while (history.length && history[history.length - 1].role === "assistant") history = history.slice(0, -1);
    if (history.length) run(history);
  }

  function clearChat() {
    abortRef.current?.abort();
    stopSpeaking();
    setSpeaking(null);
    setMessages([]);
    setError("");
  }

  function toggleSpeak(i, text) {
    if (speaking === i) {
      stopSpeaking();
      setSpeaking(null);
      return;
    }
    setSpeaking(i);
    speakText(text, i18n.language, { onEnd: () => setSpeaking((s) => (s === i ? null : s)) });
  }

  function applySuggestion(text) {
    setInput(text);
    inputRef.current?.focus();
  }

  function dropContext() {
    setParams({}, { replace: true });
  }

  const animal = dashboard?.animal;
  const animalSlug = animal?.slug;
  const weak = dashboard?.dna?.weak_areas || [];
  const last = messages[messages.length - 1];
  const canRetry = !streaming && messages.some((m) => m.role === "user") && (error || ["stopped", "error"].includes(last?.status));
  const ttsOk = canSpeakChinese() || canSpeakLocale(i18n.language);
  const contextSuggestions = contextKind ? [`context.${contextKind}Ask1`, `context.${contextKind}Ask2`] : [];

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
              {animalSlug ? <AnimalAvatar slug={animalSlug} size={36} state={streaming ? "thinking" : "idle"} /> : <Icon name="chat" size={22} />}
              <div style={{ minWidth: 0, flex: 1 }}>
                <b style={{ display: "block" }}>{animal?.name || t("nav.assistant")}</b>
                <span className="sub" style={{ fontSize: "var(--text-xs)" }} aria-live="polite">
                  {streaming ? t("pages.assistant.writing") : t("pages.assistant.scopeHint")}
                </span>
              </div>
              {messages.length > 0 && (
                <button type="button" className="btn small ghost" onClick={clearChat}>
                  <Icon name="trash" size={13} /> {t("pages.assistant.newChat")}
                </button>
              )}
            </div>

            <div className="assistant-log" aria-live="polite" aria-busy={streaming}>
              {messages.length === 0 && (
                <div className="assistant-empty">
                  {animalSlug ? <AnimalAvatar slug={animalSlug} size={56} /> : <Icon name="chat" size={28} />}
                  <p className="sub" style={{ marginTop: 10 }}>{t("pages.assistant.emptyHint")}</p>
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
                    {m.role === "user" ? (
                      <>
                        {m.previews?.length > 0 && (
                          <span className="assistant-thumbs">
                            {m.previews.map((src, k) => <img key={k} src={src} alt={m.fileNames?.[k] || ""} />)}
                          </span>
                        )}
                        {m.fileNames?.length > 0 && !m.previews?.length && (
                          <span className="assistant-file-note"><Icon name="book" size={13} /> {m.fileNames.join(", ")}</span>
                        )}
                        {m.content}
                      </>
                    ) : (
                      <>
                        {m.content ? renderReply(m.content) : (
                          <span className="assistant-thinking" aria-label={t("pages.assistant.thinking")}>
                            <span className="dot" /><span className="dot" /><span className="dot" />
                          </span>
                        )}
                        {m.status === "stopped" && <span className="assistant-status">{t("pages.assistant.stopped")}</span>}
                        {m.status === "error" && <span className="assistant-status bad">{t("pages.assistant.interrupted")}</span>}
                        {m.source === "offline" && m.status === "done" && <span className="assistant-status">{t("pages.assistant.offlineNote")}</span>}
                        {m.content && m.status !== "streaming" && ttsOk && (
                          <span className="assistant-tools">
                            <button
                              type="button"
                              className="icon-btn"
                              aria-pressed={speaking === i}
                              aria-label={speaking === i ? t("pages.assistant.stopListening") : t("pages.assistant.listen")}
                              title={!canSpeakLocale(i18n.language) ? t("pages.assistant.listenChineseOnly") : undefined}
                              onClick={() => toggleSpeak(i, m.content)}
                            >
                              <Icon name={speaking === i ? "stop" : "ear"} size={15} />
                            </button>
                          </span>
                        )}
                      </>
                    )}
                  </motion.div>
                ))}
              </AnimatePresence>
              <div ref={endRef} />
            </div>

            {error && <p className="formerr" role="alert" style={{ margin: "0 0 8px" }}>{error}</p>}

            {(contextKind || files.length > 0 || canRetry) && (
              <div className="assistant-tray">
                {contextKind && (
                  <span className="assistant-chip">
                    <Icon name="mapPin" size={13} /> {t(`pages.assistant.context.${contextKind}`)}
                    {pageContext.text && <b lang="zh-CN"> {pageContext.text}</b>}
                    <button type="button" className="icon-btn" aria-label={t("pages.assistant.dropContext")} onClick={dropContext}>
                      <Icon name="x" size={13} />
                    </button>
                  </span>
                )}
                {files.map((f) => (
                  <span key={f.id} className="assistant-chip">
                    {f.preview ? <img src={f.preview} alt="" /> : <Icon name="book" size={13} />}
                    <span className="assistant-chip-name">{f.name}</span>
                    <span className="sub">{f.mime === "application/pdf" ? "PDF" : f.mime.startsWith("image/") ? t("pages.assistant.image") : t("pages.assistant.textFile")}</span>
                    <button type="button" className="icon-btn" aria-label={t("pages.assistant.removeFile", { name: f.name })} onClick={() => setFiles((x) => x.filter((y) => y.id !== f.id))}>
                      <Icon name="x" size={13} />
                    </button>
                  </span>
                ))}
                {canRetry && (
                  <button type="button" className="btn small" onClick={retry}>
                    <Icon name="route" size={13} /> {t("pages.assistant.retry")}
                  </button>
                )}
              </div>
            )}

            <form onSubmit={send} className="assistant-input-row">
              <input
                ref={fileRef}
                type="file"
                hidden
                multiple
                accept="image/png,image/jpeg,image/webp,image/gif,application/pdf,text/plain,text/markdown,text/csv,.txt,.md,.csv"
                onChange={(e) => addFiles(e.target.files)}
              />
              <button
                type="button"
                className="icon-btn assistant-attach"
                aria-label={t("pages.assistant.attach")}
                title={t("pages.assistant.attachHint")}
                disabled={streaming || preparing || files.length >= MAX_FILES}
                onClick={() => fileRef.current?.click()}
              >
                <Icon name="plus" size={18} />
              </button>
              <textarea
                ref={inputRef}
                className="input"
                rows={1}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) send(e);
                }}
                placeholder={preparing ? t("pages.assistant.preparingFile") : t("pages.assistant.placeholder")}
                aria-label={t("pages.assistant.placeholder")}
                maxLength={4000}
              />
              {micSupported && (
                <select
                  className="input assistant-mic-lang"
                  value={micLang}
                  onChange={(e) => setMicLang(e.target.value)}
                  aria-label={t("pages.assistant.micLanguage")}
                  disabled={streaming}
                >
                  <option value="ui">{t("pages.assistant.micUi")}</option>
                  {i18n.language !== "zh" && <option value="zh">中文</option>}
                </select>
              )}
              <MicRecorder
                lang={micLang === "zh" ? "zh-CN" : SPEECH_LANG[i18n.language] || "en-US"}
                disabled={streaming}
                showStatus
                onTranscript={(txt) => {
                  setInput((prev) => (prev ? `${prev} ${txt}` : txt));
                  inputRef.current?.focus();
                }}
              />
              {streaming ? (
                <button type="button" className="btn danger" onClick={stop}>
                  <Icon name="stop" size={15} /> {t("pages.assistant.stop")}
                </button>
              ) : (
                <MotionButton type="submit" className="btn primary" disabled={preparing || (!input.trim() && !files.length)}>
                  <Icon name="arrowRight" size={15} /> {t("pages.assistant.send")}
                </MotionButton>
              )}
            </form>
          </div>
        </div>

        <aside className="ws-side">
          <div className="card side-card">
            <p className="side-title">{t("pages.assistant.tryAsking")}</p>
            <div className="prompt-chips">
              {[...contextSuggestions.map((k) => `pages.assistant.${k}`), ...SUGGESTIONS.map((k) => `pages.assistant.${k}`)].map((key) => (
                <button key={key} type="button" className="prompt-chip" disabled={streaming} onClick={() => applySuggestion(t(key))}>
                  {t(key)}
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

          <div className="card side-card">
            <p className="side-title">{t("pages.assistant.howTitle")}</p>
            <ul className="assistant-how">
              <li>{t("pages.assistant.how1")}</li>
              <li>{t("pages.assistant.how2")}</li>
              <li>{t("pages.assistant.how3")}</li>
            </ul>
          </div>
        </aside>
      </div>
    </Layout>
  );
}
