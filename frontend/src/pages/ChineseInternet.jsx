import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams, useSearchParams } from "react-router-dom";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import WordHelper from "../components/WordHelper.jsx";
import { Bar, Empty, Loading } from "../components/ui.jsx";
import { useApi } from "../hooks/useApi.js";
import { speakChinese } from "../zhSpeech.js";

// Chinese Internet (services/internet.py): curated real-world Chinese --
// news, posts, comments, shop pages, reviews, notices, chats -- each in its
// original form and two adaptations. Which version a learner is offered,
// and how every word is marked, comes from their own vocabulary, mistakes
// and Learning DNA. Reading is free; the check is a server-graded round.

const VERSIONS = ["beginner", "intermediate", "original"];
const CHATTY = new Set(["social", "comments", "messages", "chat", "review"]);

export default function ChineseInternet() {
  const { t } = useTranslation();
  const { data, error } = useApi("/internet/feed");

  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  if (!data) return <Layout><Loading /></Layout>;

  const read = data.items.filter((i) => i.rounds > 0).length;
  return (
    <Layout>
      <header className="page-head">
        <div>
          <div className="page-eyebrow"><Icon name="eye" size={13} /> {t("nav.internet")}</div>
          <h1 className="h1">{t("internet.title")}</h1>
          <p className="sub">{t("internet.subtitle")}</p>
        </div>
        <div className="kpi-row">
          <div className="kpi">
            <span className="kpi-value">{read}/{data.items.length}</span>
            <span className="kpi-label">{t("internet.checked")}</span>
          </div>
          <div className="kpi">
            <span className="kpi-value">{Math.round(data.profile.reading)}</span>
            <span className="kpi-label">{t("companionReact.skill.reading")}</span>
          </div>
        </div>
      </header>

      <div className="ws">
        <div className="ws-main">
          <div className="grid cards">
            {data.items.map((i) => (
              <Link key={i.slug} to={`/internet/${i.slug}`} className="card hover scene-card net-card">
                <div className="row spread" style={{ margin: 0, gap: 8 }}>
                  <span className="badge">
                    <span aria-hidden="true">{i.icon}</span> {t(`internet.kind.${i.kind}`)}
                  </span>
                  {i.rounds > 0 && <span className="badge good">{t("realLife.best", { score: Math.round(i.best) })}</span>}
                </div>
                <h3 className="h2" style={{ marginTop: 12 }} lang="zh-CN">{i.title}</h3>
                <p className="sub net-preview" lang="zh-CN">{i.preview}</p>
                <p className="sub">{i.summary}</p>
                <div className="net-fit">
                  <span className="badge accent">{t(`internet.version.${i.recommended}`)}</span>
                  <span className="sub">{t("internet.coverage", { pct: Math.round(i.coverage.ratio * 100) })}</span>
                </div>
                <Bar value={i.coverage.ratio * 100} />
              </Link>
            ))}
          </div>
        </div>
        <aside className="ws-side">
          <div className="card side-card">
            <p className="side-title">{t("internet.howTitle")}</p>
            <p className="sub">{t("internet.how")}</p>
            <ul className="scene-rules">
              <li>{t("internet.howLevel", { level: data.profile.level })}</li>
              <li>{t("internet.howReading", { reading: Math.round(data.profile.reading) })}</li>
              <li>{t("internet.howBar", { pct: Math.round(data.profile.bar * 100) })}</li>
            </ul>
          </div>
        </aside>
      </div>
    </Layout>
  );
}

// The workspace collapses to one column at 1080px (index.css); the word
// helper then sits under the text instead of in the side panel. One
// instance only, so a tapped word is fetched once.
function useNarrow() {
  const query = "(max-width: 1080px)";
  const [narrow, setNarrow] = useState(() => typeof window !== "undefined" && window.matchMedia(query).matches);
  useEffect(() => {
    const m = window.matchMedia(query);
    const on = () => setNarrow(m.matches);
    m.addEventListener("change", on);
    return () => m.removeEventListener("change", on);
  }, []);
  return narrow;
}

function Token({ tk, onPick, selected }) {
  if (tk.kind !== "word") return <span>{tk.text}</span>;
  const state = tk.weak ? "weak" : tk.due ? "due" : tk.status;
  return (
    <button
      type="button"
      className={`net-word is-${state}${tk.above ? " is-above" : ""}${selected ? " is-selected" : ""}`}
      onClick={() => onPick(tk.word_id)}
      title={`${tk.pinyin} — ${tk.meaning}`}
    >
      {tk.text}
    </button>
  );
}

export function InternetItem() {
  const { t } = useTranslation();
  const { slug } = useParams();
  const [params, setParams] = useSearchParams();
  const version = params.get("v");
  const { data, error } = useApi(`/internet/items/${slug}${version ? `?version=${version}` : ""}`);
  const [word, setWord] = useState(null);
  const [showSummary, setShowSummary] = useState(false);
  const narrow = useNarrow();

  if (error) {
    return (
      <Layout>
        <Empty>{error}</Empty>
        <Link to="/internet" className="btn ghost" style={{ marginTop: 12 }}>{t("practice.back")}</Link>
      </Layout>
    );
  }
  if (!data) return <Layout><Loading /></Layout>;

  const cov = data.coverage[data.version];
  const chatty = CHATTY.has(data.kind);
  return (
    <Layout>
      <header className="page-head">
        <div>
          <div className="page-eyebrow"><Icon name="eye" size={13} /> {t(`internet.kind.${data.kind}`)}</div>
          <h1 className="h1" lang="zh-CN">{data.title}</h1>
          <p className="sub">
            <span lang="zh-CN">{data.source}</span>{data.time && <> · <span lang="zh-CN">{data.time}</span></>}
          </p>
        </div>
        <div className="kpi-row">
          <div className="kpi">
            <span className="kpi-value">{Math.round(cov.ratio * 100)}%</span>
            <span className="kpi-label">{t("internet.readable")}</span>
          </div>
          <div className="kpi">
            <span className="kpi-value">{cov.new}</span>
            <span className="kpi-label">{t("internet.newWords")}</span>
          </div>
        </div>
      </header>

      <div className="ws">
        <div className="ws-main">
          <div className="card">
            <p className="side-title">{t("internet.versionLabel")}</p>
            <div className="row" style={{ gap: 8, flexWrap: "wrap", margin: 0 }} role="group" aria-label={t("internet.versionLabel")}>
              {VERSIONS.map((v) => (
                <button key={v} type="button" aria-pressed={data.version === v}
                        className={`btn small ${data.version === v ? "primary" : "ghost"}`}
                        onClick={() => setParams(v === data.recommended ? {} : { v }, { replace: true })}>
                  {t(`internet.version.${v}`)}
                  {v === data.recommended && <> · {t("internet.forYou")}</>}
                </button>
              ))}
            </div>
            <p className="sub" style={{ marginTop: 8 }}>
              {t("internet.coverageLine", {
                known: cov.known, familiar: cov.familiar, learning: cov.learning, fresh: cov.new, total: cov.total,
              })}
            </p>
          </div>

          <article className={`card net-article is-${data.kind}`}>
            <div className="row spread" style={{ margin: 0, flexWrap: "wrap", gap: 8 }}>
              <button type="button" className="btn small" onClick={() => speakChinese(data.blocks.map((b) => b.text).join(""))}>
                <Icon name="ear" size={13} /> {t("internet.listenAll")}
              </button>
              <button type="button" className="btn small ghost" aria-expanded={showSummary} onClick={() => setShowSummary((s) => !s)}>
                {showSummary ? t("internet.hideGist") : t("internet.showGist")}
              </button>
            </div>
            {showSummary && <p className="net-gist">{data.summary}</p>}
            <div className={chatty ? "net-thread" : "net-body"}>
              {data.blocks.map((b, i) => (
                <div key={i} className={chatty ? "net-post" : "net-para"}>
                  {b.who && <span className="net-who" lang="zh-CN">{b.who}</span>}
                  <p lang="zh-CN">
                    {b.tokens.map((tk, k) => (
                      <Token key={k} tk={tk} onPick={setWord} selected={word === tk.word_id} />
                    ))}
                    <button type="button" className="btn small ghost net-say" onClick={() => speakChinese(b.text)}
                            aria-label={t("companionReact.hear")} title={t("companionReact.hear")}>
                      <Icon name="ear" size={12} />
                    </button>
                  </p>
                </div>
              ))}
            </div>
            <p className="sub legend">
              <span className="net-word is-weak">词</span> {t("internet.legend.weak")}{"  "}
              <span className="net-word is-due">词</span> {t("internet.legend.due")}{"  "}
              <span className="net-word is-learning">词</span> {t("internet.legend.learning")}{"  "}
              <span className="net-word is-new is-above">词</span> {t("internet.legend.above")}
            </p>
            <p className="sub">{t("internet.tapHint")}</p>
          </article>

          {word && narrow && (
            <div className="card">
              <WordHelper wordId={word} item={slug} version={data.version} onClose={() => setWord(null)} />
            </div>
          )}

          <h2 className="h2 section-title">{t("internet.glossary")}</h2>
          {data.glossary.length === 0 ? (
            <Empty>{t("internet.noGlossary")}</Empty>
          ) : (
            <ul className="eco-list">
              {data.glossary.map((g) => (
                <li key={g.word_id}>
                  <button type="button" className={`eco-list-item${word === g.word_id ? " is-selected" : ""}`} onClick={() => setWord(g.word_id)}>
                    <b lang="zh-CN">{g.text}</b>
                    <span className="sub">{g.pinyin}</span>
                    {g.weak && <span className="badge bad">{t("internet.legend.weak")}</span>}
                    {g.due && !g.weak && <span className="badge accent">{t("internet.legend.due")}</span>}
                    {g.level && <span className="badge">HSK {g.level}</span>}
                    <span className="eco-list-meaning">{g.meaning}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}

          {data.grammar.length > 0 && (
            <>
              <h2 className="h2 section-title">{t("sentenceLesson.grammar")}</h2>
              <div className="col">
                {data.grammar.map((g) => (
                  <div key={g.id} className="card flat">
                    <div className="row spread" style={{ margin: 0, flexWrap: "wrap" }}>
                      <b>{g.title}</b>
                      <div className="row" style={{ gap: 6, margin: 0 }}>
                        {g.level && <span className="badge">HSK {g.level}</span>}
                        {g.above && <span className="badge accent">{t("sentenceLesson.stretch")}</span>}
                      </div>
                    </div>
                    {g.explanation && <p className="sub" style={{ marginTop: 8 }}>{g.explanation}</p>}
                    <p className="sub" style={{ marginTop: 8 }}>
                      {t("internet.inText")} <span lang="zh-CN">{g.example}</span>
                    </p>
                  </div>
                ))}
              </div>
            </>
          )}

          {data.notes.length > 0 && (
            <>
              <h2 className="h2 section-title">{t("internet.expressions")}</h2>
              <ul className="eco-list">
                {data.notes.map((n) => (
                  <li key={n.term} className="card flat net-note">
                    <b lang="zh-CN">{n.term}</b> <span className="sub">{n.py}</span>
                    <div className="sub">{n.text}</div>
                  </li>
                ))}
              </ul>
              <p className="sub">{t("internet.expressionsHint")}</p>
            </>
          )}
        </div>

        <aside className="ws-side">
          <div className="card side-card">
            {word && !narrow ? (
              <WordHelper wordId={word} item={slug} version={data.version} onClose={() => setWord(null)} />
            ) : (
              <>
                <p className="side-title">{t("internet.helper.title")}</p>
                <p className="sub">{t("internet.helper.empty")}</p>
              </>
            )}
          </div>
          <div className="card side-card">
            <p className="side-title">{t("internet.checkTitle")}</p>
            <p className="sub">{t("internet.checkText", { count: data.questions })}</p>
            {data.rounds > 0 && <p className="sub">{t("internet.yourBest", { score: Math.round(data.best) })}</p>}
            <Link to={`/practice?source=internet&item=${slug}&version=${data.version}`} className="btn primary" style={{ marginTop: 12 }}>
              <Icon name="target" size={15} /> {t("internet.check")}
            </Link>
          </div>
          <div className="card side-card">
            <Link to="/internet" className="btn ghost" style={{ width: "100%" }}>{t("practice.back")}</Link>
          </div>
        </aside>
      </div>
    </Layout>
  );
}
