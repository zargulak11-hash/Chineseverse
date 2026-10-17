import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../auth.js";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import MicRecorder from "../components/MicRecorder.jsx";
import UserAvatar from "../components/UserAvatar.jsx";
import { Bar, Empty, Loading } from "../components/ui.jsx";
import VoiceFeedbackCard from "../components/VoiceFeedbackCard.jsx";
import { useDashboard } from "../context/DashboardContext.jsx";
import { speakChinese } from "../zhSpeech.js";

// A scripted Real Chinese conversation, laid out as the same chat room as
// Roleplay: the person the learner meets on the left, the learner (their
// own avatar) on the right, choices as reply chips, and the speaking turn
// docked at the foot. The script, branching and grading are unchanged.

// The scenario data names roles, not people ("npc" / "learner").
function speakerLabel(t, speaker) {
  const s = String(speaker || "").toLowerCase();
  if (s === "npc") return t("pages.conversation.speakerNpc");
  if (s === "learner") return t("pages.conversation.speakerYou");
  return speaker;
}

function NpcAvatar() {
  return <span className="cv-npc" aria-hidden="true"><Icon name="user" size={20} /></span>;
}

function NpcLine({ d, t }) {
  return (
    <div className="rp-msg is-partner">
      <NpcAvatar />
      <div className="rp-line is-partner">
        <span className="rp-who">{speakerLabel(t, d.speaker)}</span>
        <div className="rp-line-main">
          <p className="rp-zh" lang="zh-CN">{d.text}</p>
          {d.text && (
            <button type="button" className="icon-btn rp-speak" onClick={() => speakChinese(d.text)} aria-label={t("roleplay.listen")} title={t("roleplay.listen")}>
              <Icon name="volume" size={16} />
            </button>
          )}
        </div>
        {d.pinyin && <p className="rp-pinyin">{d.pinyin}</p>}
        {d.english && <p className="rp-gloss">{d.english}</p>}
      </div>
    </div>
  );
}

function MyLine({ text, me }) {
  return (
    <div className="rp-msg is-learner">
      <div className="rp-line is-learner"><p className="rp-zh" lang="zh-CN">{text}</p></div>
      <UserAvatar url={me.avatar} name={me.name} size={36} className="rp-me" />
    </div>
  );
}

export default function Conversation() {
  // Back to the place on the living-world map this talk was opened from.
  const [search] = useSearchParams();
  const place = search.get("place");
  const backTo = place ? `/real-chinese?place=${place}` : "/real-chinese";
  const { t, i18n } = useTranslation();
  const { scenarioId } = useParams();
  const { dashboard, refresh } = useDashboard() || {};
  const { user } = useAuth();
  const companion = dashboard?.animal;
  const [sc, setSc] = useState(null);
  const [turnIndex, setTurnIndex] = useState(0);
  const [history, setHistory] = useState([0]); // turn_index values actually visited, in order
  const [error, setError] = useState("");
  const [text, setText] = useState("");
  const [result, setResult] = useState(null);
  const [chosen, setChosen] = useState(null); // the DialogueChoice the user picked at the current turn
  const [sent, setSent] = useState(false);
  // What the learner really said / chose at each past turn, so the thread
  // keeps it (it used to leave an empty bubble once the turn moved on).
  const [said, setSaid] = useState({});
  const scrollRef = useRef(null);

  useEffect(() => {
    api.get(`/world/scenarios/${scenarioId}`).then((data) => {
      setSc(data);
      setTurnIndex(0);
      setHistory([0]);
      setSaid({});
    }).catch((e) => setError(e.message));
  }, [scenarioId, i18n.language]);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turnIndex, result, chosen]);

  const dialogues = sc?.dialogues || [];
  // Branching means the next turn isn't necessarily "index + 1 in the
  // array" — a DialogueChoice's next_turn can jump anywhere (or past the
  // end, ending the conversation early), so turns are looked up by their
  // real turn_index, and the visited path is tracked separately from the
  // authored array order.
  const dialoguesByTurn = useMemo(() => {
    const map = {};
    for (const d of dialogues) map[d.turn_index] = d;
    return map;
  }, [dialogues]);

  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  if (!sc) return <Layout><Loading>{t("pages.conversation.entering")}</Loading></Layout>;

  const current = dialoguesByTurn[turnIndex];
  const done = !current;

  async function submit() {
    if (!text.trim() || sent) return;
    setSent(true);
    setResult(null);
    try {
      const res = await api.post("/voice/attempt", {
        spoken_text: text.trim(),
        scenario_id: sc.id,
        dialogue_id: current?.id,
        prompt_text: current?.prompt,
        expected_keywords: current?.expected_keywords || [],
        response_time_ms: 1500,
      });
      setResult(res);
      if (!res.error) setSaid((s) => ({ ...s, [turnIndex]: { text: text.trim() } }));
      refresh?.(); // XP, streak, companion -- and maybe an achievement
    } catch (e) {
      setResult({ error: e.message });
    } finally {
      setSent(false);
    }
  }

  function advanceTo(nextTurn) {
    setResult(null);
    setChosen(null);
    setText("");
    setTurnIndex(nextTurn);
    setHistory((h) => [...h, nextTurn]);
  }

  function pickChoice(choice) {
    setChosen(choice);
    setSaid((s) => ({ ...s, [turnIndex]: { choice } }));
  }

  // Workspace shape: the conversation in the main column, what it is about
  // and how far along it is beside it -- not a narrow chat floating alone.
  const turns = Object.keys(dialoguesByTurn).length;
  const turnNo = Math.min(history.length, turns);
  const keyWords = [...new Set(Object.values(dialoguesByTurn).flatMap((d) => d.expected_keywords || []))];
  const me = { avatar: dashboard?.avatar_url, name: user?.username };
  const voiceTurn = current && !(current.choices?.length > 0) && current.requires_voice;

  return (
    <Layout>
      <header className="card rp-room-head">
        <Link to={backTo} className="icon-btn" aria-label={sc.scenario_type === "case" ? t("pages.conversation.leaveCase") : t("pages.conversation.leaveConversation")}>
          <Icon name="arrowLeft" size={18} />
        </Link>
        <span className="rp-avatar cv-head-avatar"><NpcAvatar /></span>
        <div className="rp-room-id">
          <div className="page-eyebrow"><Icon name={sc.is_case ? "search" : "chat"} size={13} /> {t("nav.realChinese")}</div>
          <h1 className="h1 rp-room-title">{sc.title}</h1>
          <p className="sub">{sc.description}</p>
        </div>
        <div className="rp-room-meta">
          <span className="badge">HSK {sc.min_hsk_level} · <Icon name="star" size={11} /> {sc.difficulty}</span>
          <div className="rp-turns">
            <span className="rp-turns-label">{t("pages.conversation.turnOf", { n: done ? turns : turnNo, total: turns })}</span>
            <span className="rp-turns-bar" aria-hidden="true"><span style={{ width: `${done ? 100 : (turnNo / Math.max(1, turns)) * 100}%` }} /></span>
          </div>
        </div>
      </header>

      <div className="ws rp-ws">
      <div className="ws-main">
      <section className="card rp-chat" aria-label={sc.title}>
        <div className="rp-thread" aria-live="polite">
          {history.map((turn) => {
            const d = dialoguesByTurn[turn];
            if (!d) return null;
            const isCurrent = turn === turnIndex && !done;
            const hasChoices = d.choices && d.choices.length > 0;
            const mine = said[turn];
            return (
              <div key={d.id} className="cv-turn">
                {d.text && <NpcLine d={d} t={t} />}

                {hasChoices && isCurrent && !chosen && (
                  <div className="cv-choices">
                    <p className="sub">{t("pages.conversation.whatDoYouSay")}</p>
                    {d.choices.map((c) => (
                      <button key={c.id} type="button" className="rp-suggest-chip cv-choice" onClick={() => pickChoice(c)}>
                        <b lang="zh-CN">{c.label}</b>
                      </button>
                    ))}
                  </div>
                )}
                {hasChoices && (isCurrent ? chosen : mine?.choice) && (() => {
                  const c = isCurrent ? chosen : mine.choice;
                  return (
                    <>
                      <MyLine text={c.label} me={me} />
                      {c.response_text && (
                        <div className="rp-msg is-partner">
                          <NpcAvatar />
                          <div className="rp-line is-partner"><p className="rp-zh" lang="zh-CN">{c.response_text}</p></div>
                        </div>
                      )}
                      <div className={`cv-note${c.is_best ? " is-best" : ""}`}>
                        <Icon name={c.is_best ? "check" : "chat"} size={13} /> {c.feedback}
                      </div>
                      {isCurrent && (
                        <div className="cv-next">
                          <button type="button" className="btn primary" onClick={() => advanceTo(c.next_turn ?? d.turn_index + 1)}>
                            {t("common.continue")} <Icon name="arrowRight" size={14} />
                          </button>
                        </div>
                      )}
                    </>
                  );
                })()}

                {!hasChoices && d.requires_voice && !isCurrent && mine?.text && <MyLine text={mine.text} me={me} />}
                {!hasChoices && d.requires_voice && isCurrent && (!result || result.error) && (
                  <div className="cv-task">
                    <Icon name="mic" size={14} /> <span>{d.prompt}</span>
                  </div>
                )}
                {!hasChoices && !d.requires_voice && isCurrent && (
                  <div className="cv-next">
                    <button type="button" className="btn primary" onClick={() => advanceTo(d.turn_index + 1)}>
                      {t("common.continue")} <Icon name="arrowRight" size={14} />
                    </button>
                  </div>
                )}
                {!hasChoices && isCurrent && result && (
                  result.error ? (
                    <div className="cv-note is-bad" role="alert"><Icon name="alert" size={14} /> {result.error}</div>
                  ) : (
                    <>
                      <MyLine text={text} me={me} />
                      <div className="cv-feedback">
                        <VoiceFeedbackCard
                          attempt={result.attempt}
                          reaction={result.reaction}
                          companionSlug={companion?.slug}
                          companionName={companion?.name}
                        />
                      </div>
                      {result.improvement && (
                        <div className="cv-note is-tip"><Icon name="sparkles" size={13} /> {result.improvement}</div>
                      )}
                      <div className="cv-next">
                        <button type="button" className="btn primary" onClick={() => advanceTo(d.turn_index + 1)}>
                          {t("common.continue")} <Icon name="arrowRight" size={14} />
                        </button>
                      </div>
                    </>
                  )
                )}
              </div>
            );
          })}
          {done && (
            <div className="cv-done">
              <span className="cv-done-icon" aria-hidden="true"><Icon name="check" size={26} /></span>
              <p>{t("pages.conversation.completed")}</p>
              <Link to={backTo} className="btn primary">{t("pages.conversation.backToWorld")}</Link>
            </div>
          )}
          <div ref={scrollRef} />
        </div>

        {/* Also after a failed attempt: the error used to replace the box,
            and with it the only way on (no retry, no skip, no continue). */}
        {voiceTurn && (!result || result.error) && (
          <div className="rp-compose">
            <label className="side-title" htmlFor="cv-input">{t("pages.conversation.micPlaceholder")}</label>
            <div className="rp-compose-row">
              <input
                id="cv-input"
                className="input"
                lang="zh-CN"
                placeholder={t("pages.conversation.micPlaceholder")}
                value={text}
                onChange={(e) => setText(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && submit()}
                disabled={sent}
              />
              <span className="rp-mic"><MicRecorder onTranscript={(heard) => setText(heard)} disabled={sent} showStatus /></span>
              <button type="button" className="btn primary rp-send" onClick={submit} disabled={sent || !text.trim()}>
                <Icon name="mic" size={15} /> {sent ? t("pages.conversation.checking") : t("pages.conversation.speak")}
              </button>
            </div>
            <div className="rp-compose-foot">
              {current.expected_keywords?.length > 0 ? (
                <p className="sub rp-note">{t("pages.conversation.hint")}: <span lang="zh-CN">{current.expected_keywords.join(" · ")}</span></p>
              ) : <span />}
              <button type="button" className="btn small ghost" onClick={() => advanceTo(current.turn_index + 1)}>
                {t("pages.conversation.skipForNow")}
              </button>
            </div>
          </div>
        )}
      </section>
      </div>
      <aside className="ws-side">
        <div className="card side-card">
          <p className="side-title">{t("pages.conversation.progressTitle")}</p>
          <Bar value={done ? 100 : (turnNo / Math.max(1, turns)) * 100} />
          <p className="sub" style={{ marginTop: 8 }}>{t("pages.conversation.turnOf", { n: done ? turns : turnNo, total: turns })}</p>
        </div>
        {keyWords.length > 0 && (
          <div className="card side-card">
            <p className="side-title">{t("pages.conversation.keyWords")}</p>
            <div className="chip-row">
              {keyWords.map((w) => (
                <button key={w} type="button" className="rp-chip" lang="zh-CN" onClick={() => speakChinese(w)} aria-label={`${t("roleplay.listen")}: ${w}`}>
                  {w}
                </button>
              ))}
            </div>
          </div>
        )}
      </aside>
      </div>
    </Layout>
  );
}
