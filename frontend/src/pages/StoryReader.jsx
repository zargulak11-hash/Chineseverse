import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import WordHelper from "../components/WordHelper.jsx";
import { Empty, Loading } from "../components/ui.jsx";
import { useApi } from "../hooks/useApi.js";
import { speakChinese } from "../zhSpeech.js";

// One story (/stories/:slug): read and listen, learn its words, then the
// graded round (practice source "story": comprehension, a line heard and said
// aloud, the story's new words as real cards). Support -- pinyin, translation,
// audio speed -- follows the story's level (services/stories.py support()).

const STATES = ["new", "review", "learning", "known"];

export default function StoryReader() {
  const { t } = useTranslation();
  const { slug } = useParams();
  const { data, error } = useApi(`/stories/${slug}`);
  const [pinyin, setPinyin] = useState(null);
  const [trAll, setTrAll] = useState(null);
  const [opened, setOpened] = useState({});
  const [word, setWord] = useState(null);
  const [playing, setPlaying] = useState(-1);
  const stopRef = useRef(false);

  useEffect(() => {
    if (!data) return;
    setPinyin(data.support.pinyin === "on");
    setTrAll(data.support.translation === "inline");
  }, [data?.slug]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => () => window.speechSynthesis?.cancel(), []);

  if (error) {
    return (
      <Layout>
        <Empty>{error}</Empty>
        <div className="row" style={{ justifyContent: "center", marginTop: 12 }}>
          <Link to="/stories" className="btn">{t("stories.back")}</Link>
          <Link to="/journey" className="btn primary">{t("nav.journey")}</Link>
        </div>
      </Layout>
    );
  }
  if (!data) return <Layout><Loading /></Layout>;
  const rate = data.support.rate;
  const say = (text, onEnd) => speakChinese(text, { profile: { rate, pitch: 1, volume: 1 }, onEnd, whole: true });

  function playFrom(i) {
    if (i >= data.sentences.length || stopRef.current) {
      setPlaying(-1);
      return;
    }
    setPlaying(i);
    say(data.sentences[i].zh, () => playFrom(i + 1));
  }
  function playAll() {
    if (playing >= 0) {
      stopRef.current = true;
      window.speechSynthesis?.cancel();
      setPlaying(-1);
      return;
    }
    stopRef.current = false;
    playFrom(0);
  }

  const translationMode = data.support.translation;
  return (
    <Layout>
      <Link to="/stories" className="sub">← {t("stories.back")}</Link>
      <header className="page-head" style={{ marginTop: 10 }}>
        <div>
          <div className="page-eyebrow"><Icon name="bookOpen" size={13} /> HSK {data.level} · {t("stories.eyebrow")}</div>
          <h1 className="h1"><span aria-hidden="true">{data.icon}</span> {data.title}</h1>
          <p className="sub"><span lang="zh-CN">{data.title_zh}</span> · {data.summary}</p>
        </div>
        <div className="kpi-row">
          {STATES.filter((k) => data.counts[k] > 0).map((k) => (
            <div className="kpi" key={k}>
              <span className="kpi-value">{data.counts[k]}</span>
              <span className="kpi-label">{t(`stories.state.${k}`)}</span>
            </div>
          ))}
        </div>
      </header>

      <ol className="tale-loop" aria-label={t("stories.eyebrow")}>
        {["read", "words", "questions", "say"].map((k, i) => (
          <li key={k} className={i === 0 ? "is-current" : ""}><span>{i + 1}</span> {t(`stories.loop.${k}`)}</li>
        ))}
      </ol>

      <div className="ws">
        <div className="ws-main">
          <section className="card tale-reader">
            <div className="tale-tools">
              <button type="button" className="btn primary small" onClick={playAll} aria-pressed={playing >= 0}>
                <Icon name={playing >= 0 ? "stop" : "play"} size={14} /> {playing >= 0 ? t("stories.stop") : t("stories.playAll")}
              </button>
              <button type="button" className={`btn small${pinyin ? "" : " ghost"}`} aria-pressed={!!pinyin} onClick={() => setPinyin((v) => !v)}>
                {t("stories.pinyin")}
              </button>
              {translationMode !== "hidden" || trAll ? (
                <button type="button" className={`btn small${trAll ? "" : " ghost"}`} aria-pressed={!!trAll} onClick={() => setTrAll((v) => !v)}>
                  {t("stories.translation")}
                </button>
              ) : (
                <button type="button" className="btn small ghost" aria-pressed="false" onClick={() => setTrAll(true)}>
                  {t("stories.translation")}
                </button>
              )}
              <span className="sub tale-support">{t(`stories.support.${translationMode === "inline" ? "on" : translationMode}`)}</span>
            </div>
            <div className="tale-text" lang="zh-CN">
              {data.sentences.map((s, i) => (
                <div key={i} className={`tale-sentence${playing === i ? " is-playing" : ""}`}>
                  <button type="button" className="icon-btn tale-say" onClick={() => say(s.zh)}
                          aria-label={t("stories.playLine")} title={t("stories.playLine")}>
                    <Icon name="ear" size={15} />
                  </button>
                  <div className="tale-line">
                    <p className="tale-zh">
                      {s.tokens.map((tk, j) => tk.word_id ? (
                        <button key={j} type="button" className={`tale-word is-${tk.state}${word === tk.word_id ? " is-open" : ""}`}
                                onClick={() => setWord(tk.word_id)} title={tk.meaning}>
                          {tk.text}
                        </button>
                      ) : <span key={j}>{tk.text}</span>)}
                    </p>
                    {pinyin && <p className="tale-py">{s.pinyin}</p>}
                    {s.tr && (trAll || opened[i]) && <p className="tale-tr" lang="">{s.tr}</p>}
                    {s.tr && !trAll && !opened[i] && translationMode !== "hidden" && (
                      <button type="button" className="tale-tr-btn" onClick={() => setOpened((o) => ({ ...o, [i]: true }))}>
                        {t("stories.translate")}
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
            <ul className="tale-legend sub" aria-label={t("stories.wordsTitle")}>
              {STATES.map((k) => <li key={k}><span className={`tale-word is-${k}`} aria-hidden="true">字</span> {t(`stories.state.${k}`)}</li>)}
            </ul>
          </section>

          <section className="card tale-questions">
            <h2 className="h2">{t("stories.questionsTitle")}</h2>
            <p className="sub">{t("stories.questionsBody", { count: data.questions })}</p>
            {data.record && <p className="sub">{t("stories.bestSoFar", { best: Math.round(data.record.best) })}</p>}
            <Link to={`/practice?source=story&story=${data.slug}`} className="btn primary">
              <Icon name="play" size={15} /> {data.record ? t("stories.again") : t("stories.startQuestions")}
            </Link>
          </section>
        </div>

        <aside className="ws-side">
          {word && (
            <div className="card side-card">
              <WordHelper wordId={word} onClose={() => setWord(null)} />
            </div>
          )}
          <div className="card side-card">
            <p className="side-title">{t("stories.wordsTitle")}</p>
            <p className="sub">{t("stories.wordsHint")}</p>
            <ul className="tale-glossary">
              {data.words.slice(0, 18).map((w) => (
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
