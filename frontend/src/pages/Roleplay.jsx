import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api.js";
import Art, { placeArt } from "../components/Art.jsx";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import MicRecorder from "../components/MicRecorder.jsx";
import { Empty, Loading } from "../components/ui.jsx";
import { useDashboard } from "../context/DashboardContext.jsx";
import { useApi } from "../hooks/useApi.js";
import { speakChinese } from "../zhSpeech.js";

// AI roleplay (services/roleplay.py): hand-written real-life scenarios, played
// in the learner's own words with an AI partner that answers what they
// actually said and corrects it. Everything shown -- replies, corrections,
// goals, the summary -- comes from the server, which validated what the
// model returned; this page never invents a line.

export default function RoleplayHub() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { data, error } = useApi("/roleplay/scenarios");
  const { data: recent } = useApi("/roleplay/sessions");
  const [starting, setStarting] = useState(null);
  const [startError, setStartError] = useState("");

  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  if (!data) return <Layout><Loading /></Layout>;

  async function start(slug) {
    setStarting(slug);
    setStartError("");
    try {
      const s = await api.post("/roleplay/sessions", { scenario: slug });
      navigate(`/roleplay/${s.id}`);
    } catch (e) {
      setStartError(e.message);
      setStarting(null);
    }
  }

  const titleOf = Object.fromEntries(data.scenarios.map((s) => [s.slug, s.title]));
  return (
    <Layout>
      <header className="page-head">
        <div>
          <div className="page-eyebrow"><Icon name="chat" size={13} /> {t("nav.groupUse")}</div>
          <h1 className="h1">{t("roleplay.title")}</h1>
          <p className="sub">{t("roleplay.subtitle")}</p>
        </div>
      </header>

      {!data.ai_available && (
        <div className="card rp-unavailable" style={{ marginTop: 16 }}>
          <h2 className="h2">{t("roleplay.unavailableTitle")}</h2>
          <p className="sub">{t("roleplay.unavailableText")}</p>
          <Link to="/real-chinese" className="btn" style={{ marginTop: 12 }}>{t("roleplay.toScenes")}</Link>
        </div>
      )}
      {startError && <p className="formerr" role="alert">{startError}</p>}

      <div className="grid cards" style={{ marginTop: 16 }}>
        {data.scenarios.map((s) => (
          <article key={s.slug} className={`card rp-scenario${s.unlocked ? "" : " is-locked"}`}>
            <div className="row" style={{ margin: 0, gap: 12, alignItems: "center" }}>
              <Art name={placeArt(s.icon)} size={52} />
              <div style={{ minWidth: 0 }}>
                <h2 className="h2" style={{ margin: 0 }}>{s.title}</h2>
                <span className="badge">HSK {s.level}</span>
                {s.played > 0 && <span className="sub rp-played">{t("roleplay.played", { count: s.played })}</span>}
              </div>
            </div>
            <p className="side-title" style={{ marginTop: 14 }}>{t("roleplay.goals")}</p>
            <ul className="rp-goals">
              {s.goals.map((g, i) => <li key={i}>{g}</li>)}
            </ul>
            {s.unlocked ? (
              <button type="button" className="btn primary" disabled={!data.ai_available || starting !== null}
                      onClick={() => start(s.slug)}>
                {starting === s.slug ? t("roleplay.starting") : t("roleplay.start")}
              </button>
            ) : (
              <span className="sub"><Icon name="lock" size={13} /> {t("roleplay.locked", { level: s.level })}</span>
            )}
          </article>
        ))}
      </div>

      {recent?.length > 0 && (
        <section className="card" style={{ marginTop: 24 }} aria-labelledby="rp-recent">
          <h2 className="h2" id="rp-recent">{t("roleplay.recent")}</h2>
          <ul className="rp-recent">
            {recent.map((r) => (
              <li key={r.id}>
                <Link to={`/roleplay/${r.id}`} className="fix-row">
                  <span className="fix-text">
                    <b>{titleOf[r.scenario] || r.scenario}</b>
                    <span className="sub">{t("roleplay.messages", { count: r.messages })}</span>
                  </span>
                  <span className="badge">{r.status === "finished" ? t("roleplay.seeSummary") : t("roleplay.continue")}</span>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}
    </Layout>
  );
}

function PartnerLine({ turn, role }) {
  const { t } = useTranslation();
  const [pinyin, setPinyin] = useState(false);
  const [translation, setTranslation] = useState(false);
  return (
    <div className="rp-line is-partner">
      <span className="rp-who" lang="zh-CN">{role}</span>
      <p className="rp-zh" lang="zh-CN">{turn.zh}</p>
      {pinyin && turn.pinyin && <p className="sub rp-pinyin">{turn.pinyin}</p>}
      {translation && turn.translation && <p className="sub">{turn.translation}</p>}
      <div className="rp-tools">
        <button type="button" className="btn small ghost" onClick={() => speakChinese(turn.zh)}>
          <Icon name="ear" size={13} /> {t("roleplay.listen")}
        </button>
        {turn.pinyin && (
          <button type="button" className={`btn small${pinyin ? " primary" : " ghost"}`} aria-pressed={pinyin}
                  onClick={() => setPinyin((v) => !v)}>
            {t("roleplay.showPinyin")}
          </button>
        )}
        {turn.translation && (
          <button type="button" className={`btn small${translation ? " primary" : " ghost"}`} aria-pressed={translation}
                  onClick={() => setTranslation((v) => !v)}>
            {t("roleplay.showTranslation")}
          </button>
        )}
      </div>
    </div>
  );
}

function LearnerLine({ turn }) {
  const { t } = useTranslation();
  const fb = turn.feedback;
  return (
    <div className="rp-line is-learner">
      <p className="rp-zh" lang="zh-CN">{turn.text}</p>
      {fb ? (
        <div className="practice-why">
          <p><b>{t("roleplay.corrected")}</b> <span lang="zh-CN">{fb.corrected}</span></p>
          <p>{fb.explanation}</p>
        </div>
      ) : (
        <span className="badge good rp-ok">{t("roleplay.wellSaid")}</span>
      )}
    </div>
  );
}

// A word card that can be put on the learner's review schedule (the existing
// POST /vocab/{id}/track). Words outside the curriculum can't be reviewed,
// so they have no button.
function WordChip({ word, saved, onSave }) {
  const { t } = useTranslation();
  return (
    <li className="rp-word">
      <span>
        <b lang="zh-CN">{word.zh}</b> <span className="sub">{word.pinyin}</span>
        {word.meaning && <span className="sub rp-word-meaning">{word.meaning}</span>}
      </span>
      {word.word_id && (
        <button type="button" className={`btn small${saved ? " ghost" : ""}`} disabled={saved} onClick={() => onSave(word)}>
          {saved ? t("roleplay.saved") : t("roleplay.save")}
        </button>
      )}
    </li>
  );
}

export function RoleplayChat() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { sessionId } = useParams();
  const { refresh } = useDashboard();
  const { data, setData, error } = useApi(`/roleplay/sessions/${sessionId}`);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(null); // "turn" | "hint" | "finish"
  const [slow, setSlow] = useState(false);
  const [sendError, setSendError] = useState("");
  const [hint, setHint] = useState(null);
  const [saved, setSaved] = useState({});
  const threadEnd = useRef(null);

  useEffect(() => {
    threadEnd.current?.scrollIntoView?.({ block: "nearest" });
  }, [data?.turns?.length, busy]);
  // A busy model can take a while: after 8s, say so instead of a frozen page.
  useEffect(() => {
    if (busy !== "turn") return undefined;
    setSlow(false);
    const id = setTimeout(() => setSlow(true), 8000);
    return () => clearTimeout(id);
  }, [busy]);

  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  if (!data) return <Layout><Loading /></Layout>;

  async function send(e) {
    e?.preventDefault();
    const message = text.trim();
    if (!message || busy) return;
    setBusy("turn");
    setSendError("");
    try {
      setData(await api.post(`/roleplay/sessions/${data.id}/turn`, { text: message }));
      setText("");
      setHint(null);
      refresh?.();
    } catch (err) {
      setSendError(err.message); // the message stays in the box to send again
    } finally {
      setBusy(null);
    }
  }

  async function askHint() {
    setBusy("hint");
    try {
      setHint(await api.post(`/roleplay/sessions/${data.id}/hint`));
    } catch (err) {
      setSendError(err.message);
    } finally {
      setBusy(null);
    }
  }

  async function finish() {
    setBusy("finish");
    setSendError("");
    try {
      setData(await api.post(`/roleplay/sessions/${data.id}/finish`));
      refresh?.();
    } catch (err) {
      setSendError(err.message);
    } finally {
      setBusy(null);
    }
  }

  async function again() {
    try {
      const s = await api.post("/roleplay/sessions", { scenario: data.scenario });
      navigate(`/roleplay/${s.id}`);
    } catch (err) {
      setSendError(err.message);
    }
  }

  async function save(word) {
    try {
      await api.post(`/vocab/${word.word_id}/track`);
    } catch (err) {
      // 409: already being reviewed or mastered -- it IS in their review.
      if (!/409|already/i.test(err.message)) return setSendError(err.message);
    }
    setSaved((s) => ({ ...s, [word.word_id]: true }));
  }

  const finished = data.status === "finished";
  const sm = data.summary;
  const words = [...(data.words || []), ...data.turns.flatMap((x) => x.words || [])]
    .filter((w, i, all) => all.findIndex((o) => o.zh === w.zh) === i);

  return (
    <Layout>
      <header className="page-head">
        <div>
          <div className="page-eyebrow"><Icon name="chat" size={13} /> {t("roleplay.title")}</div>
          <h1 className="h1">{data.title}</h1>
          <p className="sub"><span lang="zh-CN">{data.role}</span> · HSK {data.level}</p>
        </div>
        {!finished && (
          <div className="kpi-row">
            <div className="kpi">
              <span className="kpi-value">{data.turns_left}</span>
              <span className="kpi-label">{t("roleplay.turnsLeft")}</span>
            </div>
          </div>
        )}
      </header>

      <div className="ws">
        <div className="ws-main">
          {finished && sm && (
            <section className="card rp-summary" aria-labelledby="rp-sum">
              <h2 className="h2" id="rp-sum">{t("roleplay.summaryTitle")}</h2>
              <div className="dash-facts" style={{ marginTop: 12 }}>
                <div className="kpi"><span className="kpi-value">{sm.messages}</span><span className="kpi-label">{t("roleplay.statMessages")}</span></div>
                <div className="kpi"><span className="kpi-value">{sm.accepted}</span><span className="kpi-label">{t("roleplay.statAccepted")}</span></div>
                <div className="kpi"><span className="kpi-value">{sm.goals_met}/{sm.goals_total}</span><span className="kpi-label">{t("roleplay.statGoals")}</span></div>
                <div className="kpi"><span className="kpi-value">+{sm.xp}</span><span className="kpi-label">XP</span></div>
              </div>
              {sm.feedback && (
                <>
                  <p style={{ marginTop: 16 }}>{sm.feedback.summary}</p>
                  {sm.feedback.strengths?.length > 0 && (
                    <>
                      <p className="side-title">{t("roleplay.strengths")}</p>
                      <ul className="rp-goals">{sm.feedback.strengths.map((s, i) => <li key={i}>{s}</li>)}</ul>
                    </>
                  )}
                  {sm.feedback.next?.length > 0 && (
                    <>
                      <p className="side-title">{t("roleplay.nextTime")}</p>
                      <ul className="rp-goals">{sm.feedback.next.map((s, i) => <li key={i}>{s}</li>)}</ul>
                    </>
                  )}
                </>
              )}
              <p className="side-title">{t("roleplay.corrections")}</p>
              {sm.corrections.length === 0 ? (
                <p className="sub">{t("roleplay.noCorrections")}</p>
              ) : (
                <ul className="rp-corrections">
                  {sm.corrections.map((c, i) => (
                    <li key={i}>
                      <s lang="zh-CN">{c.text}</s> → <b lang="zh-CN">{c.corrected}</b>
                      <span className="sub">{c.explanation}</span>
                    </li>
                  ))}
                </ul>
              )}
              <div className="row" style={{ flexWrap: "wrap", marginTop: 16 }}>
                <button type="button" className="btn primary" onClick={again}>{t("roleplay.again")}</button>
                <Link to="/roleplay" className="btn ghost">{t("roleplay.all")}</Link>
              </div>
            </section>
          )}

          <div className="card rp-thread" aria-live="polite">
            {data.turns.map((turn, i) =>
              turn.role === "partner"
                ? <PartnerLine key={i} turn={turn} role={data.role} />
                : <LearnerLine key={i} turn={turn} />
            )}
            {busy === "turn" && (
              <p className="sub rp-thinking" role="status">
                <span className="spinner" aria-hidden="true" /> {t("roleplay.thinking")}
                {slow && <span className="rp-slow">{t("roleplay.slow")}</span>}
              </p>
            )}
            <div ref={threadEnd} />
          </div>

          {!finished && (
            <form className="card rp-compose" onSubmit={send}>
              <label className="side-title" htmlFor="rp-input">{t("roleplay.inputLabel")}</label>
              <div className="rp-compose-row">
                <input
                  id="rp-input"
                  className="input"
                  lang="zh-CN"
                  value={text}
                  maxLength={200}
                  onChange={(e) => setText(e.target.value)}
                  placeholder={t("roleplay.placeholder")}
                  autoComplete="off"
                  disabled={busy === "turn" || data.turns_left === 0}
                />
                <MicRecorder onTranscript={(heard) => setText((cur) => (cur ? `${cur} ${heard}` : heard))}
                             disabled={busy !== null} />
                <button type="submit" className="btn primary" disabled={!text.trim() || busy !== null || data.turns_left === 0}>
                  {t("roleplay.send")}
                </button>
              </div>
              {sendError && <p className="formerr" role="alert">{sendError}</p>}
              <div className="row" style={{ flexWrap: "wrap", marginTop: 12, gap: 8 }}>
                <button type="button" className="btn small" onClick={askHint} disabled={busy !== null}>
                  <Icon name="sparkles" size={13} /> {t("roleplay.hint")}
                </button>
                <button type="button" className="btn small ghost" onClick={finish} disabled={busy !== null || data.learner_turns === 0}>
                  {busy === "finish" ? t("roleplay.finishing") : t("roleplay.finish")}
                </button>
              </div>
              {hint && (
                <div className="practice-why" style={{ marginTop: 12 }}>
                  {hint.goal && <p className="sub">{t("roleplay.hintGoal", { goal: hint.goal })}</p>}
                  {hint.line && (
                    <p>
                      {t("roleplay.hintLine")} <b lang="zh-CN">{hint.line.zh}</b>{" "}
                      <span className="sub">{hint.line.pinyin}</span>
                      {hint.line.translation && <span className="sub"> — {hint.line.translation}</span>}
                    </p>
                  )}
                </div>
              )}
              <p className="sub rp-note">{t("roleplay.aiNote")}</p>
            </form>
          )}
        </div>

        <aside className="ws-side">
          <div className="card side-card">
            <p className="side-title">{t("roleplay.goals")}</p>
            <ul className="rp-checklist">
              {data.goals.map((g, i) => (
                <li key={i} className={g.met ? "is-met" : ""}>
                  <Icon name={g.met ? "check" : "target"} size={14} /> <span>{g.text}</span>
                </li>
              ))}
            </ul>
          </div>
          {words.length > 0 && (
            <div className="card side-card">
              <p className="side-title">{t("roleplay.keyWords")}</p>
              <ul className="rp-words">
                {words.map((w) => (
                  <WordChip key={w.zh} word={w} saved={!!saved[w.word_id]} onSave={save} />
                ))}
              </ul>
            </div>
          )}
        </aside>
      </div>
    </Layout>
  );
}
