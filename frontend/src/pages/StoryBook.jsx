import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";
import BookCover from "../components/BookCover.jsx";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import WordHelper from "../components/WordHelper.jsx";
import { Bar, Empty, Loading } from "../components/ui.jsx";
import { useApi } from "../hooks/useApi.js";

// One book (/stories/:slug): what it is, where the learner is in it, its
// chapters (each with its own comprehension round), its words, and -- once
// read -- what the learner really did with it.

export function BookStats({ stats }) {
  const { t } = useTranslation();
  const rows = [
    ["chapters", t("stories.stats.chaptersValue", { count: stats.chapters, total: stats.chapters_total })],
    ["words", t("stories.stats.wordsValue", { count: stats.words_known, total: stats.words_total })],
    ["explained", stats.explained],
    ["lookedUp", stats.looked_up],
    ["listened", stats.listened],
    ["rounds", stats.rounds],
  ];
  return (
    <dl className="book-stats">
      {rows.map(([k, v]) => (
        <div key={k}>
          <dt>{t(`stories.stats.${k}`)}</dt>
          <dd>{v}</dd>
        </div>
      ))}
    </dl>
  );
}

export default function StoryBook() {
  const { t } = useTranslation();
  const { slug } = useParams();
  const { data, error } = useApi(`/stories/${slug}`);
  const [word, setWord] = useState(null);

  if (error) {
    return (
      <Layout>
        <Empty>{error}</Empty>
        <div className="row" style={{ justifyContent: "center", marginTop: 12 }}>
          <Link to="/stories" className="btn">{t("stories.back")}</Link>
          <Link to="/journey" className="btn primary">{t("stories.lockedCta")}</Link>
        </div>
      </Layout>
    );
  }
  if (!data) return <Layout><Loading /></Layout>;

  const p = data.progress;
  const cta = p.completed ? "again" : p.started ? "continue" : "start";
  const readTo = cta === "continue" ? `/stories/${slug}/read/${p.chapter}` : `/stories/${slug}/read/1`;

  return (
    <Layout>
      <Link to={`/stories?level=${data.level}`} className="btn ghost small">
        <Icon name="arrowLeft" size={13} /> {t("stories.back")}
      </Link>
      <header className="page-head book-head" style={{ marginTop: 12 }}>
        <div className="book-head-main">
          <BookCover icon={data.icon} titleZh={data.title_zh} level={data.level} size="lg" />
          <div>
            <div className="page-eyebrow"><Icon name="bookOpen" size={13} /> HSK {data.level} · {t(`stories.topic.${data.topic}`)}</div>
            <h1 className="h1" lang="zh-CN">《{data.title_zh}》</h1>
            <p className="sub">{data.title}</p>
            <p className="book-feature-summary">{data.summary}</p>
            {p.started && !p.completed && (
              <div className="book-card-progress">
                <Bar value={p.percent} />
                <span className="sub">{t("stories.card.where", { chapter: p.chapter, total: data.chapters.length, percent: p.percent })}</span>
              </div>
            )}
            <div className="row" style={{ marginTop: 12 }}>
              <Link to={readTo} className="btn primary">
                <Icon name={cta === "continue" ? "play" : "bookOpen"} size={15} /> {t(`stories.book.${cta}`)}
              </Link>
            </div>
          </div>
        </div>
        <div className="kpi-row">
          <div className="kpi">
            <span className="kpi-value">{data.chapters.length}</span>
            <span className="kpi-label">{t("stories.book.chapters")}</span>
          </div>
          <div className="kpi">
            <span className="kpi-value">≈{data.minutes}</span>
            <span className="kpi-label">{t("stories.book.minutes")}</span>
          </div>
          <div className="kpi">
            <span className="kpi-value">{data.counts.new}</span>
            <span className="kpi-label">{t("stories.state.new")}</span>
          </div>
          <div className="kpi">
            <span className="kpi-value">{t(`stories.difficulty.${data.difficulty}`)}</span>
            <span className="kpi-label">{t("stories.book.difficulty")}</span>
          </div>
        </div>
      </header>

      <div className="ws">
        <div className="ws-main">
          {p.completed && data.stats && (
            <section className="card book-done">
              <h2 className="h2"><Icon name="check" size={16} /> {t("stories.done.title")}</h2>
              <BookStats stats={data.stats} />
              {data.next && (
                <Link to={`/stories/${data.next.slug}`} className="btn primary">
                  {t("stories.done.next")}: <span lang="zh-CN">《{data.next.title_zh}》</span> <Icon name="arrowRight" size={13} />
                </Link>
              )}
            </section>
          )}

          <section className="card">
            <h2 className="h2">{t("stories.book.chapters")}</h2>
            <ol className="book-chapters">
              {data.chapters.map((c) => (
                <li key={c.n} className={c.done ? "is-done" : p.chapter === c.n && p.started ? "is-current" : ""}>
                  <Link to={`/stories/${slug}/read/${c.n}`} className="book-chapter-link">
                    <span className="book-chapter-n">{c.done ? <Icon name="check" size={13} /> : c.n}</span>
                    <span className="book-chapter-title">
                      <b lang="zh-CN">{c.title_zh}</b>
                      <span className="sub">{c.title}</span>
                    </span>
                    <span className="sub">{t("stories.book.sentences", { count: c.sentences })}</span>
                  </Link>
                  {c.questions > 0 && (
                    <Link to={`/practice?source=story&story=${slug}&chapter=${c.n}`} className="btn small ghost">
                      {t("stories.book.check")}
                    </Link>
                  )}
                </li>
              ))}
            </ol>
          </section>
        </div>

        <aside className="ws-side">
          {word && (
            <div className="card side-card">
              <WordHelper wordId={word} onClose={() => setWord(null)} />
            </div>
          )}
          <div className="card side-card">
            <p className="side-title">{t("stories.book.words", { count: data.word_count })}</p>
            <p className="sub">{t("stories.book.wordsHint")}</p>
            <ul className="tale-glossary">
              {data.words.slice(0, 24).map((w) => (
                <li key={w.id}>
                  <button type="button" className="tale-gloss-row" onClick={() => setWord(w.id)}>
                    <b lang="zh-CN">{w.text}</b>
                    <span className="sub">{w.pinyin}</span>
                    <span className="tale-gloss-meaning">{w.meaning}</span>
                    <span className={`badge ${w.state === "known" ? "good" : w.state === "new" ? "accent" : ""}`}>{t(`stories.state.${w.state}`)}</span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </aside>
      </div>
    </Layout>
  );
}
