import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";
import { api } from "../api.js";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import UserAvatar from "../components/UserAvatar.jsx";
import { Bar, Celebration, Empty, Loading } from "../components/ui.jsx";
import { useDashboard } from "../context/DashboardContext.jsx";
import { speakChinese } from "../zhSpeech.js";
import { duelErrorText } from "./Duels.jsx";
import { formatDate } from "../dates.js";

// One duel. The server is the only authority: it says whose turn it is,
// which question is next, how much time each player has left, and who won.
// The page keeps exactly one clock (a 250 ms tick that only re-renders the
// countdown, derived from the server's remaining_ms) and one poll, and a poll
// that started before an answer/start/accept can never overwrite the newer
// state that action returned.

const POLL_MS = { pending: 4000, active: 3000 };
const FEEDBACK_MS = 650;
// A beat after our own countdown hits zero, ask the server: it finishes the
// attempt (with the same small grace it allows answers in flight).
const TIMEOUT_CHECK_MS = 1800;
const RECOVERABLE = ["already_answered", "out_of_order", "time_up", "already_finished", "not_started"];

function fmtClock(ms) {
  const s = Math.max(0, Math.ceil(ms / 1000));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

function fmtWhen(iso, lang) {
  if (!iso) return "";
  return formatDate(iso, lang, { dateStyle: "medium", timeStyle: "short" }); // naive UTC: dates.js reads it as UTC
}

function PlayerCard({ p, isMe, total, highlight }) {
  const { t } = useTranslation();
  if (!p) return null;
  const name = isMe ? t("pages.duels.you") : p.username || "—";
  return (
    <div className={`card duel-player${highlight ? " is-winner" : ""}`}>
      <div className="row" style={{ gap: 10 }}>
        <UserAvatar url={p.avatar_url} name={p.username} size={44} />
        <div className="col" style={{ gap: 2, minWidth: 0 }}>
          <b className="duel-row-name">{name}</b>
          {p.finish_reason && <span className="sub" style={{ fontSize: 12 }}>{t(`pages.duelBattle.finish.${p.finish_reason}`)}</span>}
        </div>
        {highlight && <Icon name="trophy" size={18} style={{ marginLeft: "auto", color: "var(--accent)" }} />}
      </div>
      <div className="duel-stats">
        <div><b>{p.correct != null ? `${p.correct}/${total}` : "—"}</b><span className="sub">{t("pages.duelBattle.correctLabel")}</span></div>
        <div><b>{p.score ?? "—"}</b><span className="sub">{t("pages.duelBattle.score")}</span></div>
        <div><b>{p.time_used_ms != null ? fmtClock(p.time_used_ms) : "—"}</b><span className="sub">{t("pages.duelBattle.timeLabel")}</span></div>
      </div>
    </div>
  );
}

export default function DuelBattle() {
  const { t, i18n } = useTranslation();
  const { duelId } = useParams();
  const { refresh: refreshDashboard } = useDashboard() || {};
  const [duel, setDuelState] = useState(null);
  const [loadError, setLoadError] = useState("");
  const [netProblem, setNetProblem] = useState(false);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState("");
  const [feedback, setFeedback] = useState(null); // {index, choice_id, correct}
  const [confirmForfeit, setConfirmForfeit] = useState(false);
  const [celebrating, setCelebrating] = useState(false);
  const [, setTick] = useState(0);

  const seq = useRef(0); // bumped by every state-changing action
  const receivedAt = useRef(0); // performance.now() when `duel` arrived
  const feedbackTimer = useRef(null);
  const pollBusy = useRef(false);
  const busyRef = useRef(false); // an action (and its feedback beat) is in flight
  const timeoutAsked = useRef(false);
  const celebrated = useRef(false);
  const sawLive = useRef(false);

  const setDuel = useCallback((d) => {
    receivedAt.current = performance.now();
    timeoutAsked.current = false;
    setDuelState(d);
  }, []);

  // Read-only refresh. Dropped if an action changed the duel meanwhile.
  const fetchDuel = useCallback(
    (quiet = false) => {
      const mySeq = seq.current;
      return api
        .get(`/duels/${duelId}`)
        .then((d) => {
          setNetProblem(false);
          if (seq.current === mySeq) setDuel(d);
        })
        .catch((e) => {
          if (quiet && !e.status) setNetProblem(true);
          else if (!quiet) setLoadError(duelErrorText(t, e));
        });
    },
    [duelId, setDuel, t]
  );

  // Initial load, and again on language change (question labels are localized).
  useEffect(() => {
    setDuelState(null);
    setLoadError("");
    fetchDuel(false);
  }, [fetchDuel, i18n.language]);

  useEffect(() => () => clearTimeout(feedbackTimer.current), []);

  const status = duel?.status;
  const me = duel?.me;
  const playing = status === "active" && me?.started && !me?.finished;

  // The one poll: pending (waiting for an answer) and active (opponent
  // progress, and the result once both are done). Stops when terminal.
  useEffect(() => {
    const every = POLL_MS[status];
    if (!every) return undefined;
    const tick = () => {
      if (document.hidden || pollBusy.current || busyRef.current) return;
      pollBusy.current = true;
      fetchDuel(true).finally(() => {
        pollBusy.current = false;
      });
    };
    const id = setInterval(tick, every);
    document.addEventListener("visibilitychange", tick);
    return () => {
      clearInterval(id);
      document.removeEventListener("visibilitychange", tick);
    };
  }, [status, fetchDuel]);

  // The one clock. Only re-renders the countdown; the server decides time-up.
  useEffect(() => {
    if (!playing) return undefined;
    const id = setInterval(() => setTick((n) => n + 1), 250);
    return () => clearInterval(id);
  }, [playing]);

  const remaining = playing ? Math.max(0, (me.remaining_ms ?? 0) - (performance.now() - receivedAt.current)) : null;

  useEffect(() => {
    if (!playing || remaining > 0 || timeoutAsked.current) return undefined;
    timeoutAsked.current = true;
    const id = setTimeout(() => fetchDuel(true), TIMEOUT_CHECK_MS);
    return () => clearTimeout(id);
  }, [playing, remaining, fetchDuel]);

  // Result side effects, once.
  useEffect(() => {
    if (status === "active") sawLive.current = true;
    if (status !== "completed") return;
    if (sawLive.current && refreshDashboard) refreshDashboard(); // XP / quests changed
    if (duel?.result?.outcome === "win" && !celebrated.current && sawLive.current) {
      celebrated.current = true;
      setCelebrating(true);
    }
  }, [status, duel?.result?.outcome, refreshDashboard]);

  const q = duel?.current;
  useEffect(() => {
    if (q?.type === "listen_to_word" && q.prompt?.speak) speakChinese(q.prompt.speak);
  }, [q?.index, q?.type, q?.prompt?.speak]);

  async function act(path) {
    if (busyRef.current) return;
    busyRef.current = true;
    seq.current += 1;
    setBusy(true);
    setActionError("");
    try {
      setDuel(await api.post(`/duels/${duelId}/${path}`));
    } catch (e) {
      setActionError(duelErrorText(t, e));
      fetchDuel(true);
    } finally {
      busyRef.current = false;
      setBusy(false);
    }
  }

  async function choose(option) {
    // busyRef (not state) so a double click in the same frame can't send twice.
    if (busyRef.current || feedback || !q) return;
    busyRef.current = true;
    seq.current += 1;
    setBusy(true);
    setActionError("");
    try {
      const r = await api.post(`/duels/${duelId}/answer`, { index: q.index, choice_id: option.id });
      setFeedback({ index: q.index, choice_id: option.id, correct: r.answer.correct });
      feedbackTimer.current = setTimeout(() => {
        setFeedback(null);
        setDuel(r.duel);
        busyRef.current = false;
        setBusy(false);
      }, FEEDBACK_MS);
    } catch (e) {
      busyRef.current = false;
      setBusy(false);
      // Another tab answered, or the clock ran out: show the server's state.
      if (!RECOVERABLE.includes(e.code) && !String(e.code || "").startsWith("not_active")) {
        setActionError(duelErrorText(t, e));
      }
      fetchDuel(true);
    }
  }

  if (loadError) {
    return (
      <Layout>
        <Empty>{loadError}</Empty>
        <div className="center" style={{ marginTop: 12 }}>
          <Link to="/duels" className="btn">{t("pages.duelBattle.back")}</Link>
        </div>
      </Layout>
    );
  }
  if (!duel) return <Layout><Loading /></Layout>;

  const opp = duel.opponent || {};
  const oppName = opp.username || "—";
  const total = duel.question_count;
  const minutes = new Intl.NumberFormat(i18n.language).format(duel.time_limit_seconds / 60);
  const back = (
    <Link to="/duels" className="sub duel-back">
      ← {t("pages.duelBattle.back")}
    </Link>
  );
  const banner = (
    <div className="duel-vs">
      <div className="duel-vs-side">
        <UserAvatar url={me?.avatar_url} name={me?.username} size={48} />
        <b>{t("pages.duels.you")}</b>
      </div>
      <span className="vs">{t("pages.duels.vs")}</span>
      <div className="duel-vs-side">
        <UserAvatar url={opp.avatar_url} name={oppName} size={48} />
        <b className="duel-row-name">{oppName}</b>
      </div>
    </div>
  );
  const rules = (
    <ul className="duel-rules">
      <li>{t("pages.duelBattle.ruleSame", { count: total })}</li>
      <li>{t("pages.duelBattle.ruleClock", { minutes })}</li>
      <li>{t("pages.duelBattle.ruleWinner")}</li>
    </ul>
  );
  const errLine = actionError && <p className="formerr">{actionError}</p>;
  const netLine = netProblem && <p className="sub" style={{ color: "var(--bad)" }}>{t("pages.duelBattle.reconnecting")}</p>;

  // ------------------------------------------------------------ pending
  if (status === "pending") {
    const incoming = duel.can_accept;
    return (
      <Layout>
        {back}
        <div className="card duel-panel">
          {banner}
          <h1 className="h1 center">
            {incoming ? t("pages.duelBattle.pendingIncoming", { name: oppName }) : t("pages.duelBattle.pendingOutgoing", { name: oppName })}
          </h1>
          <p className="sub center">
            {t("pages.duels.meta", { level: duel.hsk_level, focus: t(`pages.duels.focusType.${duel.focus || "mix"}`) })}
          </p>
          {!incoming && <p className="sub center">{t("pages.duelBattle.pendingOutgoingSub")}</p>}
          <p className="sub center" style={{ fontSize: 12 }}>{t("pages.duelBattle.expiresAt", { time: fmtWhen(duel.expires_at, i18n.language) })}</p>
          <h3 className="duel-rules-title">{t("pages.duelBattle.rulesTitle")}</h3>
          {rules}
          {errLine}
          {netLine}
          <div className="row duel-actions">
            {incoming && (
              <>
                <button type="button" className="btn primary" disabled={busy} onClick={() => act("accept")}>
                  {t("pages.duels.accept")}
                </button>
                <button type="button" className="btn ghost" disabled={busy} onClick={() => act("decline")}>
                  {t("pages.duels.decline")}
                </button>
              </>
            )}
            {duel.can_cancel && (
              <button type="button" className="btn ghost" disabled={busy} onClick={() => act("cancel")}>
                {t("pages.duels.cancelChallenge")}
              </button>
            )}
          </div>
        </div>
      </Layout>
    );
  }

  // ------------------------------------------------------------ declined / cancelled / expired
  if (["declined", "cancelled", "expired"].includes(status)) {
    return (
      <Layout>
        {back}
        <div className="card duel-panel center">
          {banner}
          <h1 className="h1">{t(`pages.duelBattle.${status}`, { name: oppName })}</h1>
          <p className="sub">{duel.legacy ? t("pages.duelBattle.legacyNote") : t("pages.duelBattle.noGame")}</p>
          <span className="badge">{t(`pages.duels.status.${status}`)}</span>
        </div>
      </Layout>
    );
  }

  // ------------------------------------------------------------ completed
  if (status === "completed") {
    const res = duel.result || {};
    const title =
      res.outcome === "win" ? t("pages.duelBattle.victory") : res.outcome === "loss" ? t("pages.duelBattle.lost", { name: oppName }) : t("pages.duelBattle.draw");
    return (
      <Layout>
        <Celebration
          show={celebrating}
          icon="🏆"
          title={t("pages.duelBattle.victory")}
          subtitle={t("pages.duelBattle.yourResult", { correct: me?.correct ?? 0, total, score: me?.score ?? 0 })}
          countTo={me?.score ?? 0}
          countLabel={t("pages.duelBattle.score")}
          onClose={() => setCelebrating(false)}
          actionLabel={t("practice.nice")}
        />
        {back}
        <div className={`card duel-panel center reveal${res.outcome === "win" ? " burst" : ""}`}>
          <div className="reveal-icon" style={{ fontSize: 48 }}>{res.outcome === "win" ? "🏆" : res.outcome === "draw" ? "🤝" : "💪"}</div>
          <h1 className="h1">{title}</h1>
          {res.decided_by && <p className="sub">{t(`pages.duelBattle.decidedBy.${res.decided_by}`)}</p>}
          <span className="badge good">{t("pages.duels.status.completed")}</span>
        </div>
        <div className="grid grid-2 duel-result-grid">
          <PlayerCard p={me} isMe total={total} highlight={res.winner_id != null && res.winner_id === me?.id} />
          <PlayerCard p={opp} total={total} highlight={res.winner_id != null && res.winner_id === opp.id} />
        </div>
        {duel.legacy && <p className="sub center" style={{ marginTop: 12 }}>{t("pages.duelBattle.legacyNote")}</p>}
        {duel.review && (
          <div className="card" style={{ marginTop: 16 }}>
            <h2 className="h2" style={{ fontSize: 17 }}>{t("pages.duelBattle.review")}</h2>
            <ol className="duel-review">
              {duel.review.map((item) => {
                const a = item.answer || {};
                const picked = item.options.find((o) => o.id === a.choice_id);
                const right = item.options.find((o) => o.id === a.correct_id);
                const prompt = item.prompt?.text || item.prompt?.speak || "";
                return (
                  <li key={item.index} className={a.correct ? "is-correct" : "is-wrong"}>
                    <div className="row spread" style={{ gap: 8 }}>
                      <span className="sub" style={{ fontSize: 12 }}>{t(`practice.q.${item.type}`)}</span>
                      <Icon name={a.correct ? "check" : "x"} size={14} style={{ color: a.correct ? "var(--good)" : "var(--bad)" }} />
                    </div>
                    <b className="duel-review-prompt">{prompt}</b>
                    <div className="sub">
                      {t("pages.duelBattle.yourAnswer")}: {picked ? picked.label : t("pages.duelBattle.notAnswered")}
                    </div>
                    {!a.correct && right && (
                      <div className="sub" style={{ color: "var(--good)" }}>
                        {t("pages.duelBattle.correctAnswer")}: {right.label}
                      </div>
                    )}
                  </li>
                );
              })}
            </ol>
          </div>
        )}
      </Layout>
    );
  }

  // ------------------------------------------------------------ active
  const oppLine = opp.finished
    ? t("pages.duelBattle.opponentFinished", { name: oppName })
    : opp.started
    ? t("pages.duelBattle.opponentProgress", { name: oppName, answered: opp.answered, total })
    : t("pages.duelBattle.opponentNotStarted", { name: oppName });

  if (!me?.started) {
    return (
      <Layout>
        {back}
        <div className="card duel-panel">
          {banner}
          <h1 className="h1 center">{t("pages.duelBattle.readyTitle")}</h1>
          <p className="sub center">
            {t("pages.duels.meta", { level: duel.hsk_level, focus: t(`pages.duels.focusType.${duel.focus || "mix"}`) })}
          </p>
          <h3 className="duel-rules-title">{t("pages.duelBattle.rulesTitle")}</h3>
          {rules}
          <p className="sub center">{oppLine}</p>
          {duel.play_deadline && (
            <p className="sub center" style={{ fontSize: 12 }}>{t("pages.duelBattle.startBy", { time: fmtWhen(duel.play_deadline, i18n.language) })}</p>
          )}
          {errLine}
          {netLine}
          <div className="row duel-actions">
            <button type="button" className="btn primary" disabled={busy} onClick={() => act("start")}>
              <Icon name="play" size={14} /> {busy ? t("pages.duelBattle.starting") : t("pages.duelBattle.start")}
            </button>
          </div>
        </div>
      </Layout>
    );
  }

  if (me.finished) {
    return (
      <Layout>
        {back}
        <div className="card duel-panel center">
          {banner}
          <div className="reveal-icon" aria-hidden="true"><Icon name="clock" size={44} /></div>
          <h1 className="h1">{t("pages.duelBattle.waitingTitle", { name: oppName })}</h1>
          <p className="sub">{t("pages.duelBattle.yourResult", { correct: me.correct ?? 0, total, score: me.score ?? 0 })}</p>
          <p className="sub">{t(`pages.duelBattle.finish.${me.finish_reason || "completed"}`)}</p>
          <p className="sub">{oppLine}</p>
          <p className="sub" style={{ fontSize: 12 }}>{t("pages.duelBattle.waitingSub", { name: oppName })}</p>
          {netLine}
        </div>
      </Layout>
    );
  }

  const low = remaining != null && remaining < 20000;
  const pct = (remaining / (duel.time_limit_seconds * 1000)) * 100;
  return (
    <Layout>
      {back}
      <div className="card duel-hud">
        <div className="duel-hud-row">
          <div className={`duel-clock${low ? " low" : ""}`} role="timer" aria-label={t("pages.duelBattle.timeLeft")}>
            <Icon name="clock" size={16} /> {fmtClock(remaining)}
          </div>
          <div className="duel-hud-stat">
            <b>{me.score ?? 0}</b>
            <span className="sub">{t("pages.duelBattle.score")}</span>
          </div>
          <div className="duel-hud-opp sub">
            <UserAvatar url={opp.avatar_url} name={oppName} size={22} />
            <span className="duel-row-name">{oppLine}</span>
          </div>
        </div>
        <div className={`timerbar duel-timerbar${low ? " low" : ""}`} style={{ marginTop: 10 }}>
          <div style={{ width: `${Math.max(0, Math.min(100, pct))}%` }} />
        </div>
      </div>

      {q ? (
        <div className="card practice-card" style={{ marginTop: 14 }} key={`${duel.id}-${q.index}`}>
          <div className="row spread">
            <span className="sub">{t("pages.duelBattle.question", { n: q.index + 1, total })}</span>
            <span className="sub" style={{ fontSize: 12 }}>{t(`practice.q.${q.type}`)}</span>
          </div>
          <div style={{ marginTop: 8 }}>
            <Bar value={(me.answered / total) * 100} />
          </div>
          <div className="practice-prompt" style={{ marginTop: 12 }}>
            {q.type === "listen_to_word" ? (
              <button type="button" className="btn" onClick={() => speakChinese(q.prompt.speak)}>
                <Icon name="ear" size={16} style={{ verticalAlign: -3, marginRight: 6 }} />
                {t("practice.playAgain")}
              </button>
            ) : (
              <>
                <div className={["word_to_meaning", "char_to_meaning", "char_to_pinyin"].includes(q.type) ? "practice-hanzi" : "practice-text"}>
                  {q.prompt.text}
                </div>
                {q.prompt.pinyin && <div className="sub" style={{ color: "var(--accent2)" }}>{q.prompt.pinyin}</div>}
                {q.prompt.speak && (
                  <button type="button" className="btn small ghost" onClick={() => speakChinese(q.prompt.speak)} aria-label={t("pages.hanzi.hear")}>
                    <Icon name="ear" size={14} style={{ verticalAlign: -2 }} />
                  </button>
                )}
              </>
            )}
          </div>
          <div className="practice-options">
            {q.options.map((o) => {
              let cls = "btn practice-option";
              if (feedback && feedback.index === q.index && feedback.choice_id === o.id) {
                cls += feedback.correct ? " is-correct" : " is-wrong";
              }
              const cjk = ["meaning_to_word", "listen_to_word"].includes(q.type);
              return (
                <button key={o.id} type="button" className={cls} disabled={busy || !!feedback} onClick={() => choose(o)}>
                  <span className={cjk ? "practice-option-hanzi" : ""}>{o.label}</span>
                </button>
              );
            })}
          </div>
          <div className="duel-feedback" aria-live="polite">
            {feedback && (
              <span className={`badge ${feedback.correct ? "good" : "bad"}`}>
                {feedback.correct ? t("pages.duelBattle.correct") : t("pages.duelBattle.wrong")}
              </span>
            )}
          </div>
          {errLine}
          {netLine}
          <div className="row" style={{ marginTop: 6, justifyContent: "flex-end" }}>
            {confirmForfeit ? (
              <>
                <span className="sub" style={{ fontSize: 12 }}>{t("pages.duelBattle.forfeitConfirm")}</span>
                <button type="button" className="btn small danger" disabled={busy} onClick={() => { setConfirmForfeit(false); act("forfeit"); }}>
                  {t("pages.duelBattle.forfeit")}
                </button>
                <button type="button" className="btn small ghost" onClick={() => setConfirmForfeit(false)}>
                  {t("common.cancel")}
                </button>
              </>
            ) : (
              <button type="button" className="btn small ghost" disabled={busy} onClick={() => setConfirmForfeit(true)}>
                {t("pages.duelBattle.forfeit")}
              </button>
            )}
          </div>
        </div>
      ) : (
        <Loading />
      )}
    </Layout>
  );
}
