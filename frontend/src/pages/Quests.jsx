import { animate, stagger } from "animejs";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { prefersReducedMotion } from "../anime.js";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import { Empty, Loading } from "../components/ui.jsx";
import { useDashboard } from "../context/DashboardContext.jsx";
import { useApi } from "../hooks/useApi.js";

// Today's three quests (services/gamification.py QUEST_TEMPLATES). They
// advance by themselves from real activity, server-side; this page shows
// how far each one is, points to where it is done, and claims the reward
// once the server says it is complete.

const QUEST_ICON = { speaking: "mic", vocab: "type", lesson: "book", case: "search", listening: "ear", duel: "swords" };
// Where each kind of quest is actually advanced (the activity, not a button).
const QUEST_PATH = {
  speaking: "/real-chinese", vocab: "/vocabulary", lesson: "/lessons", case: "/detective", listening: "/real-chinese", duel: "/duels",
};

function stateOf(q) {
  return q.claimed ? "claimed" : q.completed ? "ready" : "open";
}

export default function Quests() {
  const { t } = useTranslation();
  const { data, setData, error } = useApi("/quests/today");
  const { refresh } = useDashboard();
  const quests = data || [];
  const [claimError, setClaimError] = useState("");
  const [claiming, setClaiming] = useState(null);
  const listRef = useRef(null);

  useEffect(() => {
    const root = listRef.current;
    if (!root || quests.length === 0) return;
    const targets = Array.from(root.children);
    if (prefersReducedMotion()) {
      targets.forEach((el) => {
        el.style.opacity = 1;
      });
      return;
    }
    animate(targets, {
      opacity: [0, 1],
      translateY: [22, 0],
      duration: 560,
      delay: stagger(55),
      ease: "outElastic(1, .75)",
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [quests.length]);

  async function claim(q) {
    setClaimError("");
    setClaiming(q.id);
    try {
      const updated = await api.post(`/quests/${q.id}/claim`);
      setData((qs) => (qs || []).map((x) => (x.id === q.id ? updated : x)));
      refresh?.(); // XP and coins changed
    } catch (e) {
      setClaimError(e.message);
    } finally {
      setClaiming(null);
    }
  }

  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  // The "no quests" message used to show while the request was in flight.
  if (!data) return <Layout><Loading /></Layout>;

  const done = quests.filter((q) => q.completed).length;
  const xpTotal = quests.reduce((n, q) => n + q.reward_xp, 0);
  const xpClaimed = quests.filter((q) => q.claimed).reduce((n, q) => n + q.reward_xp, 0);

  return (
    <Layout>
      <header className="page-head">
        <div>
          <div className="page-eyebrow"><Icon name="target" size={13} /> {t("nav.groupPlay")}</div>
          <h1 className="h1">{t("pages.quests.title")}</h1>
          <p className="sub">{t("pages.quests.subtitle")}</p>
        </div>
        {quests.length > 0 && (
          <div className="kpi-row">
            <div className="kpi"><span className="kpi-value">{done}/{quests.length}</span><span className="kpi-label">{t("pages.quests.kpiDone")}</span></div>
            <div className="kpi"><span className="kpi-value">{xpClaimed}/{xpTotal}</span><span className="kpi-label">{t("pages.quests.kpiXp")}</span></div>
          </div>
        )}
      </header>
      {claimError && <p className="formerr" role="alert">{claimError}</p>}

      {quests.length > 0 && (
        <div className="qs-day" aria-hidden="true">
          {quests.map((q) => <span key={q.id} className={`qs-day-seg is-${stateOf(q)}`} />)}
        </div>
      )}

      <ol className="qs-list" ref={listRef} data-self-animate="true">
        {quests.map((q) => {
          const st = stateOf(q);
          const pct = Math.min(100, Math.round((q.progress / Math.max(q.target, 1)) * 100));
          return (
            <li key={q.id} className={`qs-quest is-${st}`}>
              <div className="qs-ring" style={{ "--p": pct }} aria-hidden="true">
                <span className="qs-ring-icon"><Icon name={st === "open" ? QUEST_ICON[q.quest_type] || "target" : "check"} size={20} /></span>
              </div>
              <div className="qs-body">
                <div className="qs-title-row">
                  <h2 className="qs-title">{q.title}</h2>
                  <span className="qs-count">{q.progress}/{q.target}</span>
                </div>
                <p className="qs-desc">{q.description}</p>
                {q.flavor && <p className="qs-flavor">{q.flavor}</p>}
                <div className="qs-foot">
                  <span className="qs-reward">+{q.reward_xp} {t("common.xp")}</span>
                  <span className="qs-reward"><Icon name="coin" size={12} /> {q.reward_coins}</span>
                  <span className="qs-action">
                    {st === "ready" && (
                      <button type="button" className="btn primary small" onClick={() => claim(q)} disabled={claiming !== null}>
                        <Icon name="award" size={13} /> {t("pages.quests.claimReward")}
                      </button>
                    )}
                    {st === "claimed" && (
                      <span className="badge good"><Icon name="check" size={10} /> {t("pages.quests.claimed")}</span>
                    )}
                    {st === "open" && QUEST_PATH[q.quest_type] && (
                      <Link to={QUEST_PATH[q.quest_type]} className="btn small ghost">
                        {t("pages.quests.goDo")} <Icon name="arrowRight" size={13} />
                      </Link>
                    )}
                  </span>
                </div>
              </div>
            </li>
          );
        })}
      </ol>
      {quests.length === 0 && <Empty>{t("pages.quests.empty")}</Empty>}
      {quests.length > 0 && <p className="sub qs-note">{t("pages.quests.howNote")}</p>}
    </Layout>
  );
}
