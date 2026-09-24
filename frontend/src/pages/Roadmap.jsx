import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import { Bar, Empty, Loading } from "../components/ui.jsx";
import { useApi } from "../hooks/useApi.js";

export default function Roadmap() {
  const { t } = useTranslation();
  const { data: r, error } = useApi("/hsk/roadmap");

  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  if (!r) return <Layout><Loading>{t("pages.roadmap.loading")}</Loading></Layout>;

  const stateIcon = (s) =>
    s === "locked" ? "lock" : s === "current" ? "star" : "check";
  const stateLabel = (s) =>
    s === "locked" ? t("pages.roadmap.locked") : s === "current" ? t("pages.roadmap.current") : t("pages.roadmap.unlocked");

  return (
    <Layout>
      <h1 className="h1">{t("pages.roadmap.title")}</h1>
      <p className="sub">{r.note}</p>
      <div className="hbar" style={{ marginTop: 14 }}>
        <span className="muted">{t("pages.roadmap.overall")}</span>
        <Bar value={r.overall_mastery} />
        <span>{r.overall_mastery.toFixed(0)}%</span>
      </div>

      <div className="grid" style={{ marginTop: 20 }}>
        {r.levels.map((lvl) => (
          <div key={lvl.level} className="card"
            style={lvl.status === "locked" ? { opacity: 0.6 } : {}}>
            <div className="row spread">
              <div className="row">
                <span className="ic">
                  <Icon name={stateIcon(lvl.status)} size={16} />
                </span>
                <h2 className="h2">HSK {lvl.level}</h2>
                <span className={`badge ${lvl.status === "current" ? "accent" : ""}`}>
                  {stateLabel(lvl.status)}
                </span>
              </div>
              <span className="muted">
                {lvl.vocab_mastered}/{lvl.vocab_total} {t("pages.roadmap.words")}
              </span>
            </div>
            <div className="hbar">
              <span className="muted" style={{ width: 90, fontSize: 12 }}>
                {t("pages.roadmap.mastery")}
              </span>
              <Bar value={lvl.mastery} max={100} />
              <span style={{ width: 40, textAlign: "right" }}>{lvl.mastery.toFixed(0)}%</span>
            </div>
            <div className="hbar" style={{ marginTop: 6 }}>
              <span className="muted" style={{ width: 90, fontSize: 12 }}>
                {t("pages.roadmap.lessons")}
              </span>
              <Bar value={lvl.lessons_completed} max={10} alt />
              <span style={{ width: 40, textAlign: "right" }}>{lvl.lessons_completed}</span>
            </div>
            {lvl.ready_for_next ? (
              <BadgeOK>{lvl.level + 1 <= 6 ? t("pages.roadmap.readyForNext", { level: lvl.level + 1 }) : t("pages.roadmap.maxLevel")}</BadgeOK>
            ) : (
              lvl.reason && <p className="muted" style={{ fontSize: 12, marginTop: 8 }}>{lvl.reason}</p>
            )}
          </div>
        ))}
      </div>
      <Link to="/vocabulary">
        <button className="btn primary" style={{ marginTop: 18 }}>{t("pages.roadmap.practiceVocab")}</button>
      </Link>
    </Layout>
  );
}

function BadgeOK({ children }) {
  return <p className="badge good" style={{ marginTop: 10 }}>{children}</p>;
}