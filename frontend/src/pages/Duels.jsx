import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api.js";
import AnimalAvatar from "../components/AnimalAvatar.jsx";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import { Empty } from "../components/ui.jsx";
import { useDashboard } from "../context/DashboardContext.jsx";
import { useApi } from "../hooks/useApi.js";

const CHALLENGE_TYPE_KEYS = [
  { value: "", key: "auto" },
  { value: "meaning", key: "vocabulary" },
  { value: "tone", key: "tones" },
  { value: "character", key: "characters" },
  { value: "memory", key: "memory" },
  { value: "listening", key: "listening" },
  { value: "reaction", key: "reactionSpeed" },
  { value: "recognition", key: "speaking" },
];

export default function Duels() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { data, error } = useApi("/duels");
  const duels = data || [];
  const { dashboard: my } = useDashboard();
  const [open, setOpen] = useState(false);
  const [opponent, setOpponent] = useState("Buddy");
  const [challengeType, setChallengeType] = useState("");
  const [starting, setStarting] = useState(false);
  const [formError, setFormError] = useState("");

  if (error) return <Layout><Empty>{error}</Empty></Layout>;

  async function start() {
    setFormError("");
    setStarting(true);
    try {
      const d = await api.post("/duels", {
        opponent_username: opponent === "Buddy" ? "Buddy" : opponent,
        challenge_type: challengeType || null,
      });
      navigate(`/duels/${d.id}`);
    } catch (e) {
      setFormError(e.message);
    } finally {
      setStarting(false);
    }
  }

  const mySlug = my?.animal?.slug;

  return (
    <Layout>
      <div className="row spread">
        <div>
          <h1 className="h1">{t("pages.duels.title")}</h1>
          <p className="sub">{t("pages.duels.subtitle")}</p>
        </div>
        <button className="btn primary" onClick={() => setOpen(true)}>
          <Icon name="swords" size={14} /> {t("pages.duels.newDuel")}
        </button>
      </div>

      {open && (
        <div className="modal">
          <div className="card">
            <h2 className="h2">{t("pages.duels.challengeSomeone")}</h2>
            <div className="field" style={{ marginTop: 12 }}>
              <label>{t("pages.duels.opponent")}</label>
              <input
                className="input"
                value={opponent}
                onChange={(e) => setOpponent(e.target.value)}
                placeholder={t("pages.duels.opponentPlaceholder")}
              />
            </div>
            <div className="field">
              <label>{t("pages.duels.challengeFocus")}</label>
              <select
                className="input"
                value={challengeType}
                onChange={(e) => setChallengeType(e.target.value)}
              >
                {CHALLENGE_TYPE_KEYS.map((c) => (
                  <option key={c.value} value={c.value}>{t(`pages.duels.challengeType.${c.key}`)}</option>
                ))}
              </select>
            </div>
            {formError && <p className="formerr">{formError}</p>}
            <div className="row">
              <button className="btn primary" onClick={start} disabled={starting}>
                {starting ? t("pages.duels.creating") : t("pages.duels.start")}
              </button>
              <button className="btn ghost" onClick={() => setOpen(false)}>{t("common.cancel")}</button>
            </div>
          </div>
        </div>
      )}

      <div className="col" style={{ marginTop: 18 }}>
        {duels.map((d) => (
          <div key={d.id} className="card">
            <div className="duelbanner" style={{ padding: "0 0 14px" }}>
              <div className="row">
                {mySlug ? (
                  <AnimalAvatar slug={mySlug} accentColor={my?.animal?.accent_color} size={48} />
                ) : (
                  <span style={{ fontSize: 40 }}>🐾</span>
                )}
                <div className="col" style={{ gap: 2 }}>
                  <b>{t("pages.duels.you")}</b>
                  <span className="ilb">{d.my_score ?? 0}</span>
                </div>
              </div>
              <span className="vs">{t("pages.duels.vs")}</span>
              <div className="row">
                <div className="col" style={{ gap: 2 }}>
                  <b>{d.opponent}</b>
                  <span className="ilb">{d.opp_score ?? (d.awaiting_opponent ? "—" : 0)}</span>
                </div>
                <span className="ic" style={{ width: 44, height: 44 }}>
                  <Icon name={d.is_ai_opponent ? "sparkles" : "user"} size={20} />
                </span>
              </div>
            </div>
            <div className="row spread">
              <span className={`badge ${d.finished ? "good" : "accent"}`}>
                {d.finished
                  ? (d.winner === d.opponent ? t("pages.duels.opponentWon") : d.winner ? t("pages.duels.youWon") : t("pages.duels.draw"))
                  : d.awaiting_opponent
                  ? t("pages.duels.waitingFor", { opponent: d.opponent })
                  : d.is_ai_opponent
                  ? t("pages.duels.practiceVsAi")
                  : t("pages.duels.inProgress")}
              </span>
              <Link to={`/duels/${d.id}`}>
                <button className="btn small">{t("pages.duels.open")}</button>
              </Link>
            </div>
          </div>
        ))}
      </div>
      {duels.length === 0 && <Empty>{t("pages.duels.empty")}</Empty>}
    </Layout>
  );
}