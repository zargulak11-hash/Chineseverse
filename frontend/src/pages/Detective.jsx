import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import Icon from "../components/Icon.jsx";
import FeatureIntro from "../components/FeatureIntro.jsx";
import Layout from "../components/Layout.jsx";
import { Empty, Loading } from "../components/ui.jsx";
import { useApi } from "../hooks/useApi.js";

// Detective Mode case files (services/detective.py). Each case is built
// for this learner when it starts and played as a server-graded round
// (/practice?source=detective&case=...); this page shows the case types,
// how this learner's cases will be built, and their real record.
export default function Detective() {
  const { t } = useTranslation();
  const { data, error } = useApi("/detective/cases");

  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  if (!data) return <Layout><Loading /></Layout>;

  const p = data.profile;
  const solved = data.cases.reduce((n, c) => n + c.solved, 0);
  return (
    <Layout>
      <header className="page-head">
        <div>
          <div className="page-eyebrow"><Icon name="search" size={13} /> {t("nav.detective")}</div>
          <h1 className="h1">{t("detective.title")}</h1>
          <p className="sub">{t("detective.subtitle")}</p>
        </div>
        <div className="kpi-row">
          <div className="kpi">
            <span className="kpi-value">{solved}</span>
            <span className="kpi-label">{t("detective.solved")}</span>
          </div>
          <div className="kpi">
            <span className="kpi-value">{t(`realLife.tier.${p.tier}`)}</span>
            <span className="kpi-label">{t("realLife.yourTier")}</span>
          </div>
        </div>
      </header>
      <FeatureIntro feature="detective" />

      <div className="ws">
        <div className="ws-main">
          <h2 className="h2 section-title">{t("detective.cases")}</h2>
          <div className="grid cards">
            {data.cases.map((c) => (
              <Link key={c.key} to={`/practice?source=detective&case=${c.key}`} className="card hover scene-card">
                <div className="row spread" style={{ margin: 0 }}>
                  <span className="scene-icon" aria-hidden="true">{c.icon}</span>
                  {c.played > 0 && (
                    <span className={`badge ${c.solved ? "good" : ""}`}>
                      {t("detective.record", { solved: c.solved, played: c.played })}
                    </span>
                  )}
                </div>
                <h3 className="h2" style={{ marginTop: 12 }}>
                  <span lang="zh-CN">{t(`detective.case.${c.key}.zh`)}</span>
                </h3>
                <p className="sub" style={{ marginTop: 4 }}><b>{t(`detective.case.${c.key}.title`)}</b></p>
                <p className="sub">{t(`detective.case.${c.key}.desc`)}</p>
                <span className="btn small primary" style={{ marginTop: 12, alignSelf: "flex-start" }}>
                  <Icon name="play" size={13} /> {t("detective.open")}
                </span>
              </Link>
            ))}
          </div>
        </div>
        <aside className="ws-side">
          <div className="card side-card">
            <p className="side-title">{t("detective.yourCases")}</p>
            <ul className="scene-rules">
              <li>{t("detective.profile.suspects", { count: p.suspects })}</li>
              <li>{t("detective.profile.listen", { pct: Math.round(p.listen_share * 100) })}</li>
              <li>{t("detective.profile.skills", { reading: Math.round(p.reading), listening: Math.round(p.listening) })}</li>
              <li>{p.red_herring ? t("detective.profile.herring") : t("detective.profile.noHerring")}</li>
              <li>
                {p.evidence_notes > 0
                  ? t("detective.profile.evidence", { count: p.evidence_notes })
                  : t("detective.profile.noEvidence")}
              </li>
            </ul>
          </div>
          <div className="card side-card">
            <p className="side-title">{t("detective.howTitle")}</p>
            <p className="sub">{t("detective.how")}</p>
          </div>
        </aside>
      </div>
    </Layout>
  );
}
