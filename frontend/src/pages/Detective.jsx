import { useState } from "react";
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
// how this learner's cases will be built, and their real record. Below them
// are the hand-written case files (services/case_files.py), one HSK level
// at a time; each opens as a dossier (/detective/file/:slug).
function FileCard({ f }) {
  const { t } = useTranslation();
  const body = (
    <>
      <div className="row spread" style={{ margin: 0 }}>
        <span className="scene-icon" aria-hidden="true">{f.icon}</span>
        {f.locked ? (
          <span className="badge"><Icon name="lock" size={11} /> {t("detective.files.locked", { level: f.gate })}</span>
        ) : f.played > 0 && (
          <span className={`badge ${f.solved ? "good" : ""}`}>{t("detective.record", { solved: f.solved, played: f.played })}</span>
        )}
      </div>
      <h3 className="h2" style={{ marginTop: 12 }}><span lang="zh-CN">{f.title_zh}</span></h3>
      <p className="sub" style={{ marginTop: 4 }}><b>{f.title}</b></p>
      <p className="sub">{f.summary}</p>
      <p className="sub book-card-meta">
        <span>{t("detective.files.suspects", { count: f.suspects })}</span>
        <span>{t("detective.files.clues", { count: f.clues })}</span>
      </p>
    </>
  );
  return f.locked
    ? <div className="card scene-card is-locked">{body}</div>
    : <Link to={`/detective/file/${f.slug}`} className="card hover scene-card">{body}</Link>;
}

export default function Detective() {
  const { t } = useTranslation();
  const { data, error } = useApi("/detective/cases");
  const [picked, setPicked] = useState(null);

  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  if (!data) return <Layout><Loading /></Layout>;

  const p = data.profile;
  const files = data.files || [];
  const solved = data.cases.reduce((n, c) => n + c.solved, 0) + files.reduce((n, f) => n + f.solved, 0);
  // Open levels that have cases; the learner's own level first.
  const withCases = (data.file_levels || []).filter((x) => x.cases > 0);
  const own = [...withCases].reverse().find((x) => !x.locked)?.level ?? withCases[0]?.level;
  const level = picked ?? own;
  const shown = files.filter((f) => f.level === level);
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

          <h2 className="h2 section-title" style={{ marginTop: 24 }}>{t("detective.files.title")}</h2>
          <p className="sub" style={{ marginBottom: 16 }}>{t("detective.files.sub")}</p>
          {withCases.length > 0 && (
            <nav className="row case-file-levels" aria-label={t("detective.files.levels")}>
              {withCases.map((x) => (
                <button key={x.level} type="button" aria-pressed={level === x.level} onClick={() => setPicked(x.level)}
                        className={`btn small ${level === x.level ? "primary" : "ghost"}`}>
                  {x.locked && <Icon name="lock" size={11} />} HSK {x.level}
                  <span className="book-level-count">{x.cases}</span>
                </button>
              ))}
            </nav>
          )}
          {shown.length === 0 ? (
            <Empty>{t("detective.files.empty")}</Empty>
          ) : (
            <div className="grid cards">{shown.map((f) => <FileCard key={f.slug} f={f} />)}</div>
          )}
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
