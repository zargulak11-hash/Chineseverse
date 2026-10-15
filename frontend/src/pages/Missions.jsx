import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import { Bar, Empty, Loading } from "../components/ui.jsx";
import { useApi } from "../hooks/useApi.js";

const KIND_ICON = {
  speak: "mic",
  conversation: "chat",
  case: "search",
  listening: "ear",
  duel: "swords",
  vocab: "type",
  teach: "teach",
  world: "world",
};

// Where a mission is actually done. Missions advance on their own from that
// real activity (server-side); this page only points the learner there.
const KIND_PATH = {
  listening: "/voice-companion",
  duel: "/duels",
  vocab: "/vocabulary",
  teach: "/pet-teacher",
};

function missionPath(mission) {
  if (mission.scenario_slug) {
    return `/real-chinese/${mission.scenario_type === "case" ? "case" : "talk"}/${mission.scenario_slug}`;
  }
  return KIND_PATH[mission.kind] || "/real-chinese";
}

// The board: missions under way first (with how far each is and where to
// go on), then the ones that can be taken on, the ones a level away, and a
// log of what is done. Statuses (available -> active -> completed) and the
// level lock come from the server.
function Rewards({ m }) {
  const { t } = useTranslation();
  return (
    <span className="ms-rewards">
      <span className="ilb">HSK {m.mission.min_hsk_level}+</span>
      <span className="ilb">+{m.mission.reward_xp} {t("common.xp")}</span>
      {m.mission.reward_coins > 0 && (
        <span className="ilb">
          <Icon name="coin" size={11} style={{ verticalAlign: -1, marginRight: 3 }} />
          {m.mission.reward_coins}
        </span>
      )}
    </span>
  );
}

function Ticket({ m, children, state }) {
  return (
    <li className={`ms-ticket is-${state}`}>
      <span className="ms-kind" aria-hidden="true"><Icon name={KIND_ICON[m.mission.kind] || "flag"} size={18} /></span>
      <div className="ms-body">
        <div className="ms-head">
          <h3 className="ms-title">{m.mission.title}</h3>
          <Rewards m={m} />
        </div>
        <p className="ms-objective">{m.mission.objective}</p>
        {children}
      </div>
    </li>
  );
}

export default function Missions() {
  const { t } = useTranslation();
  const { data, setData, error } = useApi("/missions");
  const [actionError, setActionError] = useState("");
  const [accepting, setAccepting] = useState(null);

  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  if (!data) return <Layout><Loading>{t("pages.missions.loading")}</Loading></Layout>;

  async function accept(missionId) {
    setActionError("");
    setAccepting(missionId);
    try {
      const updated = await api.post(`/missions/${missionId}/accept`);
      setData((ms) => (ms || []).map((m) => (m.mission.id === missionId ? updated : m)));
    } catch (e) {
      setActionError(e.message);
    } finally {
      setAccepting(null);
    }
  }

  const active = data.filter((m) => m.status !== "completed" && !m.locked && m.status !== "available");
  const available = data.filter((m) => m.status === "available" && !m.locked);
  const locked = data.filter((m) => m.status !== "completed" && m.locked);
  const done = data.filter((m) => m.status === "completed");

  return (
    <Layout>
      <header className="page-head">
        <div>
          <div className="page-eyebrow"><Icon name="flag" size={13} /> {t("nav.groupPlay")}</div>
          <h1 className="h1">{t("pages.missions.title")}</h1>
          <p className="sub">{t("pages.missions.subtitle")}</p>
        </div>
        {data.length > 0 && (
          <div className="kpi-row">
            <div className="kpi"><span className="kpi-value">{active.length}</span><span className="kpi-label">{t("pages.missions.inProgress")}</span></div>
            <div className="kpi"><span className="kpi-value">{done.length}/{data.length}</span><span className="kpi-label">{t("pages.missions.completed")}</span></div>
          </div>
        )}
      </header>

      {actionError && <p className="formerr" role="alert">{actionError}</p>}

      <div className="ws">
        <div className="ws-main">
          {active.length > 0 && (
            <section aria-labelledby="ms-active">
              <h2 className="h2 section-title" id="ms-active">{t("pages.missions.inProgress")}</h2>
              <ul className="ms-list">
                {active.map((m) => (
                  <Ticket key={m.id} m={m} state="active">
                    <div className="ms-progress">
                      <div className="hbar" style={{ flex: 1, minWidth: 0 }}>
                        <span className="muted" style={{ fontSize: "var(--text-xs)" }}>
                          {m.progress}/{m.mission.target_count}
                        </span>
                        <Bar value={m.progress} max={m.mission.target_count} />
                      </div>
                      <Link to={missionPath(m.mission)} className="btn primary small">
                        <Icon name={KIND_ICON[m.mission.kind] || "flag"} size={13} /> {t("pages.missions.start")}
                      </Link>
                    </div>
                  </Ticket>
                ))}
              </ul>
            </section>
          )}

          {available.length > 0 && (
            <section aria-labelledby="ms-available">
              <h2 className="h2 section-title" id="ms-available">{t("pages.missions.available")}</h2>
              <ul className="ms-list">
                {available.map((m) => (
                  <Ticket key={m.id} m={m} state="available">
                    <button type="button" className="btn small ms-accept" onClick={() => accept(m.mission.id)} disabled={accepting !== null}>
                      <Icon name="plus" size={13} /> {t("pages.missions.accept")}
                    </button>
                  </Ticket>
                ))}
              </ul>
            </section>
          )}

          {locked.length > 0 && (
            <section aria-labelledby="ms-locked">
              <h2 className="h2 section-title" id="ms-locked">{t("pages.missions.lockedTitle")}</h2>
              <ul className="ms-list">
                {locked.map((m) => (
                  <Ticket key={m.id} m={m} state="locked">
                    <span className="badge"><Icon name="lock" size={11} /> {t("pages.missions.locked", { level: m.mission.min_hsk_level })}</span>
                  </Ticket>
                ))}
              </ul>
            </section>
          )}

          {data.length === 0 && <Empty>{t("pages.missions.empty")}</Empty>}
        </div>

        <aside className="ws-side">
          <div className="card side-card">
            <p className="side-title">{t("pages.missions.completed")} ({done.length})</p>
            {done.length === 0 ? (
              <p className="sub" style={{ margin: 0 }}>{t("pages.missions.noneDone")}</p>
            ) : (
              <ul className="ms-log">
                {done.map((m) => (
                  <li key={m.id}>
                    <span className="ms-log-check" aria-hidden="true"><Icon name="check" size={12} /></span>
                    <span className="ms-log-title">{m.mission.title}</span>
                    <span className="sub">
                      +{m.mission.reward_xp} {t("common.xp")}{m.mission.reward_coins > 0 ? ` · ${m.mission.reward_coins} ${t("common.coins")}` : ""}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div className="card side-card">
            <p className="side-title">{t("pages.missions.howTitle")}</p>
            <p className="sub" style={{ margin: 0 }}>{t("pages.missions.howText")}</p>
          </div>
        </aside>
      </div>
    </Layout>
  );
}
