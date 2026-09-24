import { useTranslation } from "react-i18next";
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

export default function Missions() {
  const { t } = useTranslation();
  const { data, setData, error } = useApi("/missions");

  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  if (!data) return <Layout><Loading>{t("pages.missions.loading")}</Loading></Layout>;

  async function accept(missionId) {
    const updated = await api.post(`/missions/${missionId}/accept`);
    setData((ms) => (ms || []).map((m) => (m.mission.id === missionId ? updated : m)));
  }

  const active = data.filter((m) => m.status !== "completed");
  const done = data.filter((m) => m.status === "completed");

  return (
    <Layout>
      <h1 className="h1">{t("pages.missions.title")}</h1>
      <p className="sub">{t("pages.missions.subtitle")}</p>

      <div className="col" style={{ marginTop: 18 }}>
        {active.map((m) => (
          <div key={m.id} className="card">
            <div className="row spread">
              <div className="row">
                <span className="ic">
                  <Icon name={KIND_ICON[m.mission.kind] || "flag"} size={17} />
                </span>
                <div>
                  <b>{m.mission.title}</b>
                  <p className="sub" style={{ fontSize: 12 }}>{m.mission.objective}</p>
                </div>
              </div>
              <div className="row">
                <span className="ilb">HSK {m.mission.min_hsk_level}+</span>
                <span className="ilb">+{m.mission.reward_xp} {t("common.xp")}</span>
                {m.mission.reward_coins > 0 && (
                  <span className="ilb">
                    <Icon name="coin" size={11} style={{ verticalAlign: -1, marginRight: 3 }} />
                    {m.mission.reward_coins}
                  </span>
                )}
              </div>
            </div>
            {m.status === "available" ? (
              <button className="btn primary small" style={{ marginTop: 10 }} onClick={() => accept(m.mission.id)}>
                {t("pages.missions.accept")}
              </button>
            ) : (
              <div className="hbar" style={{ marginTop: 10 }}>
                <span className="muted" style={{ fontSize: 12 }}>
                  {m.progress}/{m.mission.target_count}
                </span>
                <Bar value={m.progress} max={m.mission.target_count} />
              </div>
            )}
          </div>
        ))}
      </div>

      {done.length > 0 && (
        <div style={{ marginTop: 22 }}>
          <h2 className="h2">{t("pages.missions.completed")} ({done.length})</h2>
          <div className="grid cards">
            {done.map((m) => (
              <div key={m.id} className="card" style={{ opacity: 0.8, borderColor: "var(--good)" }}>
                <span className="badge good">
                  <Icon name="check" size={11} /> {m.mission.title}
                </span>
                <p className="sub" style={{ marginTop: 8 }}>
                  +{m.mission.reward_xp} {t("common.xp")}{m.mission.reward_coins > 0 ? ` · ${m.mission.reward_coins} ${t("common.coins")}` : ""}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {data.length === 0 && <Empty>{t("pages.missions.empty")}</Empty>}
    </Layout>
  );
}
