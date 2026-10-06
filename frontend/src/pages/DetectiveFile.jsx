import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import { Empty, Loading } from "../components/ui.jsx";
import { useApi } from "../hooks/useApi.js";
import { speakChinese } from "../zhSpeech.js";

// One hand-written Detective case file (/detective/file/:slug, from
// services/detective.dossier): the case, every suspect's statement, the
// evidence and the timeline, all in Chinese with curriculum pinyin at the
// lower levels and translations on request. The verdict only appears once
// this learner has solved the case; the case itself is played as a graded
// round (/practice?source=detective&case=file:<slug>).

function Line({ line, showTr, big = false }) {
  const { t } = useTranslation();
  return (
    <div className="dossier-line">
      <div style={{ minWidth: 0 }}>
        <div className={big ? "dossier-zh is-big" : "dossier-zh"} lang="zh-CN">{line.zh}</div>
        {line.pinyin && <div className="sub">{line.pinyin}</div>}
        {showTr && line.tr && <div className="sub dossier-tr">{line.tr}</div>}
      </div>
      <button type="button" className="icon-btn" onClick={() => speakChinese(line.zh)}
              aria-label={t("companionReact.hear")} title={t("companionReact.hear")}>
        <Icon name="ear" size={15} />
      </button>
    </div>
  );
}

export default function DetectiveFile() {
  const { t } = useTranslation();
  const { slug } = useParams();
  const { data, error } = useApi(`/detective/files/${slug}`);
  const [showTr, setShowTr] = useState(false);

  if (error) {
    return (
      <Layout>
        <Empty>{error}</Empty>
        <Link to="/detective" className="btn ghost" style={{ marginTop: 16 }}>
          <Icon name="arrowLeft" size={14} /> {t("detective.file.back")}
        </Link>
      </Layout>
    );
  }
  if (!data) return <Layout><Loading /></Layout>;

  const solved = data.solved > 0;
  return (
    <Layout>
      <header className="page-head">
        <div>
          <div className="page-eyebrow"><Icon name="search" size={13} /> {t("detective.file.eyebrow", { level: data.level })}</div>
          <h1 className="h1">{data.title}</h1>
          <p className="sub" lang="zh-CN">{data.title_zh}</p>
          <p className="sub">{data.summary}</p>
        </div>
        <div className="kpi-row">
          <div className="kpi">
            <span className="kpi-value">{data.suspects.length}</span>
            <span className="kpi-label">{t("detective.file.suspects")}</span>
          </div>
          <div className="kpi">
            <span className="kpi-value">{data.clues}</span>
            <span className="kpi-label">{t("detective.file.clues")}</span>
          </div>
          <div className="kpi">
            <span className="kpi-value">{data.solved}/{data.played}</span>
            <span className="kpi-label">{t("detective.solved")}</span>
          </div>
        </div>
      </header>

      <div className="ws">
        <div className="ws-main">
          <section className="card" aria-labelledby="dossier-brief">
            <h2 className="h2" id="dossier-brief">{t("detective.file.brief")}</h2>
            <div className="dossier-lines">
              {data.brief.map((l, i) => <Line key={i} line={l} showTr={showTr} big />)}
            </div>
          </section>

          <h2 className="h2 section-title">{t("detective.file.suspects")}</h2>
          <div className="dossier-suspects">
            {data.suspects.map((s) => (
              <article key={s.name} className="card flat dossier-suspect">
                <div className="dossier-suspect-head">
                  <span className="dossier-avatar" aria-hidden="true" lang="zh-CN">{s.name.slice(-1)}</span>
                  <div style={{ minWidth: 0 }}>
                    <b lang="zh-CN">{s.name}</b>
                    <div className="sub">{s.pinyin}</div>
                  </div>
                </div>
                <p className="sub dossier-role">
                  <span lang="zh-CN">{s.role.zh}</span>
                  {s.role.tr && <> · {s.role.tr}</>}
                </p>
                <p className="side-title">{t("detective.file.statement")}</p>
                <Line line={s.statement} showTr={showTr} />
              </article>
            ))}
          </div>

          <section className="card" aria-labelledby="dossier-evidence" style={{ marginTop: 16 }}>
            <h2 className="h2" id="dossier-evidence">{t("detective.file.evidence")}</h2>
            <ol className="dossier-list">
              {data.evidence.map((l, i) => <li key={i}><Line line={l} showTr={showTr} /></li>)}
            </ol>
          </section>

          <section className="card" aria-labelledby="dossier-timeline" style={{ marginTop: 16 }}>
            <h2 className="h2" id="dossier-timeline">{t("detective.file.timeline")}</h2>
            <ol className="dossier-timeline">
              {data.timeline.map((l, i) => (
                <li key={i}>
                  <span className="badge">{l.time}</span>
                  <Line line={l} showTr={showTr} />
                </li>
              ))}
            </ol>
          </section>

          <section className={`card dossier-verdict${solved ? " is-solved" : ""}`} aria-labelledby="dossier-verdict" style={{ marginTop: 16 }}>
            <h2 className="h2" id="dossier-verdict">
              <Icon name={solved ? "check" : "lock"} size={16} /> {t("detective.file.verdict")}
            </h2>
            {solved ? (
              <>
                <p><span className="badge good">{t("detective.file.culprit")}</span> <b lang="zh-CN">{data.culprit}</b></p>
                <div className="dossier-lines">
                  {data.verdict.map((l, i) => <Line key={i} line={l} showTr={showTr} />)}
                </div>
              </>
            ) : (
              <p className="sub">{t("detective.file.verdictLocked")}</p>
            )}
          </section>
        </div>

        <aside className="ws-side">
          <div className="card side-card">
            <p className="side-title">{t("detective.file.question")}</p>
            <Line line={data.ask} showTr={showTr} big />
            <Link to={`/practice?source=detective&case=${encodeURIComponent(`file:${data.slug}`)}`}
                  className="btn primary" style={{ marginTop: 16 }}>
              <Icon name="play" size={14} /> {t(data.played ? "detective.file.again" : "detective.file.start")}
            </Link>
          </div>
          <div className="card side-card">
            <p className="side-title">{t("detective.howTitle")}</p>
            <p className="sub">{t("detective.file.how")}</p>
            <button type="button" className="btn small ghost" aria-pressed={showTr} onClick={() => setShowTr((v) => !v)}
                    style={{ marginTop: 12 }}>
              <Icon name="eye" size={13} /> {t(showTr ? "detective.file.hideTr" : "detective.file.showTr")}
            </button>
          </div>
          <Link to="/detective" className="btn ghost">
            <Icon name="arrowLeft" size={14} /> {t("detective.file.back")}
          </Link>
        </aside>
      </div>
    </Layout>
  );
}
