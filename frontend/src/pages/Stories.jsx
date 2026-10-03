import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router-dom";
import BookCover from "../components/BookCover.jsx";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import { Bar, Empty, Loading } from "../components/ui.jsx";
import { useApi } from "../hooks/useApi.js";

// Chinese Stories (/stories): the reading library, HSK 1 to 9. Everything
// on a card comes from the server (services/stories.py): chapters, an
// honest reading time, how many of the book's words are new to THIS
// learner, difficulty measured within the level, and the learner's own
// progress. A beginner sees one recommended book first; anyone can browse.

const LEVELS = [1, 2, 3, 4, 5, 6, 7, 8, 9];
const STATUSES = ["all", "new", "in_progress", "completed"];
const TIMES = ["any", "short", "long"];
const SHORT_MIN = 10;
// Topic and time filters appear once a level has enough books to need them.
const FILTERS_FROM = 5;

function BookCard({ b }) {
  const { t } = useTranslation();
  const locked = b.status === "locked";
  const body = (
    <>
      <BookCover icon={b.icon} titleZh={b.title_zh} level={b.level} />
      <div className="book-card-body">
        <h3 className="book-card-title">{b.title}</h3>
        <span className="book-card-zh" lang="zh-CN">《{b.title_zh}》</span>
        <p className="sub book-card-summary">{b.summary}</p>
        <p className="book-card-meta">
          <span>{t("stories.card.chapters", { count: b.chapters })}</span>
          <span>{t("stories.card.minutes", { count: b.minutes })}</span>
          {!locked && <span>{t("stories.card.newWords", { count: b.new_words })}</span>}
        </p>
        <div className="row book-card-badges">
          <span className="badge">{t(`stories.topic.${b.topic}`)}</span>
          <span className="badge">{t(`stories.difficulty.${b.difficulty}`)}</span>
          {b.status === "completed" && <span className="badge good"><Icon name="check" size={11} /> {t("stories.status.completed")}</span>}
        </div>
        {b.status === "in_progress" && (
          <div className="book-card-progress">
            <Bar value={b.percent} />
            <span className="sub">{t("stories.card.where", { chapter: b.chapter, total: b.chapters, percent: b.percent })}</span>
          </div>
        )}
        {locked && (
          <p className="sub book-card-locked"><Icon name="lock" size={12} /> {t("stories.status.locked", { level: b.gate })}</p>
        )}
      </div>
    </>
  );
  return locked ? (
    <div className="card book-card is-locked">{body}</div>
  ) : (
    <Link to={`/stories/${b.slug}`} className={`card hover book-card is-${b.status}`}>{body}</Link>
  );
}

function Feature({ b, kind }) {
  const { t } = useTranslation();
  const cont = kind === "continue";
  return (
    <section className="card book-feature" aria-labelledby={`feature-${kind}`}>
      <BookCover icon={b.icon} titleZh={b.title_zh} level={b.level} size="lg" />
      <div className="book-feature-body">
        <p className="page-eyebrow" id={`feature-${kind}`}>
          <Icon name={cont ? "bookOpen" : "sparkles"} size={13} /> {t(cont ? "stories.continue.title" : "stories.recommended.title")}
        </p>
        <h2 className="h2" lang="zh-CN">《{b.title_zh}》</h2>
        <p className="sub">{b.title} · HSK {b.level} · {t("stories.card.chapters", { count: b.chapters })} · {t("stories.card.minutes", { count: b.minutes })}</p>
        <p className="book-feature-summary">{b.summary}</p>
        {cont && (
          <div className="book-card-progress">
            <Bar value={b.percent} />
            <span className="sub">{t("stories.card.where", { chapter: b.chapter, total: b.chapters, percent: b.percent })}</span>
          </div>
        )}
        <Link to={cont ? `/stories/${b.slug}/read/${b.chapter || 1}` : `/stories/${b.slug}`} className="btn primary">
          <Icon name={cont ? "play" : "bookOpen"} size={15} /> {t(cont ? "stories.continue.cta" : "stories.recommended.cta")}
        </Link>
      </div>
    </section>
  );
}

export default function Stories() {
  const { t } = useTranslation();
  const { data, error } = useApi("/stories");
  const [params, setParams] = useSearchParams();

  const level = Number(params.get("level")) || (data ? Math.min(data.level, 9) : 1);
  const status = STATUSES.includes(params.get("status")) ? params.get("status") : "all";
  const topic = params.get("topic") || "all";
  const time = TIMES.includes(params.get("time")) ? params.get("time") : "any";

  const atLevel = useMemo(() => (data ? data.books.filter((b) => b.level === level) : []), [data, level]);
  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  if (!data) return <Layout><Loading /></Layout>;

  const set = (patch) => {
    const next = { level: String(level), status, topic, time, ...patch };
    const clean = Object.fromEntries(Object.entries(next).filter(([k, v]) => !(
      (k === "status" && v === "all") || (k === "topic" && v === "all") || (k === "time" && v === "any"))));
    setParams(clean, { replace: true });
  };
  const byId = Object.fromEntries(data.books.map((b) => [b.slug, b]));
  const cont = data.continue ? byId[data.continue] : null;
  const rec = !cont && data.recommended ? byId[data.recommended] : null;
  const topics = [...new Set(atLevel.map((b) => b.topic))].sort();
  const many = atLevel.length >= FILTERS_FROM;
  const shown = atLevel.filter((b) => (status === "all" || b.status === status)
    && (topic === "all" || b.topic === topic)
    && (time === "any" || (time === "short" ? b.minutes <= SHORT_MIN : b.minutes > SHORT_MIN)));
  const lv = data.levels.find((x) => x.level === level) || { locked: true, books: 0 };

  return (
    <Layout>
      <header className="page-head">
        <div>
          <div className="page-eyebrow"><Icon name="bookOpen" size={13} /> {t("stories.eyebrow")}</div>
          <h1 className="h1">{t("stories.title")}</h1>
          <p className="sub">{t("stories.subtitle")}</p>
        </div>
        <div className="kpi-row">
          <div className="kpi">
            <span className="kpi-value">{data.counts.completed}</span>
            <span className="kpi-label">{t("stories.kpi.completed")}</span>
          </div>
          <div className="kpi">
            <span className="kpi-value">{data.counts.in_progress}</span>
            <span className="kpi-label">{t("stories.kpi.reading")}</span>
          </div>
          <div className="kpi">
            <span className="kpi-value">{data.books.length}</span>
            <span className="kpi-label">{t("stories.kpi.library")}</span>
          </div>
          <div className="kpi">
            <span className="kpi-value">HSK {data.level}</span>
            <span className="kpi-label">{t("stories.kpi.level")}</span>
          </div>
        </div>
      </header>

      {(cont || rec) && <Feature b={cont || rec} kind={cont ? "continue" : "recommended"} />}

      <nav className="row book-levels" aria-label={t("stories.levels")}>
        {LEVELS.map((l) => {
          const info = data.levels.find((x) => x.level === l);
          return (
            <button key={l} type="button" aria-pressed={level === l} onClick={() => set({ level: String(l), topic: "all" })}
                    className={`btn small ${level === l ? "primary" : "ghost"}`}>
              {info?.locked && <Icon name="lock" size={11} />} HSK {l}
              <span className="book-level-count">{info?.books ?? 0}</span>
            </button>
          );
        })}
      </nav>

      {lv.locked ? (
        <div className="card book-locked-level">
          <p><Icon name="lock" size={14} /> {t("stories.status.locked", { level: Math.min(level, 7) })}</p>
          <p className="sub">{t("stories.lockedHow")}</p>
          <Link to="/journey" className="btn">{t("stories.lockedCta")} <Icon name="arrowRight" size={13} /></Link>
        </div>
      ) : null}

      {atLevel.length > 0 && (
        <div className="book-filters" role="group" aria-label={t("stories.filter.label")}>
          <div className="row book-filter-row">
            {STATUSES.map((s) => (
              <button key={s} type="button" aria-pressed={status === s} onClick={() => set({ status: s })}
                      className={`btn small ${status === s ? "primary" : "ghost"}`}>{t(`stories.filter.${s}`)}</button>
            ))}
          </div>
          {many && (
            <div className="row book-filter-row">
              <label className="book-select">
                <span>{t("stories.filter.topic")}</span>
                <select className="input" value={topic} onChange={(e) => set({ topic: e.target.value })}>
                  <option value="all">{t("stories.filter.anyTopic")}</option>
                  {topics.map((tp) => <option key={tp} value={tp}>{t(`stories.topic.${tp}`)}</option>)}
                </select>
              </label>
              <label className="book-select">
                <span>{t("stories.filter.time")}</span>
                <select className="input" value={time} onChange={(e) => set({ time: e.target.value })}>
                  {TIMES.map((x) => <option key={x} value={x}>{t(`stories.filter.time_${x}`, { count: SHORT_MIN })}</option>)}
                </select>
              </label>
            </div>
          )}
        </div>
      )}

      {shown.length === 0 ? (
        <Empty>{atLevel.length ? t("stories.emptyFilter") : t("stories.empty")}</Empty>
      ) : (
        <div className="book-grid">{shown.map((b) => <BookCard key={b.slug} b={b} />)}</div>
      )}
      <p className="sub book-library-note">{t("stories.why")}</p>
    </Layout>
  );
}
