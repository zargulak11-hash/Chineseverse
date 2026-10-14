import { useEffect, useState } from "react";
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
//
// Lines can be pinned to "your notes" while reading -- a detective's
// notebook kept in this browser for this case only. It is a reading aid:
// nothing is sent, and solving still happens in the graded round.

const notesKey = (slug) => `chineseverse_case_notes_${slug}`;

function loadNotes(slug) {
  try {
    const v = JSON.parse(localStorage.getItem(notesKey(slug)) || "[]");
    return Array.isArray(v) ? v : [];
  } catch {
    return [];
  }
}

function Line({ line, showTr, big = false, pinId, pinned, onPin }) {
  const { t } = useTranslation();
  return (
    <div className={`dossier-line${pinned ? " is-pinned" : ""}`}>
      <div style={{ minWidth: 0 }}>
        <div className={big ? "dossier-zh is-big" : "dossier-zh"} lang="zh-CN">{line.zh}</div>
        {line.pinyin && <div className="sub">{line.pinyin}</div>}
        {showTr && line.tr && <div className="sub dossier-tr">{line.tr}</div>}
      </div>
      <div className="dossier-line-tools">
        <button type="button" className="icon-btn" onClick={() => speakChinese(line.zh)}
                aria-label={t("companionReact.hear")} title={t("companionReact.hear")}>
          <Icon name="ear" size={15} />
        </button>
        {pinId && (
          <button type="button" className={`icon-btn dossier-pin${pinned ? " is-on" : ""}`} onClick={() => onPin(pinId)}
                  aria-pressed={pinned} aria-label={t(pinned ? "detective.fileUnpin" : "detective.filePin")}
                  title={t(pinned ? "detective.fileUnpin" : "detective.filePin")}>
            <Icon name="bookmark" size={15} />
          </button>
        )}
      </div>
    </div>
  );
}

export default function DetectiveFile() {
  const { t } = useTranslation();
  const { slug } = useParams();
  const { data, error } = useApi(`/detective/files/${slug}`);
  const [showTr, setShowTr] = useState(false);
  const [notes, setNotes] = useState(() => loadNotes(slug));

  useEffect(() => setNotes(loadNotes(slug)), [slug]);

  function pin(id) {
    setNotes((cur) => {
      const next = cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id];
      try {
        localStorage.setItem(notesKey(slug), JSON.stringify(next));
      } catch {
        // storage unavailable (private mode): the notes still work for this visit
      }
      return next;
    });
  }

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
  // Every pinnable line, by a stable id, with where it came from.
  const lines = {};
  data.suspects.forEach((s, i) => { lines[`s${i}`] = { line: s.statement, from: s.name, zhFrom: true }; });
  data.evidence.forEach((l, i) => { lines[`e${i}`] = { line: l, from: t("detective.exhibit", { n: i + 1 }) }; });
  data.timeline.forEach((l, i) => { lines[`t${i}`] = { line: l, from: l.time }; });
  const pinnedNotes = notes.filter((id) => lines[id]);
  const pinProps = (id) => ({ pinId: id, pinned: notes.includes(id), onPin: pin });

  return (
    <Layout>
      <header className="page-head dossier-head">
        <div>
          <div className="page-eyebrow"><Icon name="search" size={13} /> {t("detective.file.eyebrow", { level: data.level })}</div>
          <h1 className="h1">{data.title}</h1>
          <p className="dossier-title-zh" lang="zh-CN">{data.title_zh}</p>
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
          <section className="card dossier-brief" aria-labelledby="dossier-brief">
            <h2 className="h2" id="dossier-brief">{t("detective.file.brief")}</h2>
            <div className="dossier-lines">
              {data.brief.map((l, i) => <Line key={i} line={l} showTr={showTr} big />)}
            </div>
          </section>

          <h2 className="h2 section-title">{t("detective.file.suspects")}</h2>
          <div className="dossier-suspects">
            {data.suspects.map((s, i) => {
              const guilty = solved && data.culprit && s.name === data.culprit;
              return (
                <article key={s.name} className={`card flat dossier-suspect${guilty ? " is-culprit" : ""}`}>
                  {guilty && <span className="dossier-culprit-stamp">{t("detective.culpritStamp")}</span>}
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
                  <div className="dossier-quote">
                    <Line line={s.statement} showTr={showTr} {...pinProps(`s${i}`)} />
                  </div>
                </article>
              );
            })}
          </div>

          <section className="card" aria-labelledby="dossier-evidence" style={{ marginTop: 16 }}>
            <h2 className="h2" id="dossier-evidence">{t("detective.file.evidence")}</h2>
            <ol className="dossier-exhibits">
              {data.evidence.map((l, i) => (
                <li key={i}>
                  <span className="dossier-tag">{t("detective.exhibit", { n: i + 1 })}</span>
                  <Line line={l} showTr={showTr} {...pinProps(`e${i}`)} />
                </li>
              ))}
            </ol>
          </section>

          <section className="card" aria-labelledby="dossier-timeline" style={{ marginTop: 16 }}>
            <h2 className="h2" id="dossier-timeline">{t("detective.file.timeline")}</h2>
            <ol className="dossier-timeline">
              {data.timeline.map((l, i) => (
                <li key={i}>
                  <span className="badge">{l.time}</span>
                  <Line line={l} showTr={showTr} {...pinProps(`t${i}`)} />
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
              <div className="dossier-sealed">
                <span className="dossier-seal" aria-hidden="true"><Icon name="seal" size={22} /></span>
                <p className="sub" style={{ margin: 0 }}>{t("detective.file.verdictLocked")}</p>
              </div>
            )}
          </section>
        </div>

        <aside className="ws-side">
          <div className="card side-card dossier-ask">
            <p className="side-title">{t("detective.file.question")}</p>
            <Line line={data.ask} showTr={showTr} big />
            <Link to={`/practice?source=detective&case=${encodeURIComponent(`file:${data.slug}`)}`}
                  className="btn primary" style={{ marginTop: 16 }}>
              <Icon name="play" size={14} /> {t(data.played ? "detective.file.again" : "detective.file.start")}
            </Link>
          </div>
          <div className="card side-card dossier-notes" aria-live="polite">
            <p className="side-title"><Icon name="bookmark" size={13} /> {t("detective.notesTitle")}</p>
            {pinnedNotes.length === 0 ? (
              <p className="sub" style={{ margin: 0 }}>{t("detective.notesEmpty")}</p>
            ) : (
              <ol className="dossier-notes-list">
                {pinnedNotes.map((id) => (
                  <li key={id}>
                    <span className="dossier-note-from" lang={lines[id].zhFrom ? "zh-CN" : undefined}>{lines[id].from}</span>
                    <span lang="zh-CN">{lines[id].line.zh}</span>
                    <button type="button" className="icon-btn" onClick={() => pin(id)} aria-label={t("detective.fileUnpin")}>
                      <Icon name="x" size={13} />
                    </button>
                  </li>
                ))}
              </ol>
            )}
            <p className="sub dossier-notes-note">{t("detective.notesNote")}</p>
          </div>
          <div className="card side-card">
            <p className="side-title">{t("detective.howTitle")}</p>
            <p className="sub">{t("detective.file.how")}</p>
            {/* A Chinese UI gets no translations of the Chinese lines. */}
            {data.brief.some((l) => l.tr) && (
              <button type="button" className="btn small ghost" aria-pressed={showTr} onClick={() => setShowTr((v) => !v)}
                      style={{ marginTop: 12 }}>
                <Icon name="eye" size={13} /> {t(showTr ? "detective.file.hideTr" : "detective.file.showTr")}
              </button>
            )}
          </div>
          <Link to="/detective" className="btn ghost">
            <Icon name="arrowLeft" size={14} /> {t("detective.file.back")}
          </Link>
        </aside>
      </div>
    </Layout>
  );
}
