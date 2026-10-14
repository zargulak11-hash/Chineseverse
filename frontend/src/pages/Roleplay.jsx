import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api.js";
import Art, { placeArt } from "../components/Art.jsx";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import MicRecorder from "../components/MicRecorder.jsx";
import UserAvatar from "../components/UserAvatar.jsx";
import { Empty, Loading } from "../components/ui.jsx";
import { useAuth } from "../auth.js";
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

  const bySlug = Object.fromEntries(data.scenarios.map((s) => [s.slug, s]));
  const unlocked = data.scenarios.filter((s) => s.unlocked).length;
  const finished = data.scenarios.reduce((n, s) => n + s.played, 0);
  return (
    <Layout>
      <header className="page-head">
        <div>
          <div className="page-eyebrow"><Icon name="chat" size={13} /> {t("nav.groupUse")}</div>
          <h1 className="h1">{t("roleplay.title")}</h1>
          <p className="sub">{t("roleplay.subtitle")}</p>
        </div>
        <div className="kpi-row">
          <div className="kpi"><span className="kpi-value">{unlocked}/{data.scenarios.length}</span><span className="kpi-label">{t("roleplay.statOpen")}</span></div>
          <div className="kpi"><span className="kpi-value">{finished}</span><span className="kpi-label">{t("roleplay.statPlayed")}</span></div>
        </div>
      </header>

      {startError && <p className="formerr" role="alert">{startError}</p>}

      <div className="ws">
        <div className="ws-main">
          {!data.ai_available && (
            <div className="card rp-unavailable">
              <h2 className="h2">{t("roleplay.unavailableTitle")}</h2>
              <p className="sub">{t("roleplay.unavailableText")}</p>
              <Link to="/real-chinese" className="btn" style={{ marginTop: 12 }}>{t("roleplay.toScenes")}</Link>
            </div>
          )}
          <h2 className="h2 section-title">{t("roleplay.pickScene")}</h2>
          <div className="rp-doors">
            {data.scenarios.map((s) => (
              <article key={s.slug} className={`card rp-door${s.unlocked ? "" : " is-locked"}`}>
                <div className="rp-door-art">
                  <Art name={placeArt(s.icon)} size={84} />
                  <span className="badge">HSK {s.level}</span>
                </div>
                <div className="rp-door-body">
                  <h3 className="h2 rp-door-title">{s.title}</h3>
                  {s.role && (
                    <p className="rp-door-who">
                      <Icon name="chat" size={13} /> {t("roleplay.youMeet")} <b lang="zh-CN">{s.role}</b>
                    </p>
                  )}
                  <ul className="rp-door-goals" aria-label={t("roleplay.goals")}>
                    {s.goals.map((g, i) => <li key={i}><Icon name="target" size={13} /> <span>{g}</span></li>)}
                  </ul>
                  <div className="rp-door-foot">
                    {s.played > 0 && <span className="sub rp-played">{t("roleplay.played", { count: s.played })}</span>}
                    {s.unlocked ? (
                      <button type="button" className="btn primary small" disabled={!data.ai_available || starting !== null}
                              onClick={() => start(s.slug)}>
                        {starting === s.slug ? t("roleplay.starting") : t("roleplay.start")}
                      </button>
                    ) : (
                      <span className="sub"><Icon name="lock" size={13} /> {t("roleplay.locked", { level: s.level })}</span>
                    )}
                  </div>
                </div>
              </article>
            ))}
          </div>
        </div>

        <aside className="ws-side">
          <section className="card side-card" aria-labelledby="rp-recent">
            <p className="side-title" id="rp-recent">{t("roleplay.recent")}</p>
            {recent?.length > 0 ? (
              <ul className="rp-inbox">
                {recent.map((r) => (
                  <li key={r.id}>
                    <Link to={`/roleplay/${r.id}`} className="rp-inbox-row">
                      <Art name={placeArt(bySlug[r.scenario]?.icon || "street")} size={40} shape="round" flat />
                      <span className="rp-inbox-text">
                        <b>{bySlug[r.scenario]?.title || r.scenario}</b>
                        <span className="sub">{t("roleplay.messages", { count: r.messages })}</span>
                      </span>
                      <span className={`badge${r.status === "finished" ? "" : " accent"}`}>
                        {r.status === "finished" ? t("roleplay.seeSummary") : t("roleplay.continue")}
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            ) : recent ? (
              <p className="sub">{t("roleplay.noRecent")}</p>
            ) : null}
          </section>
        </aside>
      </div>
    </Layout>
  );
}

// The partner's face in the thread: the painting of the place they work in
// (the same art the map and the scene list use) -- a character, not a stock
// photo, and never the learner's companion.
function PartnerAvatar({ icon, size = 40 }) {
  return (
    <span className="rp-avatar" aria-hidden="true">
      <Art name={placeArt(icon)} size={size} shape="round" flat />
    </span>
  );
}

// One "listen" button with a visible playing state, for any Chinese line.
function SpeakButton({ text, label }) {
  const [playing, setPlaying] = useState(false);
  return (
    <button
      type="button"
      className={`icon-btn rp-speak${playing ? " is-playing" : ""}`}
      aria-label={label}
      title={label}
      onClick={() => speakChinese(text, { onStart: () => setPlaying(true), onEnd: () => setPlaying(false) })}
    >
      <Icon name="volume" size={16} />
    </button>
  );
}

function PartnerLine({ turn, role, icon }) {
  const { t } = useTranslation();
  const [pinyin, setPinyin] = useState(false);
  const [translation, setTranslation] = useState(false);
  return (
    <div className="rp-msg is-partner">
      <PartnerAvatar icon={icon} />
      <div className="rp-line is-partner">
        <span className="rp-who" lang="zh-CN">{role}</span>
        <div className="rp-line-main">
          <p className="rp-zh" lang="zh-CN">{turn.zh}</p>
          <SpeakButton text={turn.zh} label={t("roleplay.listen")} />
        </div>
        {pinyin && turn.pinyin && <p className="rp-pinyin">{turn.pinyin}</p>}
        {translation && turn.translation && <p className="rp-gloss">{turn.translation}</p>}
        {(turn.pinyin || turn.translation) && (
          <div className="rp-tools">
            {turn.pinyin && (
              <button type="button" className={`rp-chip${pinyin ? " is-on" : ""}`} aria-pressed={pinyin}
                      onClick={() => setPinyin((v) => !v)}>
                {t("roleplay.showPinyin")}
              </button>
            )}
            {turn.translation && (
              <button type="button" className={`rp-chip${translation ? " is-on" : ""}`} aria-pressed={translation}
                      onClick={() => setTranslation((v) => !v)}>
                {t("roleplay.showTranslation")}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function LearnerLine({ turn, me }) {
  const { t } = useTranslation();
  const fb = turn.feedback;
  return (
    <div className="rp-msg is-learner">
      <div className="rp-line-stack">
        <div className="rp-line is-learner">
          <p className="rp-zh" lang="zh-CN">{turn.text}</p>
        </div>
        {fb ? (
          <div className="rp-fix">
            <p className="rp-fix-head">
              <Icon name="pen" size={13} /> <b>{t("roleplay.corrected")}</b>
            </p>
            <div className="rp-line-main">
              <p className="rp-fix-zh" lang="zh-CN">{fb.corrected}</p>
              {fb.corrected && <SpeakButton text={fb.corrected} label={t("roleplay.listen")} />}
            </div>
            <p className="rp-fix-why">{fb.explanation}</p>
          </div>
        ) : (
          <span className="rp-ok"><Icon name="check" size={13} /> {t("roleplay.wellSaid")}</span>
        )}
      </div>
      <UserAvatar url={me.avatar} name={me.name} size={36} className="rp-me" />
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
      <button type="button" className="rp-word-say" onClick={() => speakChinese(word.zh)}
              aria-label={`${t("roleplay.listen")}: ${word.zh}`}>
        <b lang="zh-CN">{word.zh}</b>
        <span className="sub">{word.pinyin}</span>
      </button>
      <span className="rp-word-rest">
        {word.meaning && <span className="rp-word-meaning">{word.meaning}</span>}
        {word.word_id && (
          <button type="button" className={`btn small${saved ? " ghost" : ""}`} disabled={saved} onClick={() => onSave(word)}>
            {saved ? <><Icon name="check" size={13} /> {t("roleplay.saved")}</> : <><Icon name="bookmark" size={13} /> {t("roleplay.save")}</>}
          </button>
        )}
      </span>
    </li>
  );
}

export function RoleplayChat() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { sessionId } = useParams();
  const { user } = useAuth();
  const { dashboard, refresh } = useDashboard();
  const { data, setData, error } = useApi(`/roleplay/sessions/${sessionId}`);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(null); // "turn" | "hint" | "finish"
  const [slow, setSlow] = useState(false);
  const [sendError, setSendError] = useState("");
  const [hint, setHint] = useState(null);
  const [saved, setSaved] = useState({});
  const threadEnd = useRef(null);
  const inputRef = useRef(null);

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

  // The suggested line goes into the box, not straight to the partner: the
  // learner still sends it (and can change it) themselves.
  function takeSuggestion(zh) {
    setText(zh);
    inputRef.current?.focus();
  }

  const finished = data.status === "finished";
  const sm = data.summary;
  const words = [...(data.words || []), ...data.turns.flatMap((x) => x.words || [])]
    .filter((w, i, all) => all.findIndex((o) => o.zh === w.zh) === i);
  const goalsMet = data.goals.filter((g) => g.met).length;
  const me = { avatar: dashboard?.avatar_url, name: user?.username };
  const totalTurns = data.learner_turns + data.turns_left;

  return (
    <Layout>
      <header className="card rp-room-head">
        <Link to="/roleplay" className="icon-btn" aria-label={t("roleplay.all")} title={t("roleplay.all")}>
          <Icon name="arrowLeft" size={18} />
        </Link>
        <PartnerAvatar icon={data.icon} size={56} />
        <div className="rp-room-id">
          <div className="page-eyebrow"><Icon name="chat" size={13} /> {t("roleplay.title")}</div>
          <h1 className="h1 rp-room-title">{data.title}</h1>
          <p className="sub"><b lang="zh-CN">{data.role}</b> · HSK {data.level}</p>
        </div>
        <div className="rp-room-meta">
          {data.goals.length > 0 && (
            <span className={`badge${goalsMet === data.goals.length ? " good" : ""}`}>
              <Icon name="target" size={13} /> {t("roleplay.goalsMet", { met: goalsMet, total: data.goals.length })}
            </span>
          )}
          {!finished && (
            <div className="rp-turns" aria-label={`${t("roleplay.turnsLeft")}: ${data.turns_left}`}>
              <span className="rp-turns-label">{t("roleplay.turnsLeft")} <b>{data.turns_left}</b></span>
              <span className="rp-turns-bar" aria-hidden="true">
                <span style={{ width: `${totalTurns ? (data.turns_left / totalTurns) * 100 : 0}%` }} />
              </span>
            </div>
          )}
        </div>
      </header>

      <div className="ws rp-ws">
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

          <section className="card rp-chat" aria-label={data.title}>
            <div className="rp-thread" aria-live="polite">
              {data.turns.map((turn, i) =>
                turn.role === "partner"
                  ? <PartnerLine key={i} turn={turn} role={data.role} icon={data.icon} />
                  : <LearnerLine key={i} turn={turn} me={me} />
              )}
              {busy === "turn" && (
                <div className="rp-msg is-partner" role="status">
                  <PartnerAvatar icon={data.icon} />
                  <div className="rp-line is-partner rp-typing">
                    <span className="rp-dots" aria-hidden="true"><i /><i /><i /></span>
                    <span className="sub">{t("roleplay.thinking")}</span>
                    {slow && <span className="rp-slow">{t("roleplay.slow")}</span>}
                  </div>
                </div>
              )}
              <div ref={threadEnd} />
            </div>

            {!finished && (
              <form className="rp-compose" onSubmit={send}>
                {hint && (
                  <div className="rp-suggest" aria-live="polite">
                    {hint.goal && <p className="rp-suggest-goal"><Icon name="target" size={13} /> {t("roleplay.hintGoal", { goal: hint.goal })}</p>}
                    {hint.line && (
                      <div className="rp-suggest-row">
                        <button type="button" className="rp-suggest-chip" onClick={() => takeSuggestion(hint.line.zh)}
                                title={t("roleplay.useSuggestion")}>
                          <span className="rp-suggest-label">{t("roleplay.hintLine")}</span>
                          <b lang="zh-CN">{hint.line.zh}</b>
                          <span className="sub">{hint.line.pinyin}</span>
                          {hint.line.translation && <span className="sub">{hint.line.translation}</span>}
                        </button>
                        <SpeakButton text={hint.line.zh} label={t("roleplay.listen")} />
                      </div>
                    )}
                  </div>
                )}
                <label className="side-title" htmlFor="rp-input">{t("roleplay.inputLabel")}</label>
                <div className="rp-compose-row">
                  <button type="button" className="btn small ghost rp-hint-btn" onClick={askHint} disabled={busy !== null}>
                    <Icon name="sparkles" size={13} /> {busy === "hint" ? t("roleplay.hinting") : t("roleplay.hint")}
                  </button>
                  <input
                    id="rp-input"
                    ref={inputRef}
                    className="input"
                    lang="zh-CN"
                    value={text}
                    maxLength={200}
                    onChange={(e) => setText(e.target.value)}
                    placeholder={t("roleplay.placeholder")}
                    autoComplete="off"
                    disabled={busy === "turn" || data.turns_left === 0}
                  />
                  <span className="rp-mic">
                    <MicRecorder onTranscript={(heard) => setText((cur) => (cur ? `${cur} ${heard}` : heard))}
                                 disabled={busy !== null} showStatus />
                  </span>
                  <button type="submit" className="btn primary rp-send" disabled={!text.trim() || busy !== null || data.turns_left === 0}>
                    <Icon name="send" size={16} /> {t("roleplay.send")}
                  </button>
                </div>
                {sendError && <p className="formerr" role="alert">{sendError}</p>}
                <div className="rp-compose-foot">
                  <p className="sub rp-note">{t("roleplay.aiNote")}</p>
                  <button type="button" className="btn small ghost" onClick={finish} disabled={busy !== null || data.learner_turns === 0}>
                    <Icon name="flag" size={13} /> {busy === "finish" ? t("roleplay.finishing") : t("roleplay.finish")}
                  </button>
                </div>
              </form>
            )}
          </section>
        </div>

        <aside className="ws-side">
          <div className="card side-card">
            <p className="side-title">{t("roleplay.goals")}</p>
            <ul className="rp-checklist">
              {data.goals.map((g, i) => (
                <li key={i} className={g.met ? "is-met" : ""}>
                  <span className="rp-check" aria-hidden="true"><Icon name={g.met ? "check" : "target"} size={14} /></span>
                  <span>{g.text}</span>
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
