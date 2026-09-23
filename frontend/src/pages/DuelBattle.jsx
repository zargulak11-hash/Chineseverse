import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";
import { api } from "../api.js";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import MicRecorder from "../components/MicRecorder.jsx";
import { Celebration, Empty, Loading } from "../components/ui.jsx";
import { usePrefs } from "../prefs.jsx";

const TYPE_LABEL = {
  pinyin: "Pinyin", meaning: "Meaning", translate: "Translate",
  recognition: "Speak it", tone: "Tone", character: "Character",
  memory: "Memory", listening: "Listening", reaction: "Reaction speed",
};

export default function DuelBattle() {
  const { t } = useTranslation();
  const { duelId } = useParams();
  const { soundEnabled } = usePrefs() || {};
  const [duel, setDuel] = useState(null);
  const [idx, setIdx] = useState(0);
  const [feedback, setFeedback] = useState(null);
  const [score, setScore] = useState(0);
  const [timer, setTimer] = useState(100);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [celebrating, setCelebrating] = useState(false);
  const celebratedRef = useRef(false);
  const answered = useRef(0);

  useEffect(() => {
    api.get(`/duels/${duelId}`).then(setDuel).catch((e) => setError(e.message));
  }, [duelId]);

  useEffect(() => {
    if (!duel || duel.finished) return;
    const t = setInterval(() => {
      setTimer((p) => Math.max(0, p - 2.5));
    }, 100);
    return () => clearInterval(t);
  }, [duel, idx]);

  const q = duel?.questions?.[idx];

  useEffect(() => {
    if (soundEnabled && q?.type === "listening" && q.tts_text && window.speechSynthesis) {
      const utter = new SpeechSynthesisUtterance(q.tts_text);
      utter.lang = "zh-CN";
      window.speechSynthesis.cancel();
      window.speechSynthesis.speak(utter);
    }
  }, [idx, q?.type, q?.tts_text, soundEnabled]);

  useEffect(() => {
    if (!duel?.finished || duel.awaiting_opponent || celebratedRef.current) return;
    const meWon = (duel.my_score ?? 0) > (duel.opp_score ?? 0);
    if (meWon) {
      celebratedRef.current = true;
      setCelebrating(true);
    }
  }, [duel]);

  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  if (!duel) return <Layout><Loading>Loading duel…</Loading></Layout>;

  function replay() {
    if (soundEnabled && q?.tts_text && window.speechSynthesis) {
      const utter = new SpeechSynthesisUtterance(q.tts_text);
      utter.lang = "zh-CN";
      window.speechSynthesis.cancel();
      window.speechSynthesis.speak(utter);
    }
  }

  async function answer(option) {
    if (busy || !q) return;
    setBusy(true);
    try {
      const r = await api.post(`/duels/${duel.id}/answer`, {
        index: q.index,
        answer: option || q.prompt,
        response_time_ms: Math.round((100 - timer) * 1500),
      });
      setFeedback(r);
      setScore(r.my_score ?? score);
      answered.current += 1;
      setTimer(100);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function finish() {
    setBusy(true);
    try {
      const d = await api.post(`/duels/${duel.id}/finish`);
      setDuel(d);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  if (duel.awaiting_opponent) {
    return (
      <Layout>
        <div className="card center reveal" style={{ maxWidth: 520, margin: "40px auto" }}>
          <div className="reveal-icon" style={{ fontSize: 52 }}>⏳</div>
          <h1 className="h1">{t("pages.duelBattle.waitingFor", { name: duel.opponent })}</h1>
          <p className="sub">
            You scored {duel.my_score ?? 0}. This is a real opponent, so nothing gets
            decided until they actually play their turn — check back once they have.
          </p>
          <Link to="/duels">
            <button className="btn primary" style={{ marginTop: 14 }}>{t("pages.duelBattle.backToDuels")}</button>
          </Link>
        </div>
      </Layout>
    );
  }

  if (duel.finished) {
    const draw = (duel.my_score ?? 0) === (duel.opp_score ?? 0);
    const meWon = !draw && (duel.my_score ?? 0) > (duel.opp_score ?? 0);
    return (
      <Layout>
        <Celebration
          show={celebrating}
          icon="🏆"
          title={t("pages.duelBattle.victory")}
          subtitle={`You ${duel.my_score ?? 0} · ${duel.opponent} ${duel.opp_score ?? 0}`}
          onClose={() => setCelebrating(false)}
          actionLabel="Nice!"
        />
        <div className={`card center reveal${meWon ? " burst" : ""}`} style={{ maxWidth: 520, margin: "40px auto" }}>
          {duel.is_ai_opponent && (
            <span className="badge accent" style={{ marginBottom: 10 }}>{t("pages.duelBattle.practiceMode")}</span>
          )}
          <div className="reveal-icon" style={{ fontSize: 52 }}>{draw ? "🤝" : meWon ? "🏆" : "😤"}</div>
          <h1 className="h1">{draw ? t("pages.duelBattle.draw") : meWon ? t("pages.duelBattle.victory") : t("pages.duelBattle.lost", { name: duel.opponent })}</h1>
          <p className="sub">You {duel.my_score ?? 0} · {duel.opponent} {duel.opp_score ?? 0}</p>
          <Link to="/duels">
            <button className="btn primary" style={{ marginTop: 14 }}>{t("pages.duelBattle.backToDuels")}</button>
          </Link>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <Link to="/duels" className="sub">← Forfeit duel</Link>
      <div className="card" style={{ marginTop: 12 }}>
        <div className="row spread">
          <span className="badge accent">{duel.challenge_type || "weakest strand"}</span>
          <span className="muted">Your score · {score}</span>
        </div>
        <div className={`timerbar${timer < 30 ? " low" : ""}`} style={{ marginTop: 12 }}>
          <div style={{ width: `${timer}%` }} />
        </div>
      </div>

      {q ? (
        <div className="card" style={{ marginTop: 16 }}>
          <div className="row spread">
            <span className="ilb">Round {idx + 1}/{duel.questions.length}</span>
            <span className="ilb">{TYPE_LABEL[q.type] || q.type}</span>
          </div>
          <h2 className="h2" style={{ marginTop: 14, fontSize: 22 }}>{q.prompt}</h2>
          {q.type === "listening" && (
            <button className="btn small ghost" style={{ marginTop: 8 }} onClick={replay}>
              🔊 Replay
            </button>
          )}

          {feedback && (
            <p
              className="sub"
              style={{ marginTop: 10, color: feedback.correct ? "var(--good)" : "var(--bad)", fontWeight: 700 }}
            >
              <Icon name={feedback.correct ? "check" : "x"} size={13} style={{ verticalAlign: -2, marginRight: 4 }} />
              {feedback.correct ? "Correct" : "Wrong answer"}
            </p>
          )}

          <div className="col" style={{ marginTop: 14 }}>
            {(q.options || []).map((opt) => (
              <button
                key={opt}
                className={`option${feedback && feedback.answer === opt && feedback.correct ? " correct" : ""}${
                  feedback && feedback.answer === opt && !feedback.correct ? " wrong" : ""
                }`}
                onClick={() => answer(opt)}
                disabled={busy || !!feedback}
              >
                {opt}
              </button>
            ))}
            {!q.options && q.type === "recognition" && !feedback && (
              <div className="row center" style={{ justifyContent: "center" }}>
                <MicRecorder onTranscript={(t) => answer(t)} disabled={busy} />
                <span className="muted" style={{ fontSize: 12 }}>Say it out loud</span>
              </div>
            )}
            {!q.options && q.type !== "recognition" && (
              <button className="option" onClick={() => answer("")} disabled={busy || !!feedback}>
                Submit guess
              </button>
            )}
          </div>

          <div className="row" style={{ marginTop: 16 }}>
            {feedback && (
              <>
                {idx + 1 < duel.questions.length ? (
                  <button className="btn primary" onClick={() => { setIdx(idx + 1); setFeedback(null); }} disabled={busy}>
                    Next round
                  </button>
                ) : (
                  <button className="btn primary" onClick={finish} disabled={busy}>
                    Finish duel
                  </button>
                )}
              </>
            )}
          </div>
        </div>
      ) : (
        <Empty>No questions loaded.</Empty>
      )}
    </Layout>
  );
}